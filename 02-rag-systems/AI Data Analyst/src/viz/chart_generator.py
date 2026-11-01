"""
Plotly chart generation for dataset previews and AI analysis results.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

_PALETTE = ["#43D6C4", "#60A5FA", "#A78BFA", "#FBBF24", "#FB7185", "#34D399", "#F97316"]
_MAX_POINTS = 5000


def generate_chart(result, chart_suggestion: dict | None, df: pd.DataFrame | None = None) -> go.Figure | None:
    """Render a suggested chart and fall back to a suitable automatic visualization."""
    if not isinstance(chart_suggestion, dict) or not chart_suggestion:
        return None
    chart_type = str(chart_suggestion.get("type", "none")).strip().lower()
    if chart_type == "none":
        return None

    data = _prepare_chart_data(result, df)
    if data is None or data.empty:
        return None
    config = chart_suggestion.get("config") or {}
    if not isinstance(config, dict):
        config = {}
    title = str(config.get("title") or "Analysis result")
    x_value, y_value = config.get("x"), config.get("y")
    x = x_value if isinstance(x_value, str) and x_value in data.columns else None
    y = y_value if isinstance(y_value, str) and y_value in data.columns else None
    if x is None or y is None:
        x, y = _auto_detect_axes(data)
    if x is not None and y is not None:
        try:
            fig = _create_chart(chart_type, _limit_points(data), x, y, title, config)
            return _apply_styling(fig, title)
        except (TypeError, ValueError, KeyError, IndexError):
            pass
    return auto_chart(data, title="Analysis result")

def auto_chart(df: pd.DataFrame, title: str = "Data overview") -> go.Figure | None:
    """Choose a visualization using numeric, date, or categorical columns."""
    if df is None or df.empty or len(df.columns) == 0:
        return None
    data = df.dropna(axis=1, how="all").copy()
    if data.empty or len(data.columns) == 0:
        return None
    for column in data.select_dtypes(include=["object", "string"]).columns:
        if any(token in str(column).lower() for token in ("date", "time", "timestamp")):
            parsed = pd.to_datetime(data[column], errors="coerce")
            if parsed.notna().mean() >= 0.7 and parsed.nunique(dropna=True) > 1:
                data[column] = parsed
    numeric = data.select_dtypes(include="number").columns.tolist()
    dates = data.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    categories = [col for col in data.columns if col not in numeric and col not in dates]

    if numeric and dates:
        date_col, value_col = dates[0], numeric[0]
        trend = data[[date_col, value_col]].dropna()
        if not trend.empty:
            trend = trend.groupby(date_col, as_index=False)[value_col].mean().sort_values(date_col)
            fig = px.line(_limit_points(trend), x=date_col, y=value_col, markers=True,
                          color_discrete_sequence=_PALETTE)
            return _apply_styling(fig, f"{title}: {value_col} over time")
    if numeric and categories:
        category = next((c for c in categories if 1 < data[c].nunique(dropna=True) <= 40), categories[0])
        value = next((c for c in numeric if data[c].nunique(dropna=True) > 1), numeric[0])
        grouped = data.groupby(category, dropna=False, observed=True)[value].mean().reset_index()
        if grouped.empty:
            return None
        if len(grouped) > 18:
            grouped = grouped.nlargest(18, value)
        grouped = grouped.sort_values(value)
        fig = px.bar(grouped, x=value, y=category, orientation="h", color=value,
                     color_continuous_scale=["#17324A", "#43D6C4"])
        return _apply_styling(fig, f"{title}: {value} by {category}")
    if len(numeric) >= 2:
        pair = data[numeric[:2]].dropna()
        if not pair.empty:
            fig = px.scatter(_limit_points(pair), x=numeric[0], y=numeric[1], opacity=.78,
                             color_discrete_sequence=_PALETTE)
            return _apply_styling(fig, f"{title}: {numeric[1]} vs {numeric[0]}")
    if numeric:
        values = data[numeric[0]].dropna()
        if not values.empty:
            fig = px.histogram(values.to_frame(), x=numeric[0], nbins=30,
                               color_discrete_sequence=_PALETTE)
            return _apply_styling(fig, f"{title}: distribution of {numeric[0]}")
    if categories:
        category = categories[0]
        counts = data[category].fillna("(missing)").astype(str).value_counts().head(18)
        if not counts.empty:
            chart_data = counts.rename_axis(category).reset_index(name="Records").sort_values("Records")
            fig = px.bar(chart_data, x="Records", y=category, orientation="h", color="Records",
                         color_continuous_scale=["#17324A", "#43D6C4"])
            return _apply_styling(fig, f"{title}: records by {category}")
    return None


def _prepare_chart_data(result, df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Convert analysis output to a frame and handle single-column results."""
    if isinstance(result, pd.DataFrame):
        data = result.copy()
    elif isinstance(result, pd.Series):
        data = result.rename(result.name or "value").rename_axis("category").reset_index()
    elif df is not None:
        data = df.copy()
    else:
        return None
    if len(data.columns) == 1 and pd.api.types.is_numeric_dtype(data.iloc[:, 0]):
        row_column = "_row_number"
        while row_column in data.columns:
            row_column = "_" + row_column
        data.insert(0, row_column, range(len(data)))
    return data


def _auto_detect_axes(df: pd.DataFrame) -> tuple[str | None, str | None]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    other = [col for col in df.columns if col not in numeric]
    if other and numeric:
        return other[0], numeric[0]
    if len(numeric) >= 2:
        return numeric[0], numeric[1]
    if len(df.columns) >= 2:
        return df.columns[0], df.columns[1]
    return None, None


def _limit_points(data: pd.DataFrame) -> pd.DataFrame:
    if len(data) <= _MAX_POINTS:
        return data
    return data.sample(_MAX_POINTS, random_state=7).sort_index()


def _create_chart(chart_type: str, data: pd.DataFrame, x: str, y: str, title: str, config: dict) -> go.Figure:
    color = config.get("color")
    color = color if color in data.columns else None
    args = {"color": color, "color_discrete_sequence": _PALETTE}
    creators = {
        "bar": lambda: px.bar(data, x=x, y=y, title=title, **args),
        "line": lambda: px.line(data, x=x, y=y, title=title, markers=True, **args),
        "scatter": lambda: px.scatter(data, x=x, y=y, title=title, opacity=.8, **args),
        "pie": lambda: px.pie(data, names=x, values=y, title=title, color_discrete_sequence=_PALETTE),
        "heatmap": lambda: px.density_heatmap(data, x=x, y=y, title=title,
                                               color_continuous_scale=["#17324A", "#43D6C4"]),
        "histogram": lambda: px.histogram(data, x=x, title=title, color_discrete_sequence=_PALETTE),
    }
    return creators.get(chart_type, creators["bar"])()


def _apply_styling(fig: go.Figure, title: str) -> go.Figure:
    """Apply one polished dark theme to every generated figure."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=_PALETTE, font=dict(family="Inter, sans-serif", size=13, color="#DCE6F1"),
        title=dict(text=title, font=dict(size=17, color="#F3F7FC"), x=0, xanchor="left"),
        margin=dict(l=22, r=24, t=58, b=28),
        hoverlabel=dict(bgcolor="#14263B", bordercolor="#37516D", font_color="#F3F7FC"),
        legend=dict(bgcolor="rgba(12,26,43,.72)", bordercolor="rgba(148,170,194,.18)",
                    borderwidth=1, font=dict(color="#B8C8D8")),
    )
    axes = dict(gridcolor="rgba(180,198,216,.10)", linecolor="rgba(180,198,216,.18)",
                zeroline=False, automargin=True, title_font=dict(color="#B8C8D8"),
                tickfont=dict(color="#A9BACB"))
    fig.update_xaxes(**axes)
    fig.update_yaxes(**axes)
    return fig
