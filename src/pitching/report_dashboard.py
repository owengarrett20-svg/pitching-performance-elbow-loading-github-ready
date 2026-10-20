"""Streamlit report builder using saved, verified research artifacts only."""

from __future__ import annotations

from math import isfinite
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from pitching.athlete_reports import (
    prepare_athlete_report,
    render_report_html,
    report_csv,
    report_metadata_json,
)
from pitching.phase2_dashboard import load_phase2_reports


def render_report_builder(frame: pd.DataFrame, report_dir: Path, project_root: Path) -> None:
    """Display a focused summary and offer self-contained research-report downloads."""
    st.subheader("A research report for one recorded athlete")
    st.write(
        "Choose a pseudonymous athlete to inspect the recorded measurements and download "
        "a readable report. The HTML opens in your browser and can be printed to PDF."
    )
    if frame.empty:
        st.info("No recorded pitches are available for a report.")
        return
    if "user" not in frame or frame.user.isna().any():
        st.warning("The report table needs nonmissing athlete identifiers.")
        return
    athletes = sorted(frame.user.astype(str).unique())
    requested = st.session_state.pop("report_requested_athlete", None)
    if requested is not None:
        if str(requested) in athletes:
            st.session_state["report_athlete"] = str(requested)
        else:
            st.info(
                "The requested athlete is unavailable in this report table. Choose a recorded athlete below."
            )
    athlete = st.selectbox("Recorded athlete", athletes, key="report_athlete")
    reports = None
    try:
        reports = load_phase2_reports(report_dir)
    except (OSError, ValueError, TypeError, KeyError) as error:
        st.info(
            f"Verified Phase 2 predictions are unavailable ({error}). "
            "The report can still summarize observed measurements."
        )
    try:
        report = prepare_athlete_report(frame, athlete, reports)
    except (ValueError, TypeError, KeyError) as error:
        st.warning(f"This athlete report could not be prepared: {error}")
        return
    first, second = st.columns(2)
    first.metric("Recorded pitches in report", len(report.pitches))
    sessions = report.metadata["n_sessions"]
    second.metric("Recorded sessions", str(sessions) if sessions is not None else "Unknown")
    st.caption(
        "This view uses the complete table supplied to the report builder; pitch-explorer "
        "filters do not imply a full career record. The released OBP cohort contains only "
        "one assessment session per athlete."
    )
    stem = "recorded-athlete-report"
    st.download_button(
        "Download illustrated HTML report",
        data=render_report_html(report),
        file_name=f"{stem}.html",
        mime="text/html",
        type="primary",
        key="report_html_download",
        width="stretch",
    )
    observed, metadata = st.columns(2)
    observed.download_button(
        "Observed pitch CSV",
        data=report_csv(report),
        file_name=f"{stem}-observations.csv",
        mime="text/csv",
        key="report_observed_download",
        width="stretch",
    )
    metadata.download_button(
        "Attribution and provenance JSON",
        data=report_metadata_json(report),
        file_name=f"{stem}-metadata.json",
        mime="application/json",
        key="report_metadata_download",
        width="stretch",
    )
    st.caption(
        "Keep the observed CSV and metadata together when sharing. Reports retain OBP data "
        "terms, including its professional-sports affiliation restriction."
    )
    for notice in report.notices:
        if notice.startswith("Saved prediction errors"):
            st.warning(notice)
    st.markdown("#### Observed pitch summaries")
    summaries = list(report.summary.itertuples(index=False))
    for start, count in ((0, 3), (3, 2)):
        for column, row in zip(st.columns(count), summaries[start : start + count]):
            available = pd.notna(row.mean) and isfinite(float(row.mean))
            column.metric(
                row.measurement,
                f"{row.mean:,.2f} {row.unit}" if available else "Unavailable",
                help="Mean of the available recorded values for this measurement.",
            )
            if available:
                column.caption(
                    f"Observed range: {row.minimum:,.2f}–{row.maximum:,.2f} {row.unit}. "
                    f"{int(row.n_observed)} of {len(report.pitches)} pitches observed; "
                    f"{int(row.n_missing)} missing."
                )
            else:
                column.caption(
                    f"No observed values in {len(report.pitches)} recorded pitches; "
                    f"{int(row.n_missing)} missing."
                )
    displayed = report.summary[
        ["measurement", "unit", "n_observed", "n_missing", "mean", "minimum", "maximum"]
    ].rename(
        columns={
            "measurement": "Recorded measurement",
            "unit": "Unit",
            "n_observed": "Observed pitches",
            "n_missing": "Missing pitches",
            "mean": "Observed mean",
            "minimum": "Minimum",
            "maximum": "Maximum",
        }
    )
    st.caption(
        "Each mean averages the available recorded pitch summaries for that variable. "
        "These few observations do not estimate long-term consistency or a mechanics intervention."
    )
    with st.expander("Detailed measurement table"):
        st.dataframe(displayed, hide_index=True, width="stretch")
    from pitching.data import VARIABLES

    measurement = st.selectbox(
        "Inspect a recorded measurement",
        list(VARIABLES),
        format_func=lambda column: f"{VARIABLES[column][0]} ({VARIABLES[column][1]})",
        key="report_measurement",
    )
    chart_data = report.pitches[["session_pitch", measurement]].rename(
        columns={measurement: "value"}
    )
    label, unit = VARIABLES[measurement]
    st.altair_chart(
        alt.Chart(chart_data.dropna(subset=["value"]))
        .mark_circle(size=100, color="#007C91")
        .encode(
            x=alt.X("session_pitch:N", title="Recorded pitch ID", sort=None),
            y=alt.Y("value:Q", title=f"Observed ({unit})", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("session_pitch:N", title="Pitch"),
                alt.Tooltip("value:Q", title=label, format=".2f"),
            ],
        )
        .properties(height=220),
        width="stretch",
    )
    st.caption(
        "One dot per observed pitch; identifier order is not a time axis. Missing values are omitted."
    )
    if not report.predictions.empty:
        with st.expander("Saved athlete-held-out prediction errors"):
            st.caption(
                "Primary-partition combined ridge model. These are previously computed "
                "errors for this athlete, separate from the complete study's equal-athlete score."
            )
            st.dataframe(report.predictions, hide_index=True, width="stretch")
    with st.expander("How to use the report"):
        st.write(
            "Open the downloaded HTML in a browser. It contains its figures and styling, "
            "requires no internet connection, and runs no scripts. Use your browser's Print "
            "command and Save as PDF for a shareable document."
        )
        st.write(
            "Read the observations before interpreting the model errors. A large error identifies "
            "a difficult recorded case; it does not identify an injury, a flawed technique, or "
            "a causal change to make."
        )
        if (project_root / "docs/ATHLETE_REPORTS.md").is_file():
            st.caption("Report methods are documented in docs/ATHLETE_REPORTS.md.")
