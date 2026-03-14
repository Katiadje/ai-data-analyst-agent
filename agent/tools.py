"""
Tools used by the AI Data Analyst Agent.
Handles dataset profiling, code execution, and visualization generation.
"""

import logging
import os
import traceback
import uuid
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)

PALETTE = ["#4F46E5", "#7C3AED", "#EC4899", "#F59E0B", "#10B981", "#3B82F6"]
sns.set_theme(style="whitegrid", palette=PALETTE)


# ── Data Loading ──────────────────────────────────────────────────────────────


def load_dataframe(file_path: str) -> pd.DataFrame:
    """Load CSV or Excel file into a DataFrame."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(file_path, low_memory=False)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use CSV or Excel.")

    logger.info("Loaded dataset: %s rows × %s cols", *df.shape)
    return df


def get_dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Build a rich summary dict to pass to the LLM (avoids token overflow)."""
    summary: dict[str, Any] = {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": [],
        "sample": df.head(5).to_dict(orient="records"),
    }

    for col in df.columns:
        series = df[col]
        col_info: dict[str, Any] = {
            "name": col,
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_pct": round(series.isna().mean() * 100, 2),
            "unique_count": int(series.nunique()),
        }

        if pd.api.types.is_numeric_dtype(series):
            col_info["category"] = "numeric"
            col_info["stats"] = {
                "mean": round(float(series.mean()), 4) if not series.isna().all() else None,
                "std": round(float(series.std()), 4) if not series.isna().all() else None,
                "min": round(float(series.min()), 4) if not series.isna().all() else None,
                "max": round(float(series.max()), 4) if not series.isna().all() else None,
                "median": round(float(series.median()), 4) if not series.isna().all() else None,
            }
        elif pd.api.types.is_datetime64_any_dtype(series):
            col_info["category"] = "datetime"
            col_info["stats"] = {
                "min": str(series.min()),
                "max": str(series.max()),
            }
        else:
            col_info["category"] = "categorical"
            top = series.value_counts().head(5).to_dict()
            col_info["stats"] = {"top_values": {str(k): int(v) for k, v in top.items()}}

        summary["columns"].append(col_info)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()[:8]
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr().round(3).to_dict()
        summary["correlation_matrix"] = corr

    return summary


# ── Safe Code Execution ───────────────────────────────────────────────────────


def execute_viz_code(code: str, df: pd.DataFrame, output_dir: str) -> dict[str, Any]:
    """Execute LLM-generated visualization code in a restricted namespace."""
    output_path = os.path.join(output_dir, f"{uuid.uuid4().hex}.png")

    namespace: dict[str, Any] = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "output_path": output_path,
    }

    try:
        exec(compile(code, "<llm_generated>", "exec"), namespace)  # noqa: S102
        if os.path.exists(output_path):
            return {"success": True, "path": output_path}
        return {"success": False, "error": "Code ran but no figure was saved."}
    except Exception:
        plt.close("all")
        return {"success": False, "error": traceback.format_exc()}


# ── Fallback Visualizations ───────────────────────────────────────────────────


def generate_overview_charts(df: pd.DataFrame, output_dir: str) -> list[dict[str, str]]:
    """Generate a guaranteed set of overview charts without LLM code execution."""
    results: list[dict[str, str]] = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    # 1. Missing values
    if df.isnull().sum().sum() > 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        missing = df.isnull().mean() * 100
        missing = missing[missing > 0].sort_values(ascending=False)
        if not missing.empty:
            ax.barh(missing.index, missing.values, color="#EC4899")
            ax.set_xlabel("Missing (%)")
            ax.set_title("Missing Values by Column", fontweight="bold", pad=15)
            ax.grid(axis="x", alpha=0.3)
            path = os.path.join(output_dir, "missing_values.png")
            fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            results.append({"id": "missing_values", "title": "Missing Values", "path": path})

    # 2. Numeric distributions
    if numeric_cols:
        cols_to_plot = numeric_cols[:4]
        n = len(cols_to_plot)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
        if n == 1:
            axes = [axes]
        for ax, col in zip(axes, cols_to_plot, strict=False):
            data = df[col].dropna()
            ax.hist(data, bins=30, color="#4F46E5", edgecolor="white", alpha=0.85)
            ax.set_title(col, fontweight="bold")
            ax.set_xlabel("Value")
            ax.set_ylabel("Count")
            ax.grid(axis="y", alpha=0.3)
        fig.suptitle("Numeric Distributions", fontsize=14, fontweight="bold", y=1.02)
        path = os.path.join(output_dir, "distributions.png")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        results.append({"id": "distributions", "title": "Numeric Distributions", "path": path})

    # 3. Correlation heatmap
    if len(numeric_cols) >= 2:
        corr_cols = numeric_cols[:10]
        fig, ax = plt.subplots(figsize=(8, 6))
        corr = df[corr_cols].corr()
        mask = np.triu(np.ones_like(corr, dtype=bool))
        sns.heatmap(
            corr,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="RdYlBu_r",
            center=0,
            ax=ax,
            linewidths=0.5,
            square=True,
            cbar_kws={"shrink": 0.8},
        )
        ax.set_title("Correlation Matrix", fontweight="bold", pad=15)
        path = os.path.join(output_dir, "correlation.png")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        results.append({"id": "correlation", "title": "Correlation Matrix", "path": path})

    # 4. Top categorical bar chart
    if cat_cols:
        col = cat_cols[0]
        top_vals = df[col].value_counts().head(10)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(range(len(top_vals)), top_vals.values, color=PALETTE * 2)
        ax.set_xticks(range(len(top_vals)))
        ax.set_xticklabels(top_vals.index, rotation=35, ha="right")
        ax.set_title(f"Top Values — {col}", fontweight="bold", pad=15)
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.3)
        path = os.path.join(output_dir, "categorical_dist.png")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        results.append({"id": "categorical", "title": f"Distribution: {col}", "path": path})

    return results
