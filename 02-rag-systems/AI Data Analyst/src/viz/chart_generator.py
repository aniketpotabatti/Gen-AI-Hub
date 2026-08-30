"""
Smart chart generator — creates Plotly visualizations from AI analyst responses.
The AI suggests chart types; this module renders them.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def generate_chart(
    result,
    chart_suggestion: dict | None,
    df: pd.DataFrame | None = None,
) -> go.Figure | None:
    """
    Generate a Plotly chart from an AI analyst response.

    Args:
        result: The raw result from code execution (DataFrame, Series, or scalar).
        chart_suggestion: Dict with 'type' and 'config' keys from the AI.
        df: The original DataFrame (used when the result is a scalar but we need chart data).

    Returns:
        A Plotly Figure, or None if no chart can be generated.
    """
    if chart_suggestion is None:
        return None

    chart_type = chart_suggestion.get("type", "none")
    config = chart_suggestion.get("config", {})

    if chart_type == "none":
        return None

    # Determine the data source for the chart
    chart_data = _prepare_chart_data(result, df)
    if chart_data is None or chart_data.empty:
        return None

    title = config.get("title", "Analysis Result")
    x = config.get("x")
    y = config.get("y")

    # Validate columns exist
    x = x if x and x in chart_data.columns else None
    y = y if y and y in chart_data.columns else None

    # Auto-detect x and y if not specified or invalid
    if x is None or y is None:
        x, y = _auto_detect_axes(chart_data)
        if x is None or y is None:
            return None

    try:
        fig = _create_chart(chart_type, chart_data, x, y, title, config)
        fig = _apply_styling(fig, title)
        return fig
    except Exception:
        # If the suggested chart fails, try a simple bar chart
        try:
            fig = px.bar(chart_data, x=x, y=y, title=title)
            fig = _apply_styling(fig, title)
            return fig
        except Exception:
            return None


def auto_chart(df: pd.DataFrame, title: str = "Data Overview") -> go.Figure | None:
    """
    Generate a sensible default chart for a DataFrame.
    Used when showing an overview of uploaded data.
    """
    if df is None or df.empty:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols:
        return None

    # Strategy: pick the best chart based on column types
    if categorical_cols and numeric_cols:
        # Bar chart: category vs first numeric
        cat = categorical_cols[0]
        num = numeric_cols[0]
        # Aggregate if too many values
        if df[cat].nunique() > 20:
            chart_df = df.groupby(cat)[num].mean().nlargest(15).reset_index()
        else:
            chart_df = df.groupby(cat)[num].mean().reset_index()

        fig = px.bar(
            chart_df, x=cat, y=num,
            title=f"{title}: {num} by {cat}",
            color=num,
            color_continuous_scale="Viridis",
        )
    elif len(numeric_cols) >= 2:
        # Scatter: first two numeric columns
        fig = px.scatter(
            df.head(500), x=numeric_cols[0], y=numeric_cols[1],
            title=f"{title}: {numeric_cols[0]} vs {numeric_cols[1]}",
            opacity=0.7,
        )
    else:
        # Histogram of the single numeric column
        fig = px.histogram(
            df, x=numeric_cols[0],
            title=f"{title}: Distribution of {numeric_cols[0]}",
            nbins=30,
        )

    return _apply_styling(fig, title)


# ── Private helpers ──────────────────────────────────────────────


def _prepare_chart_data(result, df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Convert various result types into a DataFrame for charting."""
    if isinstance(result, pd.DataFrame):
        return result
    if isinstance(result, pd.Series):
        return result.reset_index()
    if df is not None:
        return df
    return None


def _auto_detect_axes(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Pick the best x and y columns from a DataFrame."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    non_numeric = df.select_dtypes(exclude="number").columns.tolist()

    if non_numeric and numeric:
        return non_numeric[0], numeric[0]
    if len(numeric) >= 2:
        return numeric[0], numeric[1]
    if len(df.columns) >= 2:
        return df.columns[0], df.columns[1]
    if len(df.columns) == 1:
        return df.index.name or "index", df.columns[0]

    return None, None


def _create_chart(
    chart_type: str,
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    config: dict,
) -> go.Figure:
    """Create a Plotly figure based on chart type."""
    color = config.get("color")
    color = color if color and color in data.columns else None

    chart_map = {
        "bar": lambda: px.bar(data, x=x, y=y, title=title, color=color, color_continuous_scale="Viridis"),
        "line": lambda: px.line(data, x=x, y=y, title=title, color=color, markers=True),
        "scatter": lambda: px.scatter(data, x=x, y=y, title=title, color=color, opacity=0.7),
        "pie": lambda: px.pie(data, names=x, values=y, title=title),
        "heatmap": lambda: px.density_heatmap(data, x=x, y=y, title=title, color_continuous_scale="Viridis"),
    }

    creator = chart_map.get(chart_type, chart_map["bar"])
    return creator()


def _apply_styling(fig: go.Figure, title: str) -> go.Figure:
    """Apply consistent, modern styling to charts."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color="#e0e0e0"),
        title=dict(
            text=title,
            font=dict(size=18, color="#ffffff"),
            x=0.5,
            xanchor="center",
        ),
        margin=dict(l=50, r=30, t=60, b=50),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig
