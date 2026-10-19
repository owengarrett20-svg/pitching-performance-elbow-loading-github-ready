"""Read-only views of verified, full-cohort Phase 2 research reports.

Rendering never fetches observations, fits models, or resamples athletes. The
conditional intervals and split sensitivity are computed by the offline study
workflow, then bound to the parent analysis with artifact checksums.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
import streamlit as st

TARGETS = {
    "pitch_speed_mph": ("Pitch speed", "mph"),
    "elbow_varus_moment": ("Peak internal elbow varus moment", "N·m"),
}
MODELS = {
    "dummy_mean": "Training-fold mean",
    "ridge_anthropometric": "Anthropometrics",
    "ridge_kinematic": "Kinematics",
    "ridge_combined": "Combined",
}
COLORS = {
    "dummy_mean": "#777777",
    "ridge_anthropometric": "#247BA0",
    "ridge_kinematic": "#A66321",
    "ridge_combined": "#137C66",
}
REQUIRED_FILES = {
    "phase2_model_metrics.csv",
    "phase2_comparisons.csv",
    "phase2_sensitivity_metrics.csv",
    "phase2_athlete_errors.csv",
    "phase2_model_spec.json",
}
METRIC_COLUMNS = {"target", "model", "n_pitches", "n_athletes", "mae", "rmse", "r2", "athlete_mae"}
COMPARISON_COLUMNS = {
    "target",
    "model",
    "reference",
    "metric",
    "estimate",
    "ci_low",
    "ci_high",
    "n_athletes",
    "bootstrap_replicates",
}


@dataclass(frozen=True)
class Phase2Reports:
    """Verified bytes and parsed tables from one completed offline study."""

    analysis: pd.DataFrame
    metrics: pd.DataFrame
    comparisons: pd.DataFrame
    sensitivity: pd.DataFrame
    athlete_errors: pd.DataFrame
    spec: dict
    metadata: dict
    verified_bytes: dict[str, bytes]


def _digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _safe_path(base: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("Invalid Phase 2 artifact path")
    relative = PurePosixPath(name)
    if (
        relative.is_absolute()
        or relative.as_posix() != name
        or any(part in {".", ".."} or ":" in part for part in relative.parts)
        or name == "."
    ):
        raise ValueError("Invalid Phase 2 artifact path")
    candidate = base
    if candidate.is_symlink():
        raise ValueError("Phase 2 artifact directory must not be a symlink")
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError("Phase 2 artifacts must not be symlinks")
    if not candidate.resolve().is_relative_to(base.resolve()):
        raise ValueError("Phase 2 artifact escapes its report directory")
    return candidate


def _object(contents: bytes, name: str) -> dict:
    try:
        value = json.loads(contents)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError(f"Invalid JSON in {name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object")  # noqa: TRY004 - serialized content
    return value


def _artifacts(metadata: dict, label: str) -> dict[str, str]:
    if metadata.get("status") != "completed":
        raise ValueError(f"{label} is not marked completed")
    artifacts = metadata.get("artifacts_sha256")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError(f"{label} has no artifact checksums")
    for name, digest in artifacts.items():
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"Invalid checksum in {label}: {name}")
    return artifacts


def _csv(payload: bytes, required: set[str], label: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(payload), dtype={"user": "string", "session_pitch": "string"})
    missing = required - set(frame)
    if missing:
        raise ValueError(f"{label} is missing columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError(f"{label} is empty")
    return frame


def _finite(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    for name in columns:
        values = pd.to_numeric(frame[name], errors="coerce")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{label} has invalid numeric values in {name}")


def _confidence_level(reports: Phase2Reports) -> float:
    """Read the reported interval level rather than invent a display default."""
    declared = reports.spec.get("bootstrap", {}).get("confidence_level")
    if "confidence_level" in reports.comparisons:
        values = pd.to_numeric(reports.comparisons.confidence_level, errors="coerce")
        if values.isna().any() or values.nunique() != 1:
            raise ValueError("Phase 2 comparisons must declare one common confidence level")
        value = float(values.iloc[0])
        if declared is not None and not np.isclose(value, float(declared)):
            raise ValueError(
                "Phase 2 interval confidence level differs from the study specification"
            )
    elif declared is not None:
        value = float(declared)
    else:
        raise ValueError("Phase 2 interval confidence level is not declared")
    if not np.isfinite(value) or not 0 < value < 1:
        raise ValueError("Phase 2 interval confidence level must be between zero and one")
    return value


def _validate_tables(reports: Phase2Reports) -> None:
    _confidence_level(reports)
    analysis = reports.analysis
    if (
        analysis[["session_pitch", "user"]].isna().any().any()
        or analysis.session_pitch.duplicated().any()
    ):
        raise ValueError("The analysis must have unique pitch identifiers and observed athlete IDs")
    expected_pairs = {(target, model) for target in TARGETS for model in MODELS}
    for label, frame in (("metrics", reports.metrics), ("sensitivity", reports.sensitivity)):
        if set(frame.target) != set(TARGETS) or set(frame.model) != set(MODELS):
            raise ValueError(
                f"Phase 2 {label} does not contain the declared targets and four models"
            )
        _finite(frame, ["n_pitches", "n_athletes", "mae", "rmse", "athlete_mae"], label)
        r2 = pd.to_numeric(frame.r2, errors="coerce")
        if np.isinf(r2.to_numpy(dtype=float)).any() or (frame.r2.notna() & r2.isna()).any():
            raise ValueError(f"Phase 2 {label} has invalid R² values")
        # Constant observed outcomes have undefined R²; its missing value is
        # reported as such while MAE/RMSE remain interpretable and finite.
        if (frame[["mae", "rmse", "athlete_mae"]] < 0).any().any():
            raise ValueError(f"Phase 2 {label} contains negative errors")
        if (frame.n_pitches > len(analysis)).any() or (
            frame.n_athletes > analysis.user.nunique()
        ).any():
            raise ValueError(f"Phase 2 {label} has counts exceeding the analysis cohort")
        if (frame[["n_pitches", "n_athletes"]] < 1).any().any():
            raise ValueError(f"Phase 2 {label} has invalid cohort counts")
    if (
        reports.metrics.duplicated(["target", "model"]).any()
        or set(zip(reports.metrics.target, reports.metrics.model)) != expected_pairs
    ):
        raise ValueError("Phase 2 metrics must have one row per declared target and model")
    sensitivity = reports.sensitivity
    _finite(sensitivity, ["partition_seed"], "sensitivity")
    if sensitivity.duplicated(["partition_seed", "target", "model"]).any():
        raise ValueError("Phase 2 sensitivity contains duplicate partitions")
    for _, partition in sensitivity.groupby("partition_seed"):
        if set(zip(partition.target, partition.model)) != expected_pairs:
            raise ValueError("Each sensitivity partition must evaluate all targets and models")
    comparisons = reports.comparisons
    _finite(
        comparisons,
        ["estimate", "ci_low", "ci_high", "n_athletes", "bootstrap_replicates"],
        "comparisons",
    )
    if not set(comparisons.target).issubset(TARGETS) or not set(comparisons.model).issubset(MODELS):
        raise ValueError("Phase 2 comparisons contain undeclared targets or models")
    if not set(comparisons.reference).issubset(MODELS) or not set(comparisons.metric).issubset(
        {"mae", "athlete_mae"}
    ):
        raise ValueError("Phase 2 comparisons contain unsupported references or metrics")
    if (comparisons.ci_low > comparisons.ci_high).any() or (
        comparisons.bootstrap_replicates < 1
    ).any():
        raise ValueError("Phase 2 comparison intervals are invalid")
    if comparisons.duplicated(["target", "model", "reference", "metric"]).any():
        raise ValueError("Phase 2 comparisons contain duplicate contrasts")
    primary = comparisons[
        (comparisons.model == "ridge_combined")
        & (comparisons.reference == "ridge_anthropometric")
        & (comparisons.metric == "athlete_mae")
    ]
    if set(primary.target) != set(TARGETS):
        raise ValueError("Phase 2 is missing the declared primary comparisons")
    if not set(reports.athlete_errors.target).issubset(TARGETS) or not set(
        reports.athlete_errors.model
    ).issubset(MODELS):
        raise ValueError("Phase 2 athlete errors contain undeclared targets or models")
    if not set(reports.athlete_errors.user).issubset(set(analysis.user)):
        raise ValueError("Phase 2 athlete errors reference athletes absent from the analysis")


def load_phase2_reports(report_dir: Path) -> Phase2Reports:
    """Load a completed, hash-bound study without changing files or computing models.

    ``FileNotFoundError`` means no Phase 2 completion marker exists. Other
    missing, stale, or malformed artifacts raise ``ValueError`` so the UI can
    suppress every Phase 2 result rather than display a partial study.
    """
    root = Path(report_dir)
    marker = _safe_path(root, "phase2/run_metadata.json")
    if not marker.is_file():
        raise FileNotFoundError("No completed Phase 2 study is available")
    try:
        parent = _object(_safe_path(root, "run_metadata.json").read_bytes(), "parent metadata")
        parent_hashes = _artifacts(parent, "Parent analysis")
        analysis_bytes = _safe_path(root, "analysis.csv").read_bytes()
        if parent_hashes.get("analysis.csv") != _digest(analysis_bytes):
            raise ValueError("analysis.csv does not match the completed parent analysis")
        child_bytes = marker.read_bytes()
        if parent_hashes.get("phase2/run_metadata.json") != _digest(child_bytes):
            raise ValueError("Phase 2 metadata does not match the completed parent analysis")
        child = _object(child_bytes, "Phase 2 metadata")
        hashes = _artifacts(child, "Phase 2 study")
        if child.get("analysis_sha256") != _digest(analysis_bytes):
            raise ValueError("Phase 2 predictions refer to a different analysis table")
        if not REQUIRED_FILES.issubset(hashes):
            raise ValueError("Phase 2 metadata is missing required result checksums")
        payloads = {}
        for name, expected in hashes.items():
            path = _safe_path(root / "phase2", name)
            if parent_hashes.get(f"phase2/{name}") != expected:
                raise ValueError(f"Parent analysis does not bind Phase 2 artifact: {name}")
            contents = path.read_bytes()
            if _digest(contents) != expected:
                raise ValueError(f"Phase 2 artifact checksum mismatch: {name}")
            payloads[name] = contents
        reports = Phase2Reports(
            analysis=_csv(analysis_bytes, {"session_pitch", "user"}, "analysis.csv"),
            metrics=_csv(payloads["phase2_model_metrics.csv"], METRIC_COLUMNS, "Phase 2 metrics"),
            comparisons=_csv(
                payloads["phase2_comparisons.csv"], COMPARISON_COLUMNS, "Phase 2 comparisons"
            ),
            sensitivity=_csv(
                payloads["phase2_sensitivity_metrics.csv"],
                METRIC_COLUMNS | {"partition_seed"},
                "Phase 2 sensitivity",
            ),
            athlete_errors=_csv(
                payloads["phase2_athlete_errors.csv"],
                {"target", "model", "user", "n_pitches", "mae"},
                "Phase 2 athlete errors",
            ),
            spec=_object(payloads["phase2_model_spec.json"], "Phase 2 model specification"),
            metadata=child,
            verified_bytes=payloads,
        )
        _validate_tables(reports)
        return reports
    except OSError as error:
        raise ValueError(f"Phase 2 artifacts are incomplete: {error.filename}") from error


def _comparison_plot(frame: pd.DataFrame, unit: str, metric: str, confidence_level: float) -> None:
    import matplotlib.pyplot as plt

    selected = frame[frame.metric == metric].copy()
    fig, axis = plt.subplots(figsize=(9, max(2.7, 0.6 * len(selected))), layout="constrained")
    for index, row in enumerate(selected.itertuples(index=False)):
        color = COLORS[row.model]
        axis.plot([row.ci_low, row.ci_high], [index, index], color=color, linewidth=2)
        axis.scatter([row.estimate], [index], color=color, s=45, zorder=3)
    axis.axvline(0, color="#666666", linestyle="--", linewidth=1)
    axis.set_yticks(
        range(len(selected)),
        [
            f"{MODELS[row.model]} − {MODELS[row.reference]}"
            for row in selected.itertuples(index=False)
        ],
    )
    axis.set_xlabel(
        f"Difference in {'equal-athlete' if metric == 'athlete_mae' else 'pooled pitch'} MAE ({unit})"
    )
    axis.set_title(
        f"Paired error differences with {100 * confidence_level:g}% conditional bootstrap intervals"
    )
    axis.grid(axis="x", alpha=0.2)
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def _sensitivity_plot(frame: pd.DataFrame, unit: str) -> None:
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(9, 3.8), layout="constrained")
    for model, name in MODELS.items():
        selected = frame[frame.model == model].sort_values("partition_seed")
        axis.plot(
            selected.partition_seed,
            selected.athlete_mae,
            marker="o",
            markersize=4,
            color=COLORS[model],
            label=name,
        )
    axis.set(
        xlabel="Athlete-partition seed",
        ylabel=f"Equal-athlete MAE ({unit})",
        title="Full pipeline refits under alternative athlete partitions",
    )
    axis.set_xticks(sorted(frame.partition_seed.unique()))
    axis.grid(axis="y", alpha=0.2)
    axis.legend(ncols=2, frameon=False)
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def render_phase2(report_dir: Path, selected_pitch_ids: Iterable[str] | None = None) -> None:
    """Display fixed full-cohort comparisons and explicitly scoped error details."""
    st.subheader("Phase 2 · Predictor groups and athlete-aware uncertainty")
    try:
        reports = load_phase2_reports(report_dir)
    except FileNotFoundError:
        st.info("Phase 2 reports have not been generated. The Phase 1 dashboard remains available.")
        st.code("uv run --frozen pitching phase2", language="bash")
        return
    except (ValueError, TypeError, KeyError) as error:
        st.warning(
            f"Phase 2 results are stale, incomplete, or invalid: {error}. No Phase 2 results are displayed."
        )
        return
    st.caption(
        f"Full-cohort exploratory follow-on: {len(reports.analysis):,} pitches from "
        f"{reports.analysis.user.nunique():,} athletes. Sidebar filters do not change "
        "the study scores, paired intervals, or partition sensitivity. "
        "The plan was frozen before these comparisons, after Phase 1 results were available; "
        "this is not preregistered or independent confirmation. All results were computed "
        "offline; viewing this page does not fit models or bootstrap data."
    )
    target = st.selectbox(
        "Phase 2 outcome",
        list(TARGETS),
        format_func=lambda name: f"{TARGETS[name][0]} ({TARGETS[name][1]})",
        key="phase2_target",
    )
    _, unit = TARGETS[target]
    st.subheader("Full-cohort held-out performance")
    st.caption(
        "Primary metric: equal-athlete MAE, giving each athlete equal weight. Pooled metrics give each pitch equal weight. Smaller MAE and RMSE indicate less prediction error."
    )
    selected_metrics = reports.metrics[reports.metrics.target == target].copy()
    selected_metrics["Predictor set"] = selected_metrics.model.map(MODELS)
    st.dataframe(
        selected_metrics[
            ["Predictor set", "n_pitches", "n_athletes", "athlete_mae", "mae", "rmse", "r2"]
        ].rename(
            columns={
                "athlete_mae": f"Equal-athlete MAE ({unit})",
                "mae": f"Pooled MAE ({unit})",
                "rmse": f"Pooled RMSE ({unit})",
                "r2": "Pooled R²",
            }
        ),
        hide_index=True,
    )
    st.subheader("Paired predictor-group comparisons")
    confidence_level = _confidence_level(reports)
    st.caption(
        f"{100 * confidence_level:g}% per-comparison intervals, without multiplicity adjustment. "
        "Primary contrast: combined − anthropometric ridge. Negative differences favor the candidate model. Intervals condition on the already-fitted, held-out predictions and resample athletes; they do not capture full model-training uncertainty. Secondary contrasts are exploratory, without multiplicity adjustment."
    )
    metric = st.radio(
        "Error weighting for conditional intervals",
        ["athlete_mae", "mae"],
        format_func=lambda value: (
            "Equal-athlete MAE (primary)"
            if value == "athlete_mae"
            else "Pooled pitch MAE (secondary)"
        ),
        key="phase2_interval_metric",
        horizontal=True,
    )
    comparisons = reports.comparisons[reports.comparisons.target == target]
    _comparison_plot(comparisons, unit, metric, confidence_level)
    st.dataframe(
        comparisons[comparisons.metric == metric][
            [
                "model",
                "reference",
                "metric",
                "estimate",
                "ci_low",
                "ci_high",
                "n_athletes",
                "bootstrap_replicates",
            ]
        ],
        hide_index=True,
    )
    st.subheader("Sensitivity to athlete partitions")
    st.caption(
        "Each seed reruns the complete grouped evaluation and training-fold preprocessing. These partitions reuse the same athletes: the range is a stability description, not a confidence interval or independent replication."
    )
    sensitivity = reports.sensitivity[reports.sensitivity.target == target]
    _sensitivity_plot(sensitivity, unit)
    ranges = (
        sensitivity.groupby("model", sort=False)
        .agg(
            partitions=("partition_seed", "nunique"),
            minimum_athlete_mae=("athlete_mae", "min"),
            maximum_athlete_mae=("athlete_mae", "max"),
        )
        .reset_index()
    )
    ranges["model"] = ranges.model.map(MODELS)
    st.dataframe(ranges, hide_index=True)
    with st.expander("Athlete-level held-out errors"):
        athletes = reports.athlete_errors[reports.athlete_errors.target == target]
        if selected_pitch_ids is not None:
            users = reports.analysis.loc[
                reports.analysis.session_pitch.isin(set(selected_pitch_ids)), "user"
            ]
            athletes = athletes[athletes.user.isin(users)]
        st.caption(
            "This detail table includes athletes represented by the sidebar's selected pitches. Each row still summarizes all eligible pitches for that athlete. It does not recompute intervals; single-athlete confidence intervals are not provided."
        )
        if athletes.empty:
            st.info("No athlete-level rows match the selected pitches.")
        else:
            st.dataframe(athletes, hide_index=True)
    with st.expander("Verified study specification and downloads"):
        st.json(reports.spec)
        for name in sorted(reports.verified_bytes):
            if name.endswith((".csv", ".json", ".md")):
                mime = (
                    "text/csv"
                    if name.endswith(".csv")
                    else "application/json"
                    if name.endswith(".json")
                    else "text/markdown"
                )
                st.download_button(
                    f"Download {name}",
                    data=reports.verified_bytes[name],
                    file_name=Path(name).name,
                    mime=mime,
                    key=f"phase2_download_{name}",
                )
    st.caption(
        "These are retrospective associations within the released source cohort. They do not establish causal mechanical effects, injury risk, or performance in an external population."
    )
