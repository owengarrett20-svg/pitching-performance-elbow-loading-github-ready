"""A short, read-only introduction to the verified pitching research.

Displayed findings come from the completed study tables. The story does not fit
models, resample errors, infer camera measurements, or change the study cohort.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from pitching.phase2_dashboard import Phase2Reports, load_phase2_reports
from pitching.video_lab import (
    MotionAssetError,
    load_motion_manifest,
    matching_examples,
    verified_asset,
)

OUTCOMES = {
    "pitch_speed_mph": ("Pitch speed", "mph"),
    "elbow_varus_moment": ("Elbow loading", "N·m"),
}
MODEL_NAMES = {
    "dummy_mean": "Training mean",
    "ridge_anthropometric": "Age + body size",
    "ridge_kinematic": "Rotational measures",
    "ridge_combined": "Age/body size + rotation",
}
ERROR_HELP = (
    "For each athlete, average the absolute difference between observed and predicted values. "
    "Then average those athlete errors equally. Lower values mean closer predictions."
)


@dataclass(frozen=True)
class StorySummary:
    """One primary comparison, retaining its units and uncertainty scope."""

    target: str
    title: str
    unit: str
    body_error: float
    combined_error: float
    difference: float
    low: float
    high: float
    level: float
    athletes: int
    pitches: int
    resamples: int

    @property
    def interval_includes_zero(self) -> bool:
        return self.low <= 0 <= self.high

    @property
    def finding(self) -> str:
        if self.difference < 0:
            observation = (
                "Adding the selected rotational measures lowered observed prediction error "
                f"by {abs(self.difference):.2f} {self.unit}."
            )
        elif self.difference > 0:
            observation = (
                "Adding the selected rotational measures increased observed prediction error "
                f"by {self.difference:.2f} {self.unit}."
            )
        else:
            observation = "The two models have the same observed average prediction error."
        if self.interval_includes_zero:
            return (
                f"{observation} The conditional interval includes zero, so their added "
                "predictive value remains uncertain in this cohort."
            )
        return (
            f"{observation} This is an association within the released study cohort; "
            "it does not establish the effect of changing a pitcher's movement."
        )


def primary_story_summary(reports: Phase2Reports, target: str) -> StorySummary:
    """Describe the declared comparison without inventing values or a favorable finding."""
    if target not in OUTCOMES:
        raise ValueError("Unknown story outcome")
    selected = reports.metrics.loc[reports.metrics.target.eq(target)].set_index("model")
    body = selected.loc["ridge_anthropometric"]
    combined = selected.loc["ridge_combined"]
    contrasts = reports.comparisons.loc[
        reports.comparisons.target.eq(target)
        & reports.comparisons.model.eq("ridge_combined")
        & reports.comparisons.reference.eq("ridge_anthropometric")
        & reports.comparisons.metric.eq("athlete_mae")
    ]
    if len(contrasts) != 1:
        raise ValueError("The story requires one verified primary comparison per outcome")
    comparison = contrasts.iloc[0]
    difference = float(combined.athlete_mae - body.athlete_mae)
    if not np.isclose(difference, float(comparison.estimate), atol=1e-9, rtol=1e-9):
        raise ValueError("The saved comparison differs from its model errors")
    if body.n_pitches != combined.n_pitches or body.n_athletes != combined.n_athletes:
        raise ValueError("The compared models must describe the same eligible cohort")
    level = comparison.get(
        "confidence_level", reports.spec.get("bootstrap", {}).get("confidence_level")
    )
    if level is None or not np.isfinite(level) or not 0 < float(level) < 1:
        raise ValueError("The conditional interval level is unavailable")
    title, unit = OUTCOMES[target]
    return StorySummary(
        target=target,
        title=title,
        unit=unit,
        body_error=float(body.athlete_mae),
        combined_error=float(combined.athlete_mae),
        difference=difference,
        low=float(comparison.ci_low),
        high=float(comparison.ci_high),
        level=float(level),
        athletes=int(body.n_athletes),
        pitches=int(body.n_pitches),
        resamples=int(comparison.bootstrap_replicates),
    )


def preview_example(frame: pd.DataFrame, examples: list[dict]) -> dict | None:
    """Use the middle-speed available example, after matching both source identifiers."""
    entries = matching_examples(frame, examples)
    if not entries:
        return None
    speeds = (
        frame.assign(
            session_pitch=frame.session_pitch.astype(str),
            pitch_speed_mph=pd.to_numeric(frame.pitch_speed_mph, errors="coerce"),
        )
        .set_index("session_pitch")["pitch_speed_mph"]
        .to_dict()
    )
    finite = [entry for entry in entries if np.isfinite(speeds.get(entry["session_pitch"], np.nan))]
    entries = sorted(
        finite or entries,
        key=lambda entry: (speeds.get(entry["session_pitch"], np.inf), entry["session_pitch"]),
    )
    return entries[len(entries) // 2]


def _verified_reports(report_dir: Path) -> Phase2Reports | None:
    try:
        return load_phase2_reports(report_dir)
    except FileNotFoundError:
        st.info("The completed comparison study is not available in this copy yet.")
    except (OSError, ValueError, TypeError, KeyError) as error:
        st.warning(f"The study summary could not be verified: {error}. Findings are hidden.")
    return None


def _render_preview(frame: pd.DataFrame, project_root: Path) -> None:
    with st.container(border=True):
        st.markdown("**A recorded delivery, measured in 3D**")
        try:
            directory, manifest = load_motion_manifest(project_root)
            entry = preview_example(frame, manifest["examples"])
            if entry is None:
                st.info("No prepared marker example matches this set of recorded pitches.")
                return
            movie = verified_asset(
                directory, entry["animation_file"], entry["animation_sha256"], ".mp4"
            )
            st.video(str(movie), format="video/mp4")
            observed = frame.loc[frame.session_pitch.astype(str).eq(entry["session_pitch"])].iloc[0]
            speed = pd.to_numeric(pd.Series([observed.pitch_speed_mph]), errors="coerce").iloc[0]
            speed_label = f" · {speed:.1f} mph" if pd.notna(speed) and np.isfinite(speed) else ""
            st.caption(
                f"Pitch {entry['session_pitch']}{speed_label} · measured skin markers · "
                f"{entry['playback_rate']:g}× recorded speed."
            )
            st.caption(
                "This is an animation of observed markers. Guide links are not anatomical "
                "joint centers. Marker and processed-signal clocks have not been aligned here."
            )
        except (OSError, ValueError, KeyError, MotionAssetError):
            st.info(
                "The verified motion preview is unavailable. The research views remain accessible."
            )


def _summary_cards(summary: StorySummary) -> None:
    first, second = st.columns(2)
    first.metric(
        "Age + body size",
        f"{summary.body_error:.2f} {summary.unit}",
        help=ERROR_HELP,
    )
    second.metric(
        "Add rotational measures",
        f"{summary.combined_error:.2f} {summary.unit}",
        help=ERROR_HELP,
    )
    st.caption(
        "Average prediction error per athlete. Age/body size includes age, mass, and height; "
        "rotational measures include shoulder speed, torso speed, and peak hip–shoulder separation."
    )
    st.write(summary.finding)
    st.caption(
        f"Combined − age/body-size error: {summary.difference:+.3f} {summary.unit}. "
        f"Conditional {100 * summary.level:g}% interval: "
        f"{summary.low:+.3f} to {summary.high:+.3f} {summary.unit}."
    )
    st.caption(
        "The interval resamples athletes using the saved held-out errors. It excludes "
        "uncertainty from retraining the entire modeling pipeline."
    )


def _cohort_matches(frame: pd.DataFrame, reports: Phase2Reports) -> bool:
    columns = ["session_pitch", "user"]
    if not set(columns).issubset(frame):
        return False
    first = frame[columns].astype(str).sort_values(columns).reset_index(drop=True)
    second = reports.analysis[columns].astype(str).sort_values(columns).reset_index(drop=True)
    return first.equals(second)


def render_start(
    frame: pd.DataFrame,
    project_root: Path,
    report_dir: Path,
    navigate: Callable[[str], None],
) -> None:
    """A concise opening story, one measured preview, and the actual primary finding."""
    introduction, motion = st.columns([1.15, 1], gap="large")
    with introduction:
        st.subheader("What do movement measurements add?")
        st.write(
            "Explore recorded pitches, then test whether rotational measurements add "
            "information beyond a pitcher's age and body size."
        )
        st.button(
            "Explore the pitches",
            type="primary",
            on_click=navigate,
            args=("Explore pitches",),
            key="story_open_explore",
            width="stretch",
        )
        st.markdown(f"**{len(frame):,} recorded pitches · {frame.user.nunique():,} athletes**")
        st.button(
            "Open the 3D motion lab",
            on_click=navigate,
            args=("Watch motion",),
            key="story_open_motion",
            width="stretch",
        )
        st.caption("Owen Garrett · Mechanical engineering & biomechanics research")
        st.caption(
            "Fastballs from the OpenBiomechanics Project. Repeated pitches belong to the same athletes."
        )
    with motion:
        _render_preview(frame, project_root)
    st.divider()
    st.subheader("The headline finding")
    reports = _verified_reports(report_dir)
    if reports is None:
        return
    if not _cohort_matches(frame, reports):
        st.warning(
            "The opening study summary requires the complete verified cohort. Findings are hidden."
        )
        return
    target = st.radio(
        "Choose an outcome",
        list(OUTCOMES),
        format_func=lambda name: OUTCOMES[name][0],
        horizontal=True,
        key="story_target",
    )
    try:
        summary = primary_story_summary(reports, target)
    except (ValueError, KeyError, TypeError) as error:
        st.warning(f"The saved finding cannot be summarized consistently: {error}.")
        return
    _summary_cards(summary)
    study, report, new_data = st.columns(3)
    study.button(
        "See the study results",
        on_click=navigate,
        args=("Study results",),
        key="story_open_study",
        width="stretch",
    )
    report.button(
        "Build an athlete report",
        on_click=navigate,
        args=("Athlete reports",),
        key="story_open_report",
        width="stretch",
    )
    new_data.button(
        "Plan a new-data study",
        on_click=navigate,
        args=("New-data lab",),
        key="story_open_new_data",
        width="stretch",
    )


def _score_chart(reports: Phase2Reports, summary: StorySummary, include_all: bool) -> None:
    models = list(MODEL_NAMES) if include_all else ["ridge_anthropometric", "ridge_combined"]
    scores = reports.metrics.loc[
        reports.metrics.target.eq(summary.target) & reports.metrics.model.isin(models),
        ["model", "athlete_mae"],
    ].copy()
    scores["Predictors"] = scores.model.map(MODEL_NAMES)
    chart = (
        alt.Chart(scores)
        .mark_bar(cornerRadiusEnd=4, height=30)
        .encode(
            x=alt.X(
                "athlete_mae:Q",
                title=f"Error ({summary.unit})",
                scale=alt.Scale(zero=True),
            ),
            y=alt.Y(
                "Predictors:N",
                title=None,
                sort=[MODEL_NAMES[name] for name in models],
                axis=alt.Axis(labelLimit=220),
            ),
            color=alt.Color(
                "model:N",
                scale=alt.Scale(
                    domain=list(MODEL_NAMES),
                    range=["#64748B", "#304E70", "#A66321", "#007C83"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Predictors:N", title="Model inputs"),
                alt.Tooltip("athlete_mae:Q", title=f"Average error ({summary.unit})", format=".3f"),
            ],
        )
        .properties(height=190 if include_all else 125)
    )
    st.altair_chart(chart, width="stretch")


def render_study_story(report_dir: Path) -> None:
    """Readable study results with the advanced audit available through root navigation."""
    st.subheader("Did the extra movement measures improve prediction?")
    st.write(
        "The comparison starts with age, mass, and height, then adds three rotational "
        "measurements. Each prediction is evaluated on an athlete held out from its model's training."
    )
    reports = _verified_reports(report_dir)
    if reports is None:
        return
    target = st.radio(
        "Study outcome",
        list(OUTCOMES),
        format_func=lambda name: OUTCOMES[name][0],
        horizontal=True,
        key="study_story_target",
    )
    try:
        summary = primary_story_summary(reports, target)
    except (ValueError, KeyError, TypeError) as error:
        st.warning(f"The saved finding cannot be summarized consistently: {error}.")
        return
    st.caption(
        f"Full study: {summary.pitches:,} eligible pitches from {summary.athletes:,} athletes. "
        "These comparisons remain fixed when pitch-explorer filters change."
    )
    _summary_cards(summary)
    include_all = st.toggle("Include all four models", key="study_story_all_models")
    st.caption(
        "Average prediction error per athlete; lower values are closer to observed measurements."
    )
    _score_chart(reports, summary, include_all)
    if target == "elbow_varus_moment":
        st.caption(
            "Elbow loading here means peak internal net elbow varus moment. Its units are "
            "newton-meters; it does not isolate ligament force or indicate injury probability."
        )
    with st.expander("How to read the comparison"):
        st.write(ERROR_HELP)
        folds = reports.spec.get("n_splits")
        partition_label = f"{folds} evaluation folds" if folds is not None else "evaluation folds"
        st.write(
            f"Athletes are kept together in {partition_label}. The same folds are used "
            "for each model and both outcomes. All preprocessing is learned within training folds."
        )
        st.write(
            f"The conditional interval uses {summary.resamples:,} paired resamples of athletes. "
            "Their existing predictions stay fixed. It does not include full training, model-selection, "
            "measurement, or external-cohort uncertainty; overlapping training folds limit a sampling interpretation."
        )
        st.write(
            "This follow-on analysis was planned after the Phase 1 results were available. "
            "It is exploratory, without p-values or multiplicity-adjusted confirmation. "
            "The source cohort is primarily collegiate and does not establish performance in MLB."
        )
    report = reports.verified_bytes.get("phase2_report.md")
    if report is not None:
        st.link_button(
            "Read the full research report",
            "https://github.com/owengarrett20-svg/"
            "pitching-performance-elbow-loading-github-ready/blob/main/docs/PHASE2_RESULTS.md",
        )
        st.download_button(
            "Download report text",
            data=report,
            file_name="pitching-research-report.md",
            mime="text/markdown",
            key="study_story_report",
        )
