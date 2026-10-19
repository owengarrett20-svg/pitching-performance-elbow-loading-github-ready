"""Descriptive figures; repeated pitches are not independent athletes."""

from __future__ import annotations

from pathlib import Path

from pitching.runtime import configure_plot_cache

configure_plot_cache()

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pitching.data import VARIABLES


def _label(column: str) -> str:
    name, unit = VARIABLES[column]
    return f"{name}\n({unit})"


def exploratory_plots(data: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Render measured distributions and associations without inferential claims."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    colors = ["#007C91", "#C24F25", "#3D6E43", "#8755A4", "#C08B16"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout="constrained")
    for ax, (column, (name, unit)), color in zip(axes.flat, VARIABLES.items(), colors):
        values = data[column].dropna()
        ax.hist(values, bins="auto", color=color, edgecolor="white", alpha=0.85)
        ax.set(
            xlabel=f"{name}\n({unit})",
            ylabel="Pitches",
            title=f"n={len(values)} observed; missing={data[column].isna().sum()}",
        )
        ax.spines[["top", "right"]].set_visible(False)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0,
        0.9,
        f"{len(data)} pitches / {data.user.nunique()} athletes\n\n"
        "Repeated pitches are clustered.\n"
        "Distributions describe this sample.\n"
        "No missing observations are filled.\n"
        "Internal joint moment ≠ injury risk.",
        va="top",
        transform=axes.flat[-1].transAxes,
    )
    fig.suptitle("Pitching measurements: trial-level distributions", fontsize=15)
    path = output_dir / "distributions.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    columns = ["pitch_speed_mph", "elbow_varus_moment"]
    complete = data.dropna(subset=columns)
    athlete_means = complete.groupby("user")[columns].mean()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, frame, title in (
        (axes[0], complete, f"Individual pitches (n={len(complete)})"),
        (axes[1], athlete_means, f"Athlete means (n={len(athlete_means)})"),
    ):
        ax.scatter(
            frame.pitch_speed_mph,
            frame.elbow_varus_moment,
            s=24,
            alpha=0.6,
            color=colors[0],
            edgecolors="none",
        )
        ax.set(xlabel=_label(columns[0]), ylabel=_label(columns[1]), title=title)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Performance and net elbow moment: descriptive associations", fontsize=13)
    path = output_dir / "velocity_elbow.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    predictors = list(VARIABLES)[2:]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout="constrained")
    for row, outcome in enumerate(columns):
        for col, predictor in enumerate(predictors):
            ax = axes[row, col]
            ax.scatter(
                data[predictor],
                data[outcome],
                s=15,
                alpha=0.4,
                color=colors[col + 2],
                edgecolors="none",
            )
            ax.set(xlabel=_label(predictor), ylabel=_label(outcome))
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Peak kinematics and outcomes (pitches repeat within athletes)", fontsize=14)
    path = output_dir / "kinematics_vs_outcomes.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)
    return paths


def error_plots(predictions: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Use held-out predictions only; do not show training-fit performance."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for target in predictions.target.unique():
        frame = predictions.loc[(predictions.target == target) & (predictions.model == "ridge")]
        if frame.empty:
            continue
        name, unit = VARIABLES[target]
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
        lo = float(min(frame.observed.min(), frame.predicted.min()))
        hi = float(max(frame.observed.max(), frame.predicted.max()))
        axes[0].scatter(frame.observed, frame.predicted, alpha=0.45, s=20, color="#007C91")
        axes[0].plot([lo, hi], [lo, hi], "--", color="gray", linewidth=1)
        axes[0].set(xlabel=f"Observed ({unit})", ylabel=f"Held-out prediction ({unit})")
        axes[1].scatter(frame.predicted, frame.residual, alpha=0.45, s=20, color="#C24F25")
        axes[1].axhline(0, linestyle="--", color="gray", linewidth=1)
        axes[1].set(xlabel=f"Held-out prediction ({unit})", ylabel=f"Observed − predicted ({unit})")
        fig.suptitle(f"{name}: ridge, athlete-held-out errors", fontsize=13)
        path = output_dir / f"errors_{target}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path)
    return paths


def descriptive_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable, (name, unit) in VARIABLES.items():
        values = data[variable].dropna()
        summary = values.describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
        rows.append(
            {
                "variable": variable,
                "definition": name,
                "unit": unit,
                "n_missing": int(data[variable].isna().sum()),
                **summary,
            }
        )
    return pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
