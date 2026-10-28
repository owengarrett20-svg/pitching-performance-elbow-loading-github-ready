"""Interactive views of recorded pitches, with observed values kept intact.

This module only summarizes supplied observations. It does not fit a model,
download source files, infer video measurements, or simulate a mechanics change.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

MEASURES = {
    "pitch_speed_mph": (
        "Pitch speed",
        "mph",
        "Recorded pitch speed in the source dataset.",
    ),
    "elbow_varus_moment": (
        "Elbow varus moment",
        "N·m",
        "Peak internal net joint moment. This is a joint-loading summary; it does not measure injury risk or isolate UCL force.",
    ),
    "max_shoulder_internal_rotational_velo": (
        "Shoulder rotation speed",
        "deg/s",
        "Peak shoulder internal rotation angular velocity, using the source's released convention.",
    ),
    "max_rotation_hip_shoulder_separation": (
        "Hip–shoulder separation",
        "deg",
        "Peak thorax–pelvis separation angle over the delivery. This differs from separation at foot plant.",
    ),
    "max_torso_rotational_velo": (
        "Torso rotation speed",
        "deg/s",
        "Peak torso axial rotation angular velocity. The five measurement peaks need not occur at the same instant.",
    ),
}
SOURCE_COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
SOURCE_REPOSITORY = "https://github.com/drivelineresearch/openbiomechanics"
DATA_TERMS = f"{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/LICENSE-DATA.md"


def measure_label(name: str) -> str:
    label, unit, _ = MEASURES[name]
    return f"{label} ({unit})"


def _table(frame: pd.DataFrame, required: Iterable[str]) -> pd.DataFrame:
    missing = {"session_pitch", "user", *required} - set(frame)
    if missing:
        raise ValueError(f"Recorded pitch table is missing: {', '.join(sorted(missing))}")
    result = frame.copy()
    for name in ("session_pitch", "user"):
        if result[name].isna().any() or result[name].astype(str).str.strip().eq("").any():
            raise ValueError("Recorded pitches need nonempty pitch and athlete identifiers")
        result[name] = result[name].astype(str)
    if result.session_pitch.duplicated().any():
        raise ValueError("Each recorded pitch identifier must appear once")
    for name in required:
        try:
            result[name] = pd.to_numeric(result[name], errors="raise").astype(float)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Recorded {name} must contain numeric or missing observations"
            ) from error
        result[name] = result[name].replace([np.inf, -np.inf], np.nan)
    return result


def prepare_scatter_data(
    frame: pd.DataFrame, x: str, y: str, *, athlete_means: bool = False
) -> pd.DataFrame:
    """Use complete selected-axis pairs; never create missing measurements.

    Athlete means use the same paired pitches for both selected axes. They omit
    pitch IDs so that selecting an athlete average cannot masquerade as selecting
    a recorded delivery.
    """
    if x not in MEASURES or y not in MEASURES:
        raise ValueError("Choose one of the five declared biomechanical measurements")
    displayed = list(dict.fromkeys([x, y, "pitch_speed_mph", "elbow_varus_moment"]))
    available = [name for name in displayed if name in frame]
    table = _table(frame, [x, y])
    for name in available:
        table[name] = pd.to_numeric(table[name], errors="raise").replace([np.inf, -np.inf], np.nan)
    table = table.loc[table[x].notna() & table[y].notna()]
    columns = list(dict.fromkeys(["session_pitch", "user", *available]))
    if not athlete_means:
        return table[columns].reset_index(drop=True)
    means = table.groupby("user", sort=True)[available].mean()
    means["n_pitches"] = table.groupby("user", sort=True).size()
    return means.reset_index()


def selected_pitch_from_event(event: Any, valid_ids: Iterable[str]) -> str | None:
    """Accept only a single selection explicitly naming an available pitch."""
    if not isinstance(event, Mapping):
        return None
    selection = event.get("selection", {})
    if not isinstance(selection, Mapping):
        return None
    chosen = selection.get("pitch_pick", [])
    if isinstance(chosen, Mapping):
        value = chosen.get("session_pitch")
        if isinstance(value, list):
            value = value[0] if len(value) == 1 else None
    elif isinstance(chosen, list) and len(chosen) == 1 and isinstance(chosen[0], Mapping):
        value = chosen[0].get("session_pitch")
    else:
        return None
    if not isinstance(value, str):
        return None
    return value if value in set(valid_ids) else None


def build_scatter_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    *,
    athlete_means: bool = False,
    selected_pitch_id: str | None = None,
):
    """Build a hoverable, zoomable plot with pitch selection only for pitch rows."""
    if x not in MEASURES or y not in MEASURES:
        raise ValueError("Unknown recorded measurement")
    tooltips = [alt.Tooltip("user:N", title="Athlete ID")]
    if athlete_means:
        tooltips.append(alt.Tooltip("n_pitches:Q", title="Paired pitches", format=".0f"))
    else:
        tooltips.insert(0, alt.Tooltip("session_pitch:N", title="Pitch ID"))
    for name in dict.fromkeys([x, y, "pitch_speed_mph", "elbow_varus_moment"]):
        if name in data:
            prefix = "Mean " if athlete_means else ""
            tooltips.append(
                alt.Tooltip(f"{name}:Q", title=prefix + measure_label(name), format=".2f")
            )
    chart = (
        alt.Chart(data)
        .mark_circle(size=80, color="#007C91", opacity=0.75, stroke="white", strokeWidth=0.5)
        .encode(
            x=alt.X(f"{x}:Q", title=measure_label(x), scale=alt.Scale(zero=False)),
            y=alt.Y(f"{y}:Q", title=measure_label(y), scale=alt.Scale(zero=False)),
            tooltip=tooltips,
        )
        .properties(height=390)
        .configure_axis(labelFontSize=12, titleFontSize=13, titlePadding=12, gridOpacity=0.18)
        .configure_view(stroke=None)
    )
    if not athlete_means:
        initial = {}
        if selected_pitch_id in set(data.session_pitch):
            initial["value"] = [{"session_pitch": selected_pitch_id}]
        pick = alt.selection_point(
            name="pitch_pick", fields=["session_pitch"], toggle=False, empty=False, **initial
        )
        chart = chart.add_params(pick).encode(
            color=alt.condition(pick, alt.value("#C96C2D"), alt.value("#007C91")),
            size=alt.condition(pick, alt.value(160), alt.value(80)),
            stroke=alt.condition(pick, alt.value("#172B3A"), alt.value("white")),
        )
    return chart.interactive(name="explorer_zoom")


def compare_recorded_pitches(frame: pd.DataFrame, pitch_a: str, pitch_b: str) -> pd.DataFrame:
    """Calculate B-minus-A differences using two observed rows and no imputation."""
    table = _table(frame, MEASURES).set_index("session_pitch")
    if pitch_a not in table.index or pitch_b not in table.index:
        raise ValueError("Both comparison pitches must exist in the selected observations")
    first, second = table.loc[pitch_a], table.loc[pitch_b]
    return pd.DataFrame(
        [
            {
                "measure": MEASURES[name][0],
                "unit": MEASURES[name][1],
                "pitch_a": first[name],
                "pitch_b": second[name],
                "difference_b_minus_a": second[name] - first[name],
            }
            for name in MEASURES
        ]
    )


def recorded_pitch_export(frame: pd.DataFrame) -> bytes:
    """Export recorded values with pitch/athlete identity and source/license links."""
    table = _table(frame, MEASURES)
    exported = table[["session_pitch", "user", *MEASURES]].copy()
    exported["source_repository"] = SOURCE_REPOSITORY
    exported["source_commit"] = SOURCE_COMMIT
    exported["data_terms"] = DATA_TERMS
    return exported.to_csv(index=False).encode("utf-8")


def _value(value: Any) -> str:
    return (
        f"{float(value):,.1f}" if pd.notna(value) and np.isfinite(float(value)) else "Not observed"
    )


def _ensure_option(key: str, options: list[str], preferred: str | None = None) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = preferred if preferred in options else options[0]


def _reset_chart_selection() -> None:
    # A dropdown change creates a fresh chart selection seeded to that pitch.
    # Otherwise clicking an already-highlighted old point may emit no change.
    st.session_state["_explorer_chart_generation"] = (
        st.session_state.get("_explorer_chart_generation", 0) + 1
    )
    st.session_state["_explorer_chart_pick"] = None


def _pitch_label(table: pd.DataFrame, pitch_id: str) -> str:
    row = table.loc[table.session_pitch.eq(pitch_id)].iloc[0]
    return f"Pitch {pitch_id} · athlete {row.user} · {_value(row.pitch_speed_mph)} mph"


def _render_pitch_card(table: pd.DataFrame, pitch_id: str, full_frame: pd.DataFrame) -> None:
    row = table.loc[table.session_pitch.eq(pitch_id)].iloc[0]
    with st.container(border=True):
        st.subheader(f"Pitch {pitch_id}")
        st.caption(f"Pseudonymous athlete {row.user}. Values describe this recorded delivery.")
        for names in (list(MEASURES)[:2], list(MEASURES)[2:]):
            columns = st.columns(len(names))
            for column, name in zip(columns, names):
                label, unit, description = MEASURES[name]
                column.metric(f"{label} ({unit})", _value(row[name]), help=description)
        for name in ("pitch_speed_mph", "elbow_varus_moment"):
            values = pd.to_numeric(full_frame[name], errors="raise").replace(
                [np.inf, -np.inf], np.nan
            )
            if values.notna().any():
                st.caption(
                    f"Full-study median {MEASURES[name][0].lower()}: {_value(values.median())} "
                    f"{MEASURES[name][1]}. This is a descriptive reference for the observed cohort."
                )
        st.caption(
            "The peaks can occur at different instants. A pitch's joint moment alone does not identify injury risk."
        )


def render_pitch_explorer(
    frame: pd.DataFrame,
    *,
    full_frame: pd.DataFrame | None = None,
    selected_pitch_id: str | None = None,
) -> str | None:
    """Explore measured deliveries; return the selected pitch for navigation/sharing."""
    st.subheader("Explore recorded pitches")
    st.write(
        "Choose two measurements, inspect a recorded pitch, and compare observations. "
        "The controls change the view of recorded data."
    )
    if frame.empty:
        st.info("No recorded pitches match these filters. Clear a sidebar selection to continue.")
        return None
    table = _table(frame, MEASURES)
    cohort = table if full_frame is None else _table(full_frame, MEASURES)
    counts = st.columns(2)
    counts[0].metric("Pitches in this view", str(len(table)))
    counts[1].metric("Athletes in this view", str(table.user.nunique()))
    st.caption(
        "Several pitches may belong to one athlete. These observations do not establish the effects of changing mechanics."
    )
    left, right = st.columns(2)
    x = left.selectbox(
        "Horizontal measurement", list(MEASURES), format_func=measure_label, key="explorer_x"
    )
    y = right.selectbox(
        "Vertical measurement",
        list(MEASURES),
        index=1,
        format_func=measure_label,
        key="explorer_y",
    )
    unit = st.radio(
        "Each chart point represents",
        ["One pitch", "One athlete's average"],
        key="explorer_unit",
        horizontal=True,
    )
    athlete_means = unit == "One athlete's average"
    plotted = prepare_scatter_data(table, x, y, athlete_means=athlete_means)
    paired_count = len(prepare_scatter_data(table, x, y))
    st.caption(
        f"{paired_count} of {len(table)} pitches have both selected measurements; "
        f"{len(table) - paired_count} are omitted from this chart. Missing observations remain missing."
    )
    if athlete_means:
        st.caption(
            "Each point averages the paired pitches for one athlete. An average is not a single recorded pitch. "
            "Rotational values average the released per-pitch peak summaries. "
            "Use the pitch selector below to inspect an individual delivery."
        )
    else:
        st.caption(
            "Hover for measurements; click a point to open its pitch card. The selector below also works with a keyboard or touch screen. "
            "Scroll to zoom and drag to pan."
        )
    identifiers = table.session_pitch.tolist()
    previous_pitch = st.session_state.get("explorer_pitch")
    _ensure_option("explorer_pitch", identifiers, selected_pitch_id)
    if previous_pitch is not None and previous_pitch not in identifiers:
        _reset_chart_selection()
    # The root persists this function's previous return. That normal round-trip
    # must not override a freshly changed dropdown. A different incoming pitch
    # represents an external URL/navigation change.
    if (
        selected_pitch_id in identifiers
        and selected_pitch_id != st.session_state.get("_explorer_returned_pitch")
        and selected_pitch_id != st.session_state["explorer_pitch"]
    ):
        st.session_state["explorer_pitch"] = selected_pitch_id
        _reset_chart_selection()
    generation = st.session_state.get("_explorer_chart_generation", 0)
    event = None
    if plotted.empty:
        st.info("No pitches have both selected measurements. Choose another pair of measurements.")
    else:
        event = st.altair_chart(
            build_scatter_chart(
                plotted,
                x,
                y,
                athlete_means=athlete_means,
                selected_pitch_id=st.session_state["explorer_pitch"],
            ),
            key=(
                f"explorer_scatter_athletes_{generation}"
                if athlete_means
                else f"explorer_scatter_pitches_{generation}"
            ),
            on_select="ignore" if athlete_means else "rerun",
            selection_mode="pitch_pick" if not athlete_means else None,
            width="stretch",
        )
    selected_event = selected_pitch_from_event(event, identifiers)
    if selected_event != st.session_state.get("_explorer_chart_pick"):
        if selected_event is not None:
            st.session_state["explorer_pitch"] = selected_event
        st.session_state["_explorer_chart_pick"] = selected_event
    pitch_id = st.selectbox(
        "Inspect a recorded pitch",
        identifiers,
        format_func=lambda value: _pitch_label(table, value),
        key="explorer_pitch",
        on_change=_reset_chart_selection,
    )
    _render_pitch_card(table, pitch_id, cohort)
    st.subheader("Compare two observed pitches")
    st.caption(
        "Differences are B minus A for two recorded deliveries. These are descriptive comparisons, with no predicted mechanics changes or injury categories."
    )
    _ensure_option("explorer_compare_a", identifiers, pitch_id)
    alternate = next((name for name in identifiers if name != pitch_id), pitch_id)
    _ensure_option("explorer_compare_b", identifiers, alternate)
    left, right = st.columns(2)
    first = left.selectbox(
        "Pitch A",
        identifiers,
        format_func=lambda value: _pitch_label(table, value),
        key="explorer_compare_a",
    )
    second = right.selectbox(
        "Pitch B",
        identifiers,
        format_func=lambda value: _pitch_label(table, value),
        key="explorer_compare_b",
    )
    compared = compare_recorded_pitches(table, first, second)
    for name in ("pitch_a", "pitch_b", "difference_b_minus_a"):
        compared[name] = compared[name].map(_value)
    st.dataframe(
        compared.rename(
            columns={
                "measure": "Measurement",
                "unit": "Unit",
                "pitch_a": "Pitch A",
                "pitch_b": "Pitch B",
                "difference_b_minus_a": "B − A",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Peak hip–shoulder separation differs from separation at foot plant. Find & compare pitches opens measured-marker replays for any recorded study pitch; camera footage is not assumed."
    )
    with st.expander("Recorded values and source download"):
        displayed = ["session_pitch", "user", *MEASURES]
        st.dataframe(table[displayed], hide_index=True, width="stretch")
        st.download_button(
            "Download the selected recorded pitches",
            data=recorded_pitch_export(table),
            file_name="recorded_pitch_selection.csv",
            mime="text/csv",
            key="explorer_download",
        )
        st.caption(
            f"Source: Driveline Baseball Research & Development, OpenBiomechanics Project. "
            f"Data-derived exports retain CC BY-NC-SA 4.0 plus the professional-sports/financial-analysis affiliation restriction. [Full terms]({DATA_TERMS})."
        )
    st.session_state["_explorer_returned_pitch"] = pitch_id
    return pitch_id
