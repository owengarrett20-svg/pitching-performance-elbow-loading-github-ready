"""Reports for the planned, exploratory Phase 2 athlete-grouped comparisons.

This module only reads saved evaluation tables. It never fits models, selects
features, downloads measurements, or turns repeated partitions into replications.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pitching.runtime import configure_plot_cache

configure_plot_cache()

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TARGET_LABELS = {
    "pitch_speed_mph": ("Pitch speed", "mph"),
    "elbow_varus_moment": ("Elbow varus moment", "N·m"),
}
MODEL_LABELS = {
    "dummy_mean": "Training mean",
    "ridge_anthropometric": "Anthropometric",
    "ridge_kinematic": "Kinematic",
    "ridge_combined": "Combined",
}
METRIC_LABELS = {"athlete_mae": "Equal-athlete MAE", "mae": "Pooled pitch MAE"}
_COLORS = ["#70757A", "#7B55A4", "#C46728", "#007C91"]
_SCORE_COLUMNS = {"target", "model", "n_pitches", "n_athletes", "mae", "rmse", "r2", "athlete_mae"}


def _read_table(path: Path, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError(f"{path.name} must not be empty")
    return frame


def _require_keys(frame: pd.DataFrame, columns: list[str], expected: set[tuple], name: str) -> None:
    if frame.duplicated(columns).any():
        raise ValueError(f"{name} contains duplicate result keys")
    actual = set(frame[columns].itertuples(index=False, name=None))
    if actual != expected:
        raise ValueError(f"{name} does not contain exactly the planned result keys")


def _validate_tables(
    scores: pd.DataFrame, comparisons: pd.DataFrame, sensitivity: pd.DataFrame, plan: dict
) -> None:
    targets = list(plan["targets"])
    models = list(plan["models"])
    if not set(targets).issubset(TARGET_LABELS) or not set(models).issubset(MODEL_LABELS):
        raise ValueError("The reporting labels do not define every planned target and model")
    _require_keys(scores, ["target", "model"], {(t, m) for t in targets for m in models}, "Scores")
    numeric = ["n_pitches", "n_athletes", "mae", "rmse", "athlete_mae"]
    if not np.isfinite(scores[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Score counts and error metrics must be finite")
    if (scores[["n_pitches", "n_athletes"]] <= 0).any().any():
        raise ValueError("Score counts must be positive")
    if (scores[["mae", "rmse", "athlete_mae"]] < 0).any().any():
        raise ValueError("Absolute and squared-error metrics cannot be negative")
    if np.isinf(scores["r2"].to_numpy(dtype=float)).any():
        raise ValueError("R² may be undefined but cannot be infinite")
    if (scores.groupby("target")[["n_pitches", "n_athletes"]].nunique() > 1).any().any():
        raise ValueError("Models must describe the same eligible pitches and athletes per target")
    expected_comparisons = {
        (t, pair["model"], pair["reference"], metric)
        for t in targets
        for pair in plan["planned_comparisons"]
        for metric in plan["bootstrap"]["metrics"]
    }
    _require_keys(
        comparisons, ["target", "model", "reference", "metric"], expected_comparisons, "Comparisons"
    )
    if not np.isfinite(comparisons[["estimate", "ci_low", "ci_high"]].to_numpy()).all():
        raise ValueError("Comparison estimates and interval endpoints must be finite")
    if (comparisons["ci_low"] > comparisons["ci_high"]).any():
        raise ValueError("Comparison interval endpoints are reversed")
    if not comparisons["bootstrap_replicates"].eq(plan["bootstrap"]["n_resamples"]).all():
        raise ValueError("Saved bootstrap replicate counts disagree with the analysis plan")
    indexed = scores.set_index(["target", "model"])
    for row in comparisons.itertuples(index=False):
        candidate = indexed.loc[(row.target, row.model)]
        reference = indexed.loc[(row.target, row.reference)]
        expected_difference = candidate[row.metric] - reference[row.metric]
        if not np.isclose(row.estimate, expected_difference, atol=1e-9, rtol=1e-9):
            raise ValueError("Saved comparison is inconsistent with model-minus-reference scores")
        if row.n_athletes != candidate.n_athletes:
            raise ValueError("Saved comparison athlete count disagrees with model scores")
    _require_keys(
        sensitivity,
        ["partition_seed", "target", "model"],
        {(seed, t, m) for seed in plan["sensitivity_seeds"] for t in targets for m in models},
        "Partition sensitivity",
    )
    if not np.isfinite(sensitivity[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Partition sensitivity counts and error metrics must be finite")
    for target in targets:
        actual = sensitivity.loc[sensitivity.target.eq(target)]
        expected = indexed.loc[(target, models[0])]
        if (
            not actual.n_pitches.eq(expected.n_pitches).all()
            or not actual.n_athletes.eq(expected.n_athletes).all()
        ):
            raise ValueError("Partition sensitivity must reuse the same eligible sample")


def _format(value: Any) -> str:
    return f"{float(value):.3f}" if np.isfinite(float(value)) else "undefined"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
        + ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    )


def _comparison_label(model: str, reference: str) -> str:
    return f"{MODEL_LABELS[model]} − {MODEL_LABELS[reference]}"


def _primary_sensitivity(sensitivity: pd.DataFrame, plan: dict) -> pd.DataFrame:
    """Pair scores on the identical saved partition, without refitting anything."""
    primary = plan["primary_comparison"]
    wide = sensitivity.pivot(
        index=["target", "partition_seed"], columns="model", values=plan["primary_metric"]
    )
    return (wide[primary["model"]] - wide[primary["reference"]]).rename("difference").reset_index()


def _finish_figure(fig: plt.Figure, path: Path, caption: str) -> Path:
    fig.text(0.5, 0.045, caption, ha="center", va="center", fontsize=9)
    fig.text(
        0.5,
        0.015,
        "Source: Driveline OpenBiomechanics Project; CC BY-NC-SA 4.0 + affiliation restriction. "
        "See accompanying report for full terms.",
        ha="center",
        va="center",
        fontsize=7,
        color="#555555",
    )
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    return path


def _score_figure(scores: pd.DataFrame, plan: dict, path: Path) -> Path:
    models = list(plan["models"])
    fig, axes = plt.subplots(len(plan["targets"]), 2, figsize=(12, 8), squeeze=False)
    fig.subplots_adjust(left=0.18, right=0.97, top=0.90, bottom=0.16, hspace=0.50, wspace=0.30)
    for row, target in enumerate(plan["targets"]):
        target_name, unit = TARGET_LABELS[target]
        selected = scores.loc[scores.target.eq(target)].set_index("model").loc[models]
        for col, metric in enumerate(("athlete_mae", "mae")):
            ax = axes[row, col]
            ax.scatter(selected[metric], np.arange(len(models)), c=_COLORS[: len(models)], s=60)
            ax.set_yticks(np.arange(len(models)), [MODEL_LABELS[model] for model in models])
            ax.invert_yaxis()
            ax.set(xlabel=f"{METRIC_LABELS[metric]} ({unit}); lower is better", title=target_name)
            # Reserve room for the complete marker at the largest error value.
            maximum = float(selected[metric].max())
            ax.set_xlim(0, maximum * 1.12 if maximum > 0 else 1.0)
            ax.grid(axis="x", alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Held-out athlete prediction errors: planned feature sets", fontsize=14)
    return _finish_figure(
        fig,
        path,
        "Fixed out-of-fold scores. Equal-athlete MAE weights athletes equally; pooled MAE "
        "weights pitches equally. No intervals shown for absolute scores.",
    )


def _comparison_figure(comparisons: pd.DataFrame, plan: dict, path: Path) -> Path:
    fig, axes = plt.subplots(2, len(plan["targets"]), figsize=(14, 9), squeeze=False)
    fig.subplots_adjust(left=0.23, right=0.97, top=0.91, bottom=0.16, hspace=0.45, wspace=0.55)
    confidence = 100 * plan["bootstrap"]["confidence_level"]
    pairs = plan["planned_comparisons"]
    for col, target in enumerate(plan["targets"]):
        target_name, unit = TARGET_LABELS[target]
        for row, metric in enumerate(("athlete_mae", "mae")):
            ax = axes[row, col]
            for position, pair in enumerate(pairs):
                selected = comparisons.loc[
                    comparisons.target.eq(target)
                    & comparisons.metric.eq(metric)
                    & comparisons.model.eq(pair["model"])
                    & comparisons.reference.eq(pair["reference"])
                ].iloc[0]
                color = "#007C91" if pair == pairs[0] else "#67747D"
                ax.plot(
                    [selected.ci_low, selected.ci_high], [position, position], color=color, lw=2
                )
                ax.scatter(selected.estimate, position, color=color, s=34, zorder=3)
            ax.axvline(0, color="#888888", linestyle="--", linewidth=1)
            ax.set_yticks(
                np.arange(len(pairs)),
                [_comparison_label(pair["model"], pair["reference"]) for pair in pairs],
                fontsize=8,
            )
            ax.invert_yaxis()
            ax.set(
                title=f"{target_name}: {METRIC_LABELS[metric]}",
                xlabel=f"Candidate − reference ({unit}); negative favors candidate",
            )
            ax.grid(axis="x", alpha=0.15)
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Paired athlete-cluster comparisons", fontsize=14)
    return _finish_figure(
        fig,
        path,
        f"{confidence:g}% percentile intervals conditional on fixed out-of-fold errors. "
        "No model refitting within resamples; no multiplicity adjustment.",
    )


def _sensitivity_figure(differences: pd.DataFrame, plan: dict, path: Path) -> Path:
    fig, axes = plt.subplots(1, len(plan["targets"]), figsize=(12, 5), squeeze=False)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.84, bottom=0.24, wspace=0.30)
    for ax, target in zip(axes.flat, plan["targets"], strict=True):
        frame = differences.loc[differences.target.eq(target)].sort_values("partition_seed")
        name, unit = TARGET_LABELS[target]
        ax.plot(frame.partition_seed, frame.difference, marker="o", color="#007C91", lw=1.5)
        primary = frame.loc[frame.partition_seed.eq(plan["primary_seed"])]
        ax.scatter(
            primary.partition_seed,
            primary.difference,
            color="#C46728",
            marker="*",
            s=120,
            zorder=4,
            label="Primary partition",
        )
        ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
        ax.set(
            title=name,
            xlabel="Full-refit athlete partition seed",
            ylabel=f"Combined − anthropometric\nequal-athlete MAE ({unit}); negative is better",
            xticks=frame.partition_seed,
        )
        ax.legend(frameon=False, fontsize=8)
        ax.grid(alpha=0.15)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Sensitivity of the primary contrast to athlete partitioning", fontsize=14)
    return _finish_figure(
        fig,
        path,
        "Every partition refits all training pipelines. Partitions reuse the same athletes; "
        "they are not independent experiments or confidence intervals.",
    )


def write_phase2_report(report_dir: Path, plan: dict) -> list[Path]:
    """Write one Markdown report and three figures from saved Phase 2 results.

    ``report_dir`` contains the CSV artifacts produced by the Phase 2 engine,
    plus the exact frozen plan copied as ``phase2_plan.json`` by the CLI. Invalid,
    incomplete, or contradictory result tables fail before any output is written.
    Returned paths include the report first, followed by the three PNG figures.
    """
    report_dir = Path(report_dir)
    scores = _read_table(report_dir / "phase2_model_metrics.csv", _SCORE_COLUMNS)
    comparisons = _read_table(
        report_dir / "phase2_comparisons.csv",
        {
            "target",
            "model",
            "reference",
            "metric",
            "estimate",
            "ci_low",
            "ci_high",
            "n_athletes",
            "bootstrap_replicates",
        },
    )
    sensitivity = _read_table(
        report_dir / "phase2_sensitivity_metrics.csv", _SCORE_COLUMNS | {"partition_seed"}
    )
    _validate_tables(scores, comparisons, sensitivity, plan)
    differences = _primary_sensitivity(sensitivity, plan)
    primary = plan["primary_comparison"]
    selected_primary = comparisons.loc[
        comparisons.model.eq(primary["model"])
        & comparisons.reference.eq(primary["reference"])
        & comparisons.metric.eq(plan["primary_metric"])
    ].set_index("target")
    bootstrap = plan["bootstrap"]
    confidence = 100 * bootstrap["confidence_level"]
    abstract_results = []
    interpretation = []
    count_rows = []
    for target in plan["targets"]:
        name, unit = TARGET_LABELS[target]
        row = selected_primary.loc[target]
        count = scores.loc[scores.target.eq(target)].iloc[0]
        count_rows.append([name, int(count.n_pitches), int(count.n_athletes)])
        abstract_results.append(
            f"{name}: combined-minus-anthropometric equal-athlete MAE "
            f"{_format(row.estimate)} {unit} (conditional {confidence:g}% interval "
            f"{_format(row.ci_low)} to {_format(row.ci_high)})."
        )
        direction = "lower" if row.estimate < 0 else "higher" if row.estimate > 0 else "equal"
        zero = "includes zero" if row.ci_low <= 0 <= row.ci_high else "does not include zero"
        interpretation.append(
            f"- **{name}:** the combined model had {direction} observed held-out equal-athlete "
            f"MAE than the anthropometric model; the signed difference was "
            f"{_format(row.estimate)} {unit}. Its conditional interval {zero}. "
            "This describes the saved prediction errors and does not establish a causal "
            "benefit of changing mechanics or an independent confirmation of model superiority."
        )
    model_rows = []
    for target in plan["targets"]:
        name, unit = TARGET_LABELS[target]
        for model in plan["models"]:
            row = scores.loc[scores.target.eq(target) & scores.model.eq(model)].iloc[0]
            model_rows.append(
                [
                    f"{name} ({unit})",
                    MODEL_LABELS[model],
                    int(row.n_pitches),
                    int(row.n_athletes),
                    _format(row.athlete_mae),
                    _format(row.mae),
                    _format(row.rmse),
                    _format(row.r2),
                ]
            )
    primary_rows = []
    contrast_rows = []
    for target in plan["targets"]:
        name, unit = TARGET_LABELS[target]
        row = selected_primary.loc[target]
        primary_rows.append(
            [
                f"{name} ({unit})",
                _format(row.estimate),
                f"[{_format(row.ci_low)}, {_format(row.ci_high)}]",
                int(row.n_athletes),
            ]
        )
        for pair in plan["planned_comparisons"]:
            for metric in bootstrap["metrics"]:
                row = comparisons.loc[
                    comparisons.target.eq(target)
                    & comparisons.model.eq(pair["model"])
                    & comparisons.reference.eq(pair["reference"])
                    & comparisons.metric.eq(metric)
                ].iloc[0]
                contrast_rows.append(
                    [
                        f"{name} ({unit})",
                        _comparison_label(pair["model"], pair["reference"]),
                        METRIC_LABELS[metric],
                        _format(row.estimate),
                        f"[{_format(row.ci_low)}, {_format(row.ci_high)}]",
                    ]
                )
    partition_rows = []
    primary_ranges = []
    for target in plan["targets"]:
        name, unit = TARGET_LABELS[target]
        difference = differences.loc[differences.target.eq(target), "difference"]
        primary_ranges.append(
            f"- {name}: primary equal-athlete MAE contrast ranged from "
            f"{_format(difference.min())} to {_format(difference.max())} {unit}; "
            f"negative in {int(difference.lt(0).sum())} of {len(difference)} saved partitions."
        )
        for model in plan["models"]:
            frame = sensitivity.loc[sensitivity.target.eq(target) & sensitivity.model.eq(model)]
            partition_rows.append(
                [
                    f"{name} ({unit})",
                    MODEL_LABELS[model],
                    f"{_format(frame.athlete_mae.min())} to {_format(frame.athlete_mae.max())}",
                    f"{_format(frame.mae.min())} to {_format(frame.mae.max())}",
                ]
            )
    source_commit = plan["source_commit"]
    source_url = f"https://github.com/drivelineresearch/openbiomechanics/tree/{source_commit}"
    license_url = (
        "https://github.com/drivelineresearch/openbiomechanics/blob/"
        f"{source_commit}/LICENSE-DATA.md"
    )
    sections = [
        "# Phase 2: Feature-set comparisons and conditional athlete-level uncertainty",
        "## Abstract",
        (
            "**Question.** Do fixed kinematic summaries add predictive information beyond age, "
            "mass, and height for pitch speed and peak internal elbow varus moment in held-out "
            "athletes from this source cohort?"
        ),
        (
            f"**Methods.** Four planned baselines share {plan['n_splits']} shuffled athlete-grouped "
            f"folds (primary seed {plan['primary_seed']}). Ridge alpha is fixed at "
            f"{plan['ridge_alpha']:g}. Primary comparisons use equal-athlete MAE, with "
            f"{bootstrap['n_resamples']:,} paired athlete-cluster resamples of fixed out-of-fold "
            f"errors and {len(plan['sensitivity_seeds'])} full-refit partition sensitivity analyses."
        ),
        "**Results.** " + " ".join(abstract_results),
        (
            "**Interpretation.** This is an exploratory follow-on after viewing Phase 1 results, "
            "not a preregistered study or independent confirmatory evidence. The outcomes are "
            "performance and joint loading, with no injury labels or injury prediction."
        ),
        "## Question, plan, and eligible sample",
        (
            "The exact [frozen comparison plan](phase2_plan.json) was recorded before these "
            "Phase 2 comparisons, after the Phase 1 results had already been viewed. Both "
            "outcomes and all planned contrasts are reported; no features, alpha, or winning "
            "outcome were chosen by scoring these comparisons."
        ),
        _table(["Outcome", "Eligible pitches", "Eligible athletes"], count_rows),
        (
            "Missing or nonfinite outcomes are omitted separately by target, never imputed "
            "or replaced from duplicate metadata. No outliers are removed. Model counts above "
            "are the actual saved eligible counts, not expected sample-size constants."
        ),
        "## Methods",
        (
            "The training-mean baseline is compared with anthropometric-only, kinematic-only, "
            "and combined ridge models. Anthropometrics are age, body mass, and height. "
            "Kinematics are peak shoulder internal rotation velocity, peak thorax–pelvis "
            "separation, and peak torso rotational velocity. Both outcomes, IDs, and filenames "
            "are excluded from every predictor set. These same-pitch summaries support "
            "retrospective prediction, not pre-pitch forecasting."
        ),
        (
            "Athletes remain wholly within one held-out fold, with the same partitions across "
            "targets and models. Missing predictor handling and scaling are fitted only on "
            "training rows with observed targets in each fold. A model is refitted inside every "
            "fold and for every partition seed; no hyperparameter search is performed."
        ),
        (
            "Equal-athlete MAE averages absolute errors within athlete, then averages athletes "
            "equally. Pooled pitch MAE weights every pitch equally. The primary contrast is "
            "**combined minus anthropometric equal-athlete MAE**, separately for both outcomes. "
            "Negative contrasts favor the candidate model. RMSE and R² are descriptive secondary "
            "scores; R² is undefined when the observed outcome has no variance."
        ),
        (
            f"The paired cluster percentile bootstrap draws athlete IDs with replacement "
            f"{bootstrap['n_resamples']:,} times (seed {bootstrap['seed']}), retaining all eligible "
            "pitches and each sampled athlete's multiplicity. Identical athlete draws are used "
            "for paired models. Percentile intervals are computed separately for equal-athlete "
            "and pooled MAE contrasts."
        ),
        (
            "**Interval scope:** intervals are conditional on fixed out-of-fold predictions "
            "and the observed source cohort. There is no refitting within bootstrap resamples. "
            "They exclude model-refitting, model-selection, and full training-set uncertainty. "
            "Overlapping cross-validation training folds also limit a sampling interpretation "
            "of these error intervals. No p-values, formal significance threshold, or "
            "multiplicity-adjusted confirmation are reported."
        ),
        "## All model scores",
        _table(
            [
                "Outcome",
                "Model",
                "Pitches",
                "Athletes",
                "Equal-athlete MAE",
                "Pooled MAE",
                "RMSE",
                "R²",
            ],
            model_rows,
        ),
        "Error scores retain the outcome's stated units. R² is dimensionless.",
        "![Held-out errors by planned model](figures/phase2_model_scores.png)",
        "## Primary paired comparisons",
        (
            f"Conditional {confidence:g}% paired athlete-cluster percentile intervals; "
            "candidate minus reference, with negative values favoring the combined model."
        ),
        _table(
            [
                "Outcome",
                "Combined − anthropometric equal-athlete MAE",
                "Conditional interval",
                "Athletes",
            ],
            primary_rows,
        ),
        "\n".join(interpretation),
        "## Every planned contrast",
        (
            "Both error weightings are shown for all six planned model pairs and both outcomes. "
            "These exploratory intervals are not adjusted for multiple comparisons."
        ),
        _table(
            ["Outcome", "Candidate − reference", "Metric", "Difference", "Conditional interval"],
            contrast_rows,
        ),
        "![Paired contrasts with conditional intervals](figures/phase2_paired_contrasts.png)",
        "## Partition sensitivity",
        "All training pipelines are refitted for seeds "
        + ", ".join(str(seed) for seed in plan["sensitivity_seeds"])
        + ". "
        "The same athletes and pitches recur across partitions. These are descriptive "
        "sensitivity analyses, not independent experiments, additional independent cohorts, "
        "or confidence intervals. No standard error is calculated by treating partition "
        "seeds as independent replicates.",
        "\n".join(primary_ranges),
        _table(["Outcome", "Model", "Equal-athlete MAE range", "Pooled MAE range"], partition_rows),
        "![Full-refit partition sensitivity](figures/phase2_partition_sensitivity.png)",
        "## Biomechanical and statistical limits",
        (
            "A lower prediction error identifies an association in this dataset, not a causal "
            "mechanical intervention. Peak variables need not occur at the same instant and "
            "do not establish sequencing or energy transfer. Internal net elbow varus moment "
            "is not tissue-specific force, injury probability, or a safe threshold. There are "
            "no injury outcomes. The small, predominantly collegiate fastball cohort and its "
            "measurement setting limit transport to professional players, other pitch types, "
            "and future sessions. No new camera alignment, video-derived moment estimation, "
            "or external validation was performed in this phase."
        ),
        (
            "The next defensible extension is an appropriately licensed independent or "
            "longitudinal cohort. Model tuning would require a separate, nested athlete-grouped "
            "evaluation; it should not reuse these displayed errors as an unbiased test set."
        ),
        "## Reproducibility and source attribution",
        (
            "This report only reads saved evaluation artifacts; it does not fit models or "
            "download data. Reproduction settings are in [phase2_plan.json](phase2_plan.json). "
            "Machine-readable scores, paired contrasts, per-athlete errors, partition results, "
            "and provenance accompany this report. Numeric display is rounded to three "
            "decimals; saved CSV files preserve computational precision."
        ),
        (
            f"Source: Driveline Baseball Research & Development and Kyle Boddy, "
            f"[The OpenBiomechanics Project]({source_url}), commit `{source_commit}`. "
            "Adaptations by this project include joins, feature-set comparisons, grouped "
            "evaluation, conditional bootstrap summaries, and figures. No endorsement is implied."
        ),
        (
            f"Data and derived reports/figures retain [CC BY-NC-SA 4.0]"
            f"(https://creativecommons.org/licenses/by-nc-sa/4.0/) plus the "
            f"[additional upstream affiliation restriction]({license_url}):"
        ),
        (
            "> Any employee or contractor employed by, associated with, or a significant "
            "shareholder of a professional sports organization or financial analysis firm is "
            "forbidden to use The OpenBiomechanics Project data for any use whatsoever."
        ),
        (
            "A specific written paid license is required for such use. The original software's "
            "MIT license does not override data and derived-material restrictions."
        ),
    ]
    figures_dir = report_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figures = [
        _score_figure(scores, plan, figures_dir / "phase2_model_scores.png"),
        _comparison_figure(comparisons, plan, figures_dir / "phase2_paired_contrasts.png"),
        _sensitivity_figure(differences, plan, figures_dir / "phase2_partition_sensitivity.png"),
    ]
    report_path = report_dir / "phase2_report.md"
    report_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return [report_path, *figures]
