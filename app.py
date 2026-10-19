"""Explore local Phase 1 reports; never fetch data or fit models on rerun."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from pitching.runtime import configure_plot_cache
from pitching.trace_viewer import render_trace_lesson
from pitching.video_lab import render_video_lab

configure_plot_cache()

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_REVISION = "44b98dae05cceb016f080ab39d105c85b8639084"
SOURCE_URL = f"https://github.com/drivelineresearch/openbiomechanics/blob/{SOURCE_REVISION}"
VARIABLES = {
    "pitch_speed_mph": ("Pitch speed", "mph", "Reported pitch speed."),
    "elbow_varus_moment": (
        "Peak elbow varus moment",
        "N·m",
        "Reported peak joint moment; it is not tissue-specific loading or injury probability.",
    ),
    "max_shoulder_internal_rotational_velo": (
        "Peak shoulder internal rotation velocity",
        "deg/s",
        "Maximum shoulder internal rotation velocity over the delivery.",
    ),
    "max_rotation_hip_shoulder_separation": (
        "Peak hip–shoulder separation",
        "deg",
        "Maximum thorax–pelvis separation; this is not separation at foot contact.",
    ),
    "max_torso_rotational_velo": (
        "Peak torso rotation velocity",
        "deg/s",
        "Maximum torso axial (Z) rotation velocity over the delivery.",
    ),
}
IDENTIFIERS = {"user": "string", "session_pitch": "string", "playing_level": "string"}
ERROR_COLUMNS = {
    "session_pitch",
    "user",
    "fold",
    "target",
    "model",
    "observed",
    "predicted",
    "residual",
    "absolute_error",
}


def label(variable: str) -> str:
    """Human-readable label while retaining source names in exported tables."""
    if variable in VARIABLES:
        name, unit, _ = VARIABLES[variable]
        return f"{name} ({unit})"
    return variable


def read_csv(path: Path) -> pd.DataFrame:
    # Small POI reports are read on every rerun so replacing reports cannot leave
    # stale predictions in a process-wide cache. No network or training occurs.
    return pd.read_csv(path, dtype=IDENTIFIERS)


def require_reports(message: str) -> None:
    st.info(message)
    st.code("uv run pitching run", language="bash")


def distribution_plot(frame: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout="constrained")
    for axis, variable in zip(axes.flat, VARIABLES):
        values = pd.to_numeric(frame[variable], errors="coerce").dropna()
        values = values[np.isfinite(values)]
        if values.empty:
            axis.text(0.5, 0.5, "No observed values", ha="center", va="center")
        else:
            axis.hist(values, bins=min(20, max(1, len(values))), color="#247BA0", alpha=0.85)
        axis.set_xlabel(label(variable), fontsize=9)
        axis.set_ylabel("Pitches")
        axis.set_title(f"Observed n = {len(values)}", fontsize=10)
    axes.flat[-1].set_visible(False)
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def overview(frame: pd.DataFrame, report_dir: Path) -> None:
    st.subheader("Pitch-level analysis table")
    st.caption(
        "One row per recorded pitch. Repeated pitches from the same athlete are not independent observations."
    )
    displayed = ["session_pitch", "user", "playing_level", *VARIABLES]
    st.dataframe(frame[[name for name in displayed if name in frame]], hide_index=True)
    st.subheader("Data quality for the complete input dataset")
    st.caption(
        "These reports describe all input rows before dashboard filters. Missing values remain missing."
    )
    missing_path = report_dir / "missingness.csv"
    if missing_path.is_file():
        st.dataframe(pd.read_csv(missing_path), hide_index=True)
    else:
        require_reports("The missing-data report has not been generated.")
    audit_path = report_dir / "audit.json"
    if audit_path.is_file():
        with st.expander("Join audit and source provenance"):
            st.json(json.loads(audit_path.read_text()))
    else:
        require_reports("The join audit has not been generated.")


def explore(frame: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    st.subheader("Observed distributions")
    st.caption(
        "Histograms omit missing values and report the observed sample size separately for each variable."
    )
    distribution_plot(frame)
    st.subheader("Explore associations")
    left, right = st.columns(2)
    x = left.selectbox(
        "Horizontal axis", list(VARIABLES), index=4, format_func=label, key="explore_x"
    )
    y = right.selectbox("Vertical axis", list(VARIABLES), format_func=label, key="explore_y")
    paired = (
        frame[[x, y]].apply(pd.to_numeric, errors="coerce")
        if x != y
        else frame[[x]].apply(pd.to_numeric, errors="coerce")
    )
    paired = paired.replace([np.inf, -np.inf], np.nan).dropna()
    st.caption(
        f"{len(paired)} pitches have both selected values. Associations do not establish causation."
    )
    if not paired.empty:
        fig, axis = plt.subplots(figsize=(8, 4.5), layout="constrained")
        axis.scatter(paired[x], paired[y], alpha=0.65, s=22)
        axis.set(xlabel=label(x), ylabel=label(y))
        st.pyplot(fig, width="stretch")
        plt.close(fig)


def error_metrics(frame: pd.DataFrame) -> dict[str, float]:
    residual = frame["observed"] - frame["predicted"]
    denominator = float(((frame["observed"] - frame["observed"].mean()) ** 2).sum())
    return {
        "mae": float(residual.abs().mean()),
        "rmse": float(np.sqrt((residual**2).mean())),
        "r2": float(1 - (residual**2).sum() / denominator)
        if len(frame) > 1 and denominator > 0
        else float("nan"),
        "athlete_mae": float(residual.abs().groupby(frame["user"]).mean().mean()),
    }


def completed_model_report(report_dir: Path) -> bool:
    """Reject mixed artifacts after an interrupted or partially refreshed run."""
    marker = report_dir / "run_metadata.json"
    if not marker.is_file():
        require_reports(
            "No completed modeling run is available. Audit-only data can still be explored."
        )
        return False
    try:
        metadata = json.loads(marker.read_text())
        if metadata.get("status") != "completed":
            raise ValueError("run is not marked completed")
        for name in ("analysis.csv", "oof_predictions.csv", "model_metrics.csv"):
            path = report_dir / name
            expected = metadata.get("artifacts_sha256", {}).get(name)
            if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"{name} does not match the completed run")
    except (OSError, ValueError) as error:
        st.warning(f"Model results are stale or incomplete: {error}.")
        require_reports("Regenerate a complete report before interpreting model errors.")
        return False
    return True


def errors(frame: pd.DataFrame, report_dir: Path) -> None:
    import matplotlib.pyplot as plt

    st.subheader("Held-out model errors")
    st.caption(
        "Each displayed prediction comes from a fold that held out that athlete. "
        "Same-pitch biomechanics make these retrospective association models, not pre-pitch forecasts. "
        "Residual = observed − predicted; positive means underprediction."
    )
    if not completed_model_report(report_dir):
        return
    predictions_path = report_dir / "oof_predictions.csv"
    if not predictions_path.is_file():
        require_reports("Model reports are not available yet.")
        return
    predictions = read_csv(predictions_path)
    missing = ERROR_COLUMNS - set(predictions)
    if missing:
        require_reports(f"Model report is missing required columns: {', '.join(sorted(missing))}.")
        return
    # Filter pitch membership first; athlete/level filters must affect model errors.
    predictions = predictions[predictions["session_pitch"].isin(frame["session_pitch"])]
    if predictions.empty:
        st.info("No held-out predictions match the selected pitches.")
        return
    target = st.selectbox(
        "Prediction target",
        sorted(predictions["target"].dropna().unique()),
        format_func=label,
        key="error_target",
    )
    available = predictions[predictions["target"] == target]
    model = st.selectbox(
        "Baseline model", sorted(available["model"].dropna().unique()), key="error_model"
    )
    selected = available[available["model"] == model].copy()
    for column in ("observed", "predicted"):
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    selected = selected.replace([np.inf, -np.inf], np.nan).dropna(subset=["observed", "predicted"])
    if selected.empty:
        st.info("No finite held-out predictions match these filters.")
        return
    # Compute errors from actual pairs so dashboard summaries remain internally consistent.
    selected["residual"] = selected["observed"] - selected["predicted"]
    selected["absolute_error"] = selected["residual"].abs()
    metrics = error_metrics(selected)
    st.caption(
        f"Metrics below are recomputed for the selected subset, in {VARIABLES.get(target, ('', 'target units', ''))[1]} except R²."
    )
    columns = st.columns(4)
    columns[0].metric("Subset pitches", str(len(selected)))
    columns[1].metric("Subset MAE", f"{metrics['mae']:.2f}")
    columns[2].metric("Subset RMSE", f"{metrics['rmse']:.2f}")
    columns[3].metric(
        "Subset R²", f"{metrics['r2']:.3f}" if np.isfinite(metrics["r2"]) else "Undefined"
    )
    st.caption(
        f"Selected athletes: {selected['user'].nunique()}. Equal-athlete MAE: {metrics['athlete_mae']:.2f}; each athlete contributes equally."
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    axes[0].scatter(selected["observed"], selected["predicted"], alpha=0.65, s=22)
    low = float(selected[["observed", "predicted"]].min().min())
    high = float(selected[["observed", "predicted"]].max().max())
    if low == high:
        low, high = low - 0.5, high + 0.5
    axes[0].plot([low, high], [low, high], "--", color="gray")
    unit = VARIABLES.get(target, ("", "target units", ""))[1]
    axes[0].set(xlabel=f"Observed ({unit})", ylabel=f"Held-out prediction ({unit})")
    axes[1].scatter(selected["predicted"], selected["residual"], alpha=0.65, s=22)
    axes[1].axhline(0, linestyle="--", color="gray")
    axes[1].set(xlabel=f"Held-out prediction ({unit})", ylabel=f"Residual ({unit})")
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.dataframe(selected.sort_values("absolute_error", ascending=False), hide_index=True)
    metrics_path = report_dir / "model_metrics.csv"
    if metrics_path.is_file():
        with st.expander("Full cross-validation metrics before dashboard filtering"):
            st.caption(
                "These saved metrics use the complete eligible modeling sample. They do not change with the sidebar filters."
            )
            complete = pd.read_csv(metrics_path)
            if {"target", "model"}.issubset(complete):
                st.dataframe(
                    complete[(complete["target"] == target) & (complete["model"] == model)],
                    hide_index=True,
                )
            else:
                st.warning(
                    "The saved aggregate model report does not include target and model identifiers."
                )
    else:
        require_reports("The full cross-validation summary has not been generated.")


def definitions() -> None:
    st.subheader("Variable definitions")
    rows = [
        {"Source column": variable, "Variable": name, "Unit": unit, "Interpretation": description}
        for variable, (name, unit, description) in VARIABLES.items()
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.markdown(
        f"Definitions follow the pinned [upstream data dictionary]({SOURCE_URL}/baseball_pitching/data/data_dictionary.csv)."
    )
    st.write(
        "Peak variables summarize the delivery and may occur at different times. "
        "They do not show temporal sequencing, and no synchronized video is assumed. "
        "Group validation estimates transfer to held-out athletes in this dataset; "
        "it does not demonstrate transfer to MLB pitchers or clinical populations."
    )


def main(report_dir_override: Path | None = None, bundled_demo: bool = False) -> None:
    st.set_page_config(page_title="Pitching Performance and Elbow Loading", layout="wide")
    st.title("Pitching Performance and Elbow Loading")
    st.caption("OpenBiomechanics Project · Pitching data, motion examples, and measurement methods")
    if bundled_demo:
        st.caption(
            "Reference demonstration: checksum-verified, precomputed study outputs. "
            "Browser interactions do not download source data or retrain models."
        )
    st.info(
        "Elbow varus moment describes joint-level loading. This dashboard does not predict injury or provide clinical advice."
    )
    st.caption(
        f"Data: Driveline's OpenBiomechanics Project, CC BY-NC-SA 4.0 with an additional "
        f"professional-sports / financial-analysis affiliation restriction. Such use requires a specific "
        f"written paid license. [Read the pinned data license]({SOURCE_URL}/LICENSE-DATA.md)."
    )
    report_dir = (
        Path(
            report_dir_override
            or os.environ.get("PITCHING_REPORT_DIR", str(PROJECT_ROOT / "reports"))
        )
        .expanduser()
        .resolve()
    )
    source_path = report_dir / "analysis.csv"
    if not source_path.is_file():
        require_reports(
            "No local analysis report found. Run the pipeline from the project directory, then refresh this page."
        )
        if (PROJECT_ROOT / "assets/demo/manifest.json").is_file():
            st.info(
                "A verified reference demonstration is also available without regenerating reports."
            )
            st.code("uv run --frozen streamlit run streamlit_app.py", language="bash")
        return
    try:
        frame = read_csv(source_path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        st.error(f"Cannot read the local analysis report: {error}")
        require_reports("Regenerate the reports after checking the input files.")
        return
    required = {"session_pitch", "user", "playing_level", *VARIABLES}
    missing = required - set(frame)
    if missing:
        require_reports(
            f"Analysis report is missing required columns: {', '.join(sorted(missing))}."
        )
        return
    if (
        frame["session_pitch"].isna().any()
        or frame["session_pitch"].duplicated().any()
        or frame["user"].isna().any()
    ):
        st.error(
            "Analysis report must contain one row per nonmissing pitch identifier and a nonmissing athlete identifier. Review the join audit."
        )
        return
    st.sidebar.header("Filter recorded pitches")
    levels = st.sidebar.multiselect(
        "Playing level", sorted(frame["playing_level"].dropna().unique()), key="level_filter"
    )
    athletes = st.sidebar.multiselect(
        "Athlete ID", sorted(frame["user"].unique()), key="athlete_filter"
    )
    st.sidebar.caption(
        "An empty selection includes all values. Athlete IDs are pseudonymous source identifiers."
    )
    subset = frame.copy()
    if levels:
        subset = subset[subset["playing_level"].isin(levels)]
    if athletes:
        subset = subset[subset["user"].isin(athletes)]
    first, second = st.columns(2)
    first.metric("Pitches", str(len(subset)))
    second.metric("Athletes", str(subset["user"].nunique()))
    st.caption(
        f"Selected {len(subset)} of {len(frame)} pitches. Data are read from local pipeline artifacts; this app does not download data or fit models."
    )
    if subset.empty:
        st.info("No pitches match both sidebar filters. Clear a selection to continue.")
        return
    tabs = st.tabs(
        ["Overview", "Watch pitches", "Explore", "Model errors", "Definitions and limitations"]
    )
    try:
        with tabs[0]:
            overview(subset, report_dir)
        with tabs[1]:
            selected_pitch = render_video_lab(subset, PROJECT_ROOT)
            if selected_pitch is not None:
                render_trace_lesson(PROJECT_ROOT, selected_pitch)
        with tabs[2]:
            explore(subset)
        with tabs[3]:
            errors(subset, report_dir)
        with tabs[4]:
            definitions()
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        st.error(f"A local report could not be displayed: {error}")
        require_reports("Check the reports and regenerate them if incomplete.")


if __name__ == "__main__":
    main()
