"""Explore verified research reports; never fetch data or fit models on rerun."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from pitching.phase2_dashboard import render_phase2
from pitching.runtime import configure_plot_cache
from pitching.site_navigation import PAGE_SLUGS, PAGES, resolve_location
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


def navigate(page: str) -> None:
    """Button/radio callback; runs before the next render of the route widget."""
    if page not in PAGES:
        return
    st.session_state["app_page"] = page
    st.query_params["page"] = PAGE_SLUGS[page]
    st.session_state["_last_query_page"] = PAGE_SLUGS[page]


def _navigation_changed() -> None:
    navigate(st.session_state["app_page"])


def _open_athlete_report(athlete_id: str) -> None:
    st.session_state["report_requested_athlete"] = str(athlete_id)
    navigate("Athlete reports")


def _remember_filters() -> None:
    for name in ("level_filter", "athlete_filter"):
        if name in st.session_state:
            st.session_state[f"saved_{name}"] = list(st.session_state[name])


def _filter_pitches(frame: pd.DataFrame) -> pd.DataFrame:
    """Preserve filter choices between routes without changing the study cohort."""
    levels = sorted(frame["playing_level"].dropna().unique())
    athletes = sorted(frame["user"].unique())
    for key, available in (("level_filter", levels), ("athlete_filter", athletes)):
        if key not in st.session_state:
            st.session_state[key] = [
                value for value in st.session_state.get(f"saved_{key}", []) if value in available
            ]
    st.sidebar.header("Explore the recorded pitches")
    st.sidebar.multiselect("Playing level", levels, key="level_filter", on_change=_remember_filters)
    st.sidebar.multiselect(
        "Athlete ID", athletes, key="athlete_filter", on_change=_remember_filters
    )
    st.sidebar.caption(
        "Leave a selection empty to include everyone. IDs are pseudonymous. "
        "Study findings always use the full eligible cohort."
    )
    subset = frame.copy()
    if st.session_state["level_filter"]:
        subset = subset[subset["playing_level"].isin(st.session_state["level_filter"])]
    if st.session_state["athlete_filter"]:
        subset = subset[subset["user"].isin(st.session_state["athlete_filter"])]
    return subset


def _selected_counts(frame: pd.DataFrame, total: int) -> None:
    first, second = st.columns(2)
    first.metric("Pitches", str(len(frame)))
    second.metric("Athletes", str(frame["user"].nunique()))
    st.caption(f"Showing {len(frame)} of {total} recorded pitches.")


def _initialize_location(frame: pd.DataFrame) -> None:
    query_page, query_pitch = st.query_params.get("page"), st.query_params.get("pitch")
    page, pitch = resolve_location(query_page, query_pitch, frame["session_pitch"])
    if "app_page" not in st.session_state or query_page != st.session_state.get("_last_query_page"):
        st.session_state["app_page"] = page
        st.session_state["_last_query_page"] = query_page
    if st.session_state["app_page"] not in PAGES:
        st.session_state["app_page"] = PAGES[0]
    query_compare = st.query_params.get("compare")
    if query_compare != st.session_state.get("_last_query_compare"):
        _, comparison = resolve_location("explore", query_compare, frame["session_pitch"])
        st.session_state["active_comparison"] = comparison
        st.session_state["_last_query_compare"] = query_compare
        if comparison is not None:
            for key in ("level_filter", "athlete_filter"):
                st.session_state[f"saved_{key}"] = []
                st.session_state.pop(key, None)
    if query_pitch != st.session_state.get("_last_query_pitch"):
        st.session_state["active_pitch"] = pitch
        st.session_state["_last_query_pitch"] = query_pitch
        if pitch is not None:
            # An explicitly opened recorded-pitch link should be visible.
            for key in ("level_filter", "athlete_filter"):
                st.session_state[f"saved_{key}"] = []
                st.session_state.pop(key, None)


def main(report_dir_override: Path | None = None, bundled_demo: bool = False) -> None:
    st.set_page_config(
        page_title="Pitching Performance and Elbow Loading",
        page_icon="⚾",
        layout="wide",
    )
    st.markdown(
        """<style>
        [data-testid="stMainBlockContainer"] {max-width: 1220px; padding-top: 3.8rem;}
        h1 {letter-spacing: -.025em;}
        [data-testid="stCaptionContainer"] {line-height: 1.5;}
        @media (max-width: 640px) {
          [data-testid="stMainBlockContainer"] {padding-left: 1rem; padding-right: 1rem;}
          h1 {font-size: 1.9rem !important; line-height: 1.15 !important;}
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.title("Pitching Performance and Elbow Loading")
    st.caption(
        "Find a recorded pitch, inspect its movement and measurements, and follow the evidence."
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
    _initialize_location(frame)
    page = st.radio(
        "Choose a research view",
        PAGES,
        key="app_page",
        horizontal=True,
        on_change=_navigation_changed,
        label_visibility="collapsed",
    )
    st.caption(
        f"**Data use:** OBP restricts use by professional-sports and financial-analysis "
        f"affiliates; a specific written paid license is required. "
        f"[Full source terms]({SOURCE_URL}/LICENSE-DATA.md)."
    )
    subset = (
        _filter_pitches(frame)
        if page in {"Explore pitches", "Watch motion", "Study results"}
        else frame
    )
    try:
        if page == "Start here":
            from pitching.research_story import render_start

            render_start(frame, PROJECT_ROOT, report_dir, navigate)
        elif page == "Research brief":
            from pitching.research_brief import render_research_brief

            render_research_brief(PROJECT_ROOT, report_dir)
        elif page == "Explore pitches":
            if subset.empty:
                _selected_counts(subset, len(frame))
                st.info("No pitches match both sidebar filters. Clear a selection to continue.")
                return
            explore_view = st.radio(
                "Explore view",
                ["Find & compare pitches", "Charts & associations"],
                key="explore_view",
                horizontal=True,
            )
            if explore_view == "Find & compare pitches":
                from pitching.pitch_workspace import render_pitch_workspace

                selection = render_pitch_workspace(
                    subset,
                    PROJECT_ROOT,
                    selected_pitch_id=st.session_state.get("active_pitch"),
                    comparison_pitch_id=st.session_state.get("active_comparison"),
                    full_frame=frame,
                )
                chosen = None if selection is None else selection.primary
                if selection is not None:
                    st.session_state["active_comparison"] = selection.comparison
                    st.session_state["_last_query_compare"] = selection.comparison
                    st.query_params["compare"] = selection.comparison
            else:
                from pitching.pitch_explorer import render_pitch_explorer

                chosen = render_pitch_explorer(
                    subset,
                    full_frame=frame,
                    selected_pitch_id=st.session_state.get("active_pitch"),
                )
            if chosen is not None:
                st.session_state["active_pitch"] = chosen
                st.session_state["_last_query_pitch"] = chosen
                st.query_params["pitch"] = chosen
                st.caption(
                    "To share this recorded selection, copy the page address from your browser."
                )
                motion_action, report_action = st.columns(2)
                motion_action.button(
                    "See available motion examples", on_click=navigate, args=("Watch motion",)
                )
                athlete = frame.loc[frame.session_pitch.eq(chosen), "user"].iloc[0]
                report_action.button(
                    "Create this athlete's report",
                    on_click=_open_athlete_report,
                    args=(str(athlete),),
                )
        elif page == "Watch motion":
            if subset.empty:
                st.info("No pitches match both sidebar filters. Clear a selection to continue.")
                return
            requested = st.session_state.get("active_pitch")
            motion_view = st.radio(
                "Motion view",
                ["Interactive lab", "Video & measurement lessons"],
                key="motion_view",
                horizontal=True,
            )
            if motion_view == "Interactive lab":
                from pitching.motion_lab import render_motion_lab

                selected_pitch = render_motion_lab(subset, PROJECT_ROOT, requested)
            else:
                from pitching.video_lab import (
                    MotionAssetError,
                    load_motion_manifest,
                    matching_examples,
                )

                if requested is not None and requested != st.session_state.get("_motion_requested"):
                    try:
                        _, manifest = load_motion_manifest(PROJECT_ROOT)
                        available = matching_examples(subset, manifest["examples"])
                        match = [
                            entry for entry in available if entry["session_pitch"] == requested
                        ]
                        if match:
                            st.session_state["motion_study_pitch"] = match[0]
                        else:
                            st.info(
                                f"Pitch {requested} has no prepared marker replay in this view. "
                                "The player below identifies one of the available recorded examples."
                            )
                    except MotionAssetError:
                        pass  # The viewer supplies the specific asset message.
                    st.session_state["_motion_requested"] = requested
                selected_pitch = render_video_lab(subset, PROJECT_ROOT, compact=True)
                if selected_pitch is not None:
                    st.session_state["_motion_requested"] = selected_pitch
                    render_trace_lesson(PROJECT_ROOT, selected_pitch)
            if selected_pitch is not None:
                st.session_state["active_pitch"] = selected_pitch
                st.session_state["_last_query_pitch"] = selected_pitch
                st.query_params["pitch"] = selected_pitch
        elif page == "Athlete reports":
            from pitching.report_dashboard import render_report_builder

            requested = st.session_state.get("active_pitch")
            if requested is not None and requested != st.session_state.get("_reports_link_pitch"):
                match = frame.loc[frame.session_pitch.eq(requested), "user"]
                if len(match) == 1:
                    st.session_state["report_requested_athlete"] = str(match.iloc[0])
                st.session_state["_reports_link_pitch"] = requested
            render_report_builder(frame, report_dir, PROJECT_ROOT)
            athlete = st.session_state.get("report_athlete")
            pitches = frame.loc[frame.user.astype(str).eq(str(athlete)), "session_pitch"].astype(
                str
            )
            if not pitches.empty:
                actual = requested if requested in set(pitches) else min(pitches)
                st.session_state["active_pitch"] = actual
                st.session_state["_reports_link_pitch"] = actual
                st.session_state["_last_query_pitch"] = actual
                st.query_params["pitch"] = actual
        elif page == "New-data lab":
            from pitching.new_data_lab import render_new_data_lab

            render_new_data_lab(PROJECT_ROOT)
        elif page == "Study results":
            mode = st.radio(
                "Study depth",
                ["What changed?", "Prediction errors", "Detailed audit"],
                key="study_mode",
                horizontal=True,
            )
            if mode == "What changed?":
                from pitching.research_story import render_study_story

                render_study_story(report_dir)
            elif mode == "Prediction errors":
                _selected_counts(subset, len(frame))
                if subset.empty:
                    st.info("No pitches match both sidebar filters. Clear a selection to continue.")
                    return
                errors(subset, report_dir)
            else:
                render_phase2(report_dir, subset["session_pitch"].tolist())
        else:
            from pitching.collaboration_view import render_collaboration_methods

            render_collaboration_methods(report_dir, PROJECT_ROOT)
            with st.expander("Variable definitions and measurement conventions"):
                definitions()
            with st.expander("Data-quality reports and source tables"):
                overview(frame, report_dir)
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        st.error(f"A local report could not be displayed: {error}")
        require_reports("Check the reports and regenerate them if incomplete.")
    st.divider()
    st.caption(
        "Retrospective research. Elbow moment describes joint loading; injury risk is outside "
        "this study. Peaks do not establish causal movement effects."
    )
    st.caption(
        "Source: Driveline OpenBiomechanics Project. Original code: MIT. "
        "Data and derivatives: CC BY-NC-SA 4.0 plus the source affiliation restriction. "
        "[Research code](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready) "
        "· [Study report](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready/blob/main/docs/PHASE2_RESULTS.md)"
    )
    if bundled_demo:
        with st.expander("About this reference demonstration"):
            st.caption(
                "Reference demonstration: checksum-verified, precomputed study outputs. "
                "Browser interactions do not download source data, fit models, or resample athletes."
            )


if __name__ == "__main__":
    main()
