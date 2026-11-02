"""Local dataset summaries and context-aware question starters."""
from __future__ import annotations
import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict:
    rows, ncols = df.shape
    total = rows * ncols
    missing = df.isna().sum()
    numeric = df.select_dtypes(include="number").replace([float("inf"), float("-inf")], float("nan"))
    categorical = df.select_dtypes(include=["object", "category", "bool"])
    duplicates = int(df.duplicated().sum()) if rows else 0
    stats = numeric.describe(percentiles=[.25, .5, .75]).T if not numeric.empty else pd.DataFrame()
    if not stats.empty:
        stats.insert(0, "Column", stats.index.astype(str))
        stats.insert(2, "sum", numeric.sum(min_count=1).values)
        stats["IQR"] = stats["75%"] - stats["25%"]
        indexed = stats.set_index("Column")
        lo, hi = numeric.quantile(.25) - indexed["IQR"] * 1.5, numeric.quantile(.75) + indexed["IQR"] * 1.5
        stats["Potential outliers (IQR)"] = [int(((numeric[c] < lo[str(c)]) | (numeric[c] > hi[str(c)])).sum()) for c in numeric.columns]
        stats = stats.reset_index(drop=True)
    columns = pd.DataFrame({
        "Column": [str(c) for c in df.columns], "Type": [str(t) for t in df.dtypes],
        "Non-null": [int(df[c].count()) for c in df.columns], "Missing": [int(missing[c]) for c in df.columns],
        "Missing %": [(df[c].isna().mean() * 100).round(1) for c in df.columns],
        "Unique": [int(df[c].nunique()) for c in df.columns],
    })
    categories = []
    for c in categorical.columns:
        counts = df[c].value_counts().head(5)
        if not counts.empty:
            categories.append({"column": str(c), "values": [(str(v), int(n)) for v, n in counts.items()]})
    findings = [f"The dataset contains {rows:,} rows across {ncols:,} columns."]
    if not stats.empty:
        row = stats.loc[stats["count"].idxmax()]
        findings.append(f"For {row['Column']}, the median is {row['50%']:,.2f}; values range from {row['min']:,.2f} to {row['max']:,.2f}.")
        outlier_row = stats.loc[stats["Potential outliers (IQR)"].idxmax()]
        if outlier_row["Potential outliers (IQR)"]:
            findings.append(f"The IQR rule flags {int(outlier_row['Potential outliers (IQR)']):,} potential outlier(s) in {outlier_row['Column']}; review them in context.")
    missing_pct = missing.sum() / total * 100 if total else 0
    findings.append(f"{int(missing.sum()):,} cells ({missing_pct:.1f}%) are missing." if total else "The dataset has no cells.")
    findings.append(f"{duplicates:,} exact duplicate row(s) were found.")
    if categories:
        c = categories[0]
        findings.append(f"{c['column']} most often contains {c['values'][0][0]!r} ({c['values'][0][1]:,} rows).")
    findings.append("These are descriptive patterns and do not establish cause and effect.")
    return {"rows": rows, "columns": ncols, "numeric_columns": len(numeric.columns),
            "missing_cells": int(missing.sum()), "missing_percent": missing.sum()/total*100 if total else 0,
            "duplicate_rows": duplicates, "numeric_summary": stats, "column_summary": columns,
            "top_categories": categories, "findings": findings}


def suggest_questions(df: pd.DataFrame, limit: int = 4) -> list[str]:
    if df is None or df.empty:
        return []
    nums = df.select_dtypes(include="number").columns.tolist()
    cats = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    dates = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    date = dates[0] if dates else None
    if date is None:
        for c in cats:
            values = df[c].dropna().head(300)
            if len(values) > 1 and pd.to_datetime(values, errors="coerce").notna().mean() >= .85:
                date = c
                break
    q = []
    if nums:
        q.append(f"Summarize {nums[0]} with its mean, median, range, and total.")
        if date is not None:
            q.append(f"How does {nums[0]} change over time in {date}? Include a chart.")
        if cats:
            q.append(f"Compare {nums[0]} across groups in {cats[0]}, and visualize the results.")
        if len(nums) > 1:
            q.append(f"Is there a relationship between {nums[0]} and {nums[1]}? Show a chart.")
    if cats:
        q.append(f"What are the most common values in {cats[0]}?")
    if any(df[c].isna().any() for c in df.columns):
        q.append("Which fields have missing values, and how could that affect this analysis?")
    q.append("What does this dataset describe? Summarize its main patterns with visuals.")
    return list(dict.fromkeys(q))[:limit]
