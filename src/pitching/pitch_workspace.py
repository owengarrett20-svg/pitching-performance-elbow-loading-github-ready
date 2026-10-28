"""Search recorded pitches and inspect their exact source-linked marker replays.

Every selection identifies an observed source row. Replays show measured skin
markers, not camera footage. Their independent clocks are never event-aligned.
This view reads local verified assets; it does not fit, download, or infer motion.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from pitching.motion_lab import MEASUREMENT_NOTES, marker_regions, marker_viewer_html
from pitching.pitch_explorer import (
    DATA_TERMS,
    MEASURES,
    SOURCE_COMMIT,
    compare_recorded_pitches,
    measure_label,
    selected_pitch_from_event,
)
from pitching.video_lab import (
    MotionAssetError,
    load_marker_frames,
    load_motion_manifest,
    matching_examples,
    verified_asset,
)


@dataclass(frozen=True)
class WorkspaceSelection:
    """Actual observed row IDs returned to the route and its shareable URL."""

    primary: str
    comparison: str


def workspace_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy and validate source identity; keep absent/nonfinite measures missing."""
    required = {"session_pitch", "user", *MEASURES}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Pitch workspace is missing fields: {', '.join(sorted(missing))}")
    table = frame.copy().reset_index(drop=True)
    for name in ("session_pitch", "user"):
        if table[name].isna().any() or table[name].astype(str).str.strip().eq("").any():
            raise ValueError("Pitch workspace needs nonmissing source pitch and athlete IDs")
        table[name] = table[name].astype(str)
    if table.session_pitch.duplicated().any():
        raise ValueError("Each source pitch ID must identify exactly one workspace row")
    for name in MEASURES:
        try:
            table[name] = pd.to_numeric(table[name], errors="raise").astype(float)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Source measurement {name} must be numeric or missing") from error
        table[name] = table[name].replace([np.inf, -np.inf], np.nan)
    return table


def load_workspace_catalog(
    project_root: Path, frame: pd.DataFrame
) -> tuple[Path, dict[str, dict[str, Any]]]:
    """Prefer the expanded catalog; a present invalid catalog never silently falls back."""
    catalog_path = project_root / "assets/pitch_catalog/manifest.json"
    if catalog_path.exists() or catalog_path.is_symlink():
        from pitching.pitch_catalog import catalog_examples, load_pitch_catalog

        directory, manifest = load_pitch_catalog(project_root)
        entries = catalog_examples(frame, manifest)
    else:
        directory, manifest = load_motion_manifest(project_root)
        entries = matching_examples(frame, manifest["examples"])
    source = frame.copy()
    if entries:
        source["session_pitch"] = source.session_pitch.astype(str)
        if source.session_pitch.duplicated().any():
            raise MotionAssetError("Replay source identity is not unique in the observed table")
        source = source.set_index("session_pitch")
    for entry in entries:
        row = source.loc[entry["session_pitch"]]
        for name in MEASURES:
            try:
                value, released = float(row[name]), float(entry["poi"][name])
            except (ValueError, TypeError, KeyError) as error:
                raise MotionAssetError("Replay source measurements cannot be matched") from error
            if not np.isfinite(value) or not np.isclose(value, released, rtol=0, atol=1e-9):
                raise MotionAssetError(
                    f"Source pitch {entry['session_pitch']} measurements differ from the replay catalog"
                )
    return directory, {entry["session_pitch"]: entry for entry in entries}


def search_pitch_rows(
    frame: pd.DataFrame,
    query: str,
    replay_ids: Sequence[str] = (),
    *,
    replays_only: bool = False,
) -> pd.DataFrame:
    """Literal, case-insensitive all-token search; row positions follow this exact output."""
    table = workspace_table(frame)
    prepared = set(replay_ids)
    table["replay_available"] = table.session_pitch.isin(prepared)
    if replays_only:
        table = table.loc[table.replay_available]
    columns = [
        name
        for name in ("session_pitch", "user", "session", "playing_level", "pitch_type")
        if name in table
    ]
    names = {
        "session_pitch": "pitch",
        "user": "athlete",
        "session": "session",
        "playing_level": "playing level",
        "pitch_type": "pitch type",
    }
    text = pd.Series("", index=table.index)
    for name in columns:
        text += " " + names[name] + " " + table[name].fillna("").astype(str)
    text = text.str.casefold()
    for name in MEASURES:
        # Search both exact released scalars and the rounded numbers displayed in
        # the table. Missing observations contribute no invented zero/string.
        text += " " + table[name].map(
            lambda value: f"{value:g} {value:.1f} {value:.2f}" if pd.notna(value) else ""
        )
    keep = pd.Series(True, index=table.index)
    tokens = str(query).casefold().split()
    identity_fields = {"pitch": "session_pitch", "athlete": "user", "session": "session"}
    if tokens and ":" in tokens[0]:
        prefix, value = tokens[0].split(":", 1)
        if prefix in identity_fields and value:
            tokens = [prefix, value, *tokens[1:]]
    if len(tokens) >= 2 and tokens[0] in identity_fields:
        column = identity_fields[tokens[0]]
        keep &= (
            table[column].fillna("").astype(str).str.casefold().eq(tokens[1])
            if column in table
            else False
        )
        tokens = tokens[2:]
    for token in tokens:
        keep &= text.str.contains(token, regex=False, na=False)
    return (
        table.loc[keep]
        .sort_values(["replay_available", "session_pitch"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )


def pitch_from_table_event(event: Any, displayed_ids: Sequence[str]) -> str | None:
    """Map original-input row positions, including after client-side sorting, to exact IDs."""
    if not isinstance(event, Mapping):
        return None
    selection = event.get("selection")
    if not isinstance(selection, Mapping):
        return None
    rows = selection.get("rows")
    if not isinstance(rows, list) or len(rows) != 1 or type(rows[0]) is not int:
        return None
    index = rows[0]
    return displayed_ids[index] if 0 <= index < len(displayed_ids) else None


def cohort_percentiles(cohort: pd.DataFrame, identifier: str) -> dict[str, float | None]:
    """Mid-rank percentile of one observed pitch among observed cohort values.

    Ties count half. A missing value has no percentile; missing cohort values are
    excluded rather than treated as zero. This is a descriptive position in this
    sample, not a performance grade or risk category.
    """
    table = workspace_table(cohort)
    match = table.loc[table.session_pitch.eq(identifier)]
    if match.empty:
        raise ValueError(f"Source pitch {identifier} is not in the reference cohort")
    row = match.iloc[0]
    result: dict[str, float | None] = {}
    for name in MEASURES:
        values = table[name].dropna()
        value = row[name]
        if pd.isna(value) or values.empty:
            result[name] = None
            continue
        below = float((values < value).sum())
        tied = float((values == value).sum())
        result[name] = 100.0 * (below + 0.5 * tied) / len(values)
    return result


def next_athlete_pitch(table: pd.DataFrame, primary: str, current: str | None) -> str | None:
    """Cycle through the same athlete's other recorded pitches, never returning Pitch A."""
    rows = workspace_table(table)
    athlete = rows.loc[rows.session_pitch.eq(primary), "user"]
    if athlete.empty:
        return None
    siblings = sorted(
        identifier
        for identifier in rows.loc[rows.user.eq(athlete.iloc[0]), "session_pitch"]
        if identifier != primary
    )
    if not siblings:
        return None
    if current in siblings:
        return siblings[(siblings.index(current) + 1) % len(siblings)]
    return siblings[0]


def selection_roles(identifiers: Sequence[str], selection: WorkspaceSelection) -> list[str]:
    """Label each displayed source row as A, B, both, or unselected."""
    roles = []
    for identifier in identifiers:
        role = [
            side
            for side, chosen in (("A", selection.primary), ("B", selection.comparison))
            if identifier == chosen
        ]
        roles.append(" & ".join(role))
    return roles


ROLE_COLORS = {"A": "#C96C2D", "B": "#6B4FA0", "A & B": "#8A3B12", "": "#007C91"}


def workspace_chart(
    visible: pd.DataFrame, x: str, y: str, selection: WorkspaceSelection
) -> alt.Chart | None:
    """Clickable scatter of the searched rows; A and B are drawn on top and labeled."""
    if x not in MEASURES or y not in MEASURES:
        raise ValueError("Choose one of the five declared biomechanical measurements")
    table = workspace_table(visible)
    plotted = table.loc[table[x].notna() & table[y].notna()].copy()
    if plotted.empty:
        return None
    plotted["role"] = selection_roles(plotted.session_pitch.tolist(), selection)
    plotted["layer"] = plotted.role.map(lambda role: 1 if role else 0)
    fields = list(dict.fromkeys([x, y, *MEASURES]))
    tooltips = [
        alt.Tooltip("session_pitch:N", title="Pitch ID"),
        alt.Tooltip("user:N", title="Athlete ID"),
    ]
    if "playing_level" in plotted:
        tooltips.append(alt.Tooltip("playing_level:N", title="Playing level"))
    tooltips += [
        alt.Tooltip(f"{name}:Q", title=measure_label(name), format=".1f") for name in fields
    ]
    tooltips.append(alt.Tooltip("role:N", title="Selected as"))
    columns = ["session_pitch", "user", "role", "layer", *fields]
    if "playing_level" in plotted:
        columns.append("playing_level")
    pick = alt.selection_point(
        name="pitch_pick", fields=["session_pitch"], toggle=False, empty=False
    )
    domain = list(ROLE_COLORS)
    base = alt.Chart(plotted[columns]).encode(
        x=alt.X(f"{x}:Q", title=measure_label(x), scale=alt.Scale(zero=False)),
        y=alt.Y(f"{y}:Q", title=measure_label(y), scale=alt.Scale(zero=False)),
    )
    points = (
        base.mark_circle(stroke="white", strokeWidth=0.6)
        .encode(
            color=alt.Color(
                "role:N",
                scale=alt.Scale(domain=domain, range=[ROLE_COLORS[name] for name in domain]),
                legend=None,
            ),
            size=alt.condition("datum.layer > 0", alt.value(230), alt.value(70)),
            opacity=alt.condition("datum.layer > 0", alt.value(1.0), alt.value(0.55)),
            order=alt.Order("layer:Q"),
            tooltip=tooltips,
        )
        .add_params(pick)
    )
    labels = (
        base.transform_filter("datum.layer > 0")
        .mark_text(align="left", dx=10, dy=-10, fontSize=13, fontWeight="bold")
        .encode(
            text="role:N",
            color=alt.Color(
                "role:N",
                scale=alt.Scale(domain=domain, range=[ROLE_COLORS[name] for name in domain]),
                legend=None,
            ),
        )
    )
    return (
        alt.layer(points.interactive(name="workspace_zoom"), labels)
        .properties(height=380)
        .configure_axis(labelFontSize=12, titleFontSize=13, titlePadding=12, gridOpacity=0.18)
        .configure_view(stroke=None)
    )


def _reset_table_selection() -> None:
    st.session_state["_workspace_table_generation"] = (
        st.session_state.get("_workspace_table_generation", 0) + 1
    )
    st.session_state["_workspace_last_table_pick"] = None


def _reset_chart_selection() -> None:
    st.session_state["_workspace_chart_generation"] = (
        st.session_state.get("_workspace_chart_generation", 0) + 1
    )
    st.session_state["_workspace_last_chart_pick"] = None


def _apply_pick(identifier: str, target: str) -> None:
    key = "workspace_compare_pitch" if target == "Pitch B" else "workspace_primary_pitch"
    st.session_state[key] = identifier


def _swap_pitches() -> None:
    primary = st.session_state.get("workspace_primary_pitch")
    comparison = st.session_state.get("workspace_compare_pitch")
    if primary is None or comparison is None:
        return
    # Pitch A must be a searched row. Reveal the full table rather than letting
    # the visible-row fallback silently substitute a different recording.
    if comparison not in st.session_state.get("_workspace_visible_ids", []):
        st.session_state["workspace_search"] = ""
        st.session_state["workspace_replays_only"] = False
    st.session_state["workspace_primary_pitch"] = comparison
    st.session_state["workspace_compare_pitch"] = primary
    _reset_table_selection()
    _reset_chart_selection()


def _compare_with(identifier: str | None) -> None:
    if identifier is not None:
        st.session_state["workspace_compare_pitch"] = identifier


def _label(table: pd.DataFrame, identifier: str) -> str:
    row = table.loc[table.session_pitch.eq(identifier)].iloc[0]
    speed = f"{row.pitch_speed_mph:.1f} mph" if pd.notna(row.pitch_speed_mph) else "speed missing"
    return f"{identifier} · athlete {row.user} · {speed}"


def _verified_replay(directory: Path, entry: dict) -> dict[str, np.ndarray]:
    if "frames_bytes" in entry:
        from pitching.pitch_catalog import load_catalog_frames

        arrays = load_catalog_frames(directory, entry)
    else:
        path = verified_asset(directory, entry["frames_file"], entry["frames_sha256"], ".npz")
        arrays = load_marker_frames(path, entry["n_frames"])
    if not np.isfinite(arrays["positions_m"]).all(axis=2).any():
        raise MotionAssetError("No complete measured marker is available in this recording")
    declared = entry.get("marker_labels")
    if declared is not None and list(arrays["labels"]) != declared:
        raise MotionAssetError("Marker labels do not match the selected source recording")
    return arrays


def comparison_replay_html(
    first: tuple[dict[str, np.ndarray], dict] | None,
    second: tuple[dict[str, np.ndarray], dict] | None,
    selection: WorkspaceSelection,
    unavailable: dict[str, str] | None = None,
) -> str:
    """Author two offline source-bound replays with independent clocks and accessible controls."""
    notices = unavailable or {}
    panes = []
    for side, recording, identifier in (
        ("A", first, selection.primary),
        ("B", second, selection.comparison),
    ):
        heading = f"Pitch {side} · {html.escape(identifier)}"
        if recording is None:
            reason = html.escape(notices.get(side, "No prepared marker replay for this pitch."))
            content = f'<div class="empty">{reason}<p>The observed measurements remain available below.</p></div>'
        else:
            arrays, entry = recording
            document = marker_viewer_html(arrays, entry)
            content = (
                f'<iframe id="replay-{side}" title="Measured marker replay for pitch {side}" '
                f'srcdoc="{html.escape(document, quote=True)}"></iframe>'
            )
        panes.append(f"<section><h2>{heading}</h2>{content}</section>")
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;color:#172b3a}
.tools{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}button{font:inherit;padding:9px 13px;border:1px solid #b6cbd4;border-radius:7px;background:#f3f8fa;color:#172b3a;cursor:pointer}
.note{font-size:13px;line-height:1.5;color:#4f6473;margin:9px 0 16px}.panes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
section{min-width:0}h2{font-size:16px;margin:0 0 8px}iframe{display:block;width:100%;height:840px;border:0}
.empty{border:1px dashed #aec4ce;border-radius:9px;padding:22px;min-height:220px;line-height:1.6}
@media(max-width:760px){.panes{grid-template-columns:1fr}}
</style></head><body><div class="tools"><button id="start-both">Start available replays from their own starts</button><button id="pause-both">Pause both</button></div>
<p class="note">Measured skin markers, not camera footage. Each replay keeps its own clock, so starting both together does not align foot plant or ball release.</p>
<div class="panes">__PANES__</div><script>
const frames=()=>Array.from(document.querySelectorAll('iframe'));
function resizeFrame(frame){try{const body=frame.contentDocument.body;if(body)frame.style.height=Math.ceil(body.getBoundingClientRect().height+4)+'px'}catch(error){}}
for(const frame of frames()){frame.addEventListener('load',()=>{resizeFrame(frame);new ResizeObserver(()=>resizeFrame(frame)).observe(frame.contentDocument.body)})}
document.getElementById('start-both').onclick=()=>{for(const frame of frames()){try{const d=frame.contentDocument,s=d.getElementById('frame'),p=d.getElementById('play');if(s&&p){s.value=0;s.dispatchEvent(new Event('input',{bubbles:true}));p.click()}}catch(error){}}};
document.getElementById('pause-both').onclick=()=>{for(const frame of frames()){try{const p=frame.contentDocument.getElementById('play');if(p&&p.textContent==='Pause')p.click()}catch(error){}}};
</script></body></html>""".replace("__PANES__", "".join(panes))


def selected_observations_json(table: pd.DataFrame, selection: WorkspaceSelection) -> str:
    """Export only the selected observed rows, retaining missing values as JSON null."""
    rows = []
    source_records = []
    for role, identifier in (("A", selection.primary), ("B", selection.comparison)):
        source = table.loc[table.session_pitch.eq(identifier)].iloc[0]
        row = {"role": role, "session_pitch": identifier, "user": str(source.user)}
        for name in MEASURES:
            row[name] = float(source[name]) if pd.notna(source[name]) else None
        rows.append(row)
        record = {}
        for name, value in source.items():
            if pd.isna(value):
                record[name] = None
            else:
                scalar = value.item() if isinstance(value, np.generic) else value
                record[name] = (
                    None if isinstance(scalar, float) and not np.isfinite(scalar) else scalar
                )
        source_records.append({"role": role, "released_fields": record})
    return json.dumps(
        {
            "source_commit": SOURCE_COMMIT,
            "data_terms": DATA_TERMS,
            "interpretation": "Two recorded observations; B-minus-A is descriptive, not a mechanics intervention.",
            "units": {name: value[1] for name, value in MEASURES.items()},
            "observations": rows,
            "source_records": source_records,
        },
        indent=2,
        allow_nan=False,
    )


def _render_markers(recording: tuple[dict[str, np.ndarray], dict], side: str) -> None:
    arrays, entry = recording
    st.markdown(f"**Pitch {side}: {entry['session_pitch']} · athlete {entry['user']}**")
    groups = marker_regions(arrays["labels"])
    grouped = {
        index: name
        for name, indices in groups.items()
        if name != "All markers"
        for index in indices
    }
    positions = arrays["positions_m"]
    observed = np.isfinite(positions).all(axis=2).sum(axis=0)
    markers = pd.DataFrame(
        {
            "Display marker label": arrays["labels"],
            "Original source label": entry.get("source_marker_labels", arrays["labels"]),
            "Display group": [grouped.get(index, "Other") for index in range(len(observed))],
            "Observed display samples": observed,
            "Missing display samples": len(positions) - observed,
        }
    )
    st.dataframe(markers, hide_index=True, width="stretch", height=245)
    st.caption(
        f"{len(arrays['labels'])} recorded skin markers · {entry['point_rate_hz']:g} Hz source · "
        f"{entry['n_frames']} prepared display samples. Use Inspect in this replay to view X/Y/Z coordinates. "
        "Display groups and links are visual guides, not validated joint centers."
    )
    if entry.get("marker_label_aliases"):
        st.caption(
            "This source uses explicit Skeleton_001_ label prefixes. The display aliases "
            "remove that namespace for known marker names; original labels remain in this table. "
            "Coordinates are unchanged, and the labels do not establish a validated skeleton model."
        )


def render_pitch_workspace(
    frame: pd.DataFrame,
    project_root: Path,
    selected_pitch_id: str | None = None,
    comparison_pitch_id: str | None = None,
    full_frame: pd.DataFrame | None = None,
) -> WorkspaceSelection | None:
    """Search a source table, select an observed pitch, and inspect both exact recordings."""
    st.subheader("Find a pitch. Inspect its motion and measurements.")
    st.write(
        "Search by pitch, athlete, session, playing level, or a displayed measurement. "
        "Click a table row or chart point to open Pitch A or Pitch B, then compare their "
        "marker replays, marker sets, and recorded measurements side by side."
    )
    table = workspace_table(frame)
    if table.empty:
        st.info("No recorded pitches match the current filters.")
        return None
    try:
        directory, catalog = load_workspace_catalog(project_root, table)
    except (OSError, ValueError, TypeError, KeyError) as error:
        directory, catalog = project_root / "assets/motion", {}
        st.warning(
            f"Prepared replay catalog is unavailable: {error}. Measurements remain available."
        )
    all_ids = table.session_pitch.tolist()
    incoming = selected_pitch_id in all_ids and (
        selected_pitch_id != st.session_state.get("_workspace_returned_primary")
        or "workspace_primary_pitch" not in st.session_state
    )
    if incoming:
        st.session_state["workspace_primary_pitch"] = selected_pitch_id
        # A deliberately opened source-ID link must not remain hidden behind a
        # previous search. Ordinary parent echoes do not clear the user's query.
        st.session_state["workspace_search"] = ""
        if selected_pitch_id not in catalog:
            st.session_state["workspace_replays_only"] = False
        _reset_table_selection()
    if comparison_pitch_id in all_ids and (
        comparison_pitch_id != st.session_state.get("_workspace_returned_comparison")
        or "workspace_compare_pitch" not in st.session_state
    ):
        st.session_state["workspace_compare_pitch"] = comparison_pitch_id
    search, availability = st.columns([2, 1])
    query = search.text_input(
        "Search recorded pitches",
        placeholder="For example: 1623_3, athlete 970, or 85.3",
        key="workspace_search",
        on_change=_reset_table_selection,
    )
    replays_only = availability.toggle(
        "Replays available only", key="workspace_replays_only", on_change=_reset_table_selection
    )
    visible = search_pitch_rows(table, query, list(catalog), replays_only=replays_only)
    st.caption(
        f"{len(visible):,} of {len(table):,} recorded pitches match · "
        f"{len(catalog):,} matching pitches have prepared marker replays. "
        "Missing measurements stay missing."
    )
    if visible.empty:
        st.info("No pitches match this search. Clear the text or replay filter to continue.")
        st.session_state["_workspace_last_table_pick"] = None
        return None
    visible_ids = visible.session_pitch.tolist()
    st.session_state["_workspace_visible_ids"] = visible_ids
    if st.session_state.get("workspace_primary_pitch") not in visible_ids:
        st.session_state["workspace_primary_pitch"] = visible_ids[0]
        _reset_table_selection()
    if st.session_state.get("workspace_compare_pitch") not in all_ids:
        current = st.session_state["workspace_primary_pitch"]
        candidates = [identifier for identifier in catalog if identifier != current]
        candidates += [identifier for identifier in all_ids if identifier != current]
        st.session_state["workspace_compare_pitch"] = next(iter(candidates), current)
    current = WorkspaceSelection(
        st.session_state["workspace_primary_pitch"], st.session_state["workspace_compare_pitch"]
    )
    target = st.radio(
        "A row or chart click opens",
        ["Pitch A", "Pitch B"],
        key="workspace_pick_target",
        horizontal=True,
        help="Choose which pane the next table-row or chart-point click fills.",
    )
    table_tab, chart_tab = st.tabs(["Table", "Chart · pick a point"])
    digest = hashlib.sha256(json.dumps(visible_ids).encode()).hexdigest()[:12]
    generation = st.session_state.get("_workspace_table_generation", 0)
    columns = {
        "selected": "Selected",
        "session_pitch": "Pitch ID",
        "user": "Athlete",
        "playing_level": "Level",
        "pitch_speed_mph": "Speed (mph)",
        "elbow_varus_moment": "Elbow moment (N·m)",
        "max_shoulder_internal_rotational_velo": "Shoulder IR (deg/s)",
        "max_rotation_hip_shoulder_separation": "Hip–shoulder sep. (deg)",
        "max_torso_rotational_velo": "Torso rot. (deg/s)",
        "replay_available": "Marker replay",
    }
    shown = visible.assign(selected=selection_roles(visible_ids, current))
    shown = shown[[name for name in columns if name in shown]].rename(columns=columns)
    with table_tab:
        event = st.dataframe(
            shown,
            hide_index=True,
            width="stretch",
            height=300,
            on_select="rerun",
            selection_mode="single-row",
            key=f"workspace_table_{digest}_{generation}",
            column_config={
                "Selected": st.column_config.TextColumn(width="small"),
                "Speed (mph)": st.column_config.NumberColumn(format="%.1f"),
                "Elbow moment (N·m)": st.column_config.NumberColumn(format="%.1f"),
                "Shoulder IR (deg/s)": st.column_config.NumberColumn(format="%.0f"),
                "Hip–shoulder sep. (deg)": st.column_config.NumberColumn(format="%.1f"),
                "Torso rot. (deg/s)": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        st.caption(
            f"Click a row to open it as {target}. Click a column header to sort. "
            "The selectors below also work with a keyboard or touch."
        )
    picked = pitch_from_table_event(event, visible_ids)
    if picked != st.session_state.get("_workspace_last_table_pick"):
        st.session_state["_workspace_last_table_pick"] = picked
        if picked is not None:
            _apply_pick(picked, target)
            _reset_table_selection()
            st.rerun()
    with chart_tab:
        axis_x, axis_y = st.columns(2)
        chart_x = axis_x.selectbox(
            "Horizontal measurement",
            list(MEASURES),
            format_func=measure_label,
            key="workspace_chart_x",
        )
        chart_y = axis_y.selectbox(
            "Vertical measurement",
            list(MEASURES),
            index=1,
            format_func=measure_label,
            key="workspace_chart_y",
        )
        chart = workspace_chart(visible, chart_x, chart_y, current)
        chart_event = None
        if chart is None:
            st.info("No searched pitches have both selected measurements.")
        else:
            chart_generation = st.session_state.get("_workspace_chart_generation", 0)
            chart_event = st.altair_chart(
                chart,
                key=f"workspace_chart_{digest}_{chart_generation}",
                on_select="rerun",
                selection_mode="pitch_pick",
                width="stretch",
            )
            plotted = int((visible[chart_x].notna() & visible[chart_y].notna()).sum())
            st.caption(
                f"{plotted:,} of {len(visible):,} searched pitches have both values. "
                f"Hover for details; click a point to open it as {target}. "
                "Scroll to zoom, drag to pan, double-click to reset."
            )
    chart_pick = selected_pitch_from_event(chart_event, visible_ids)
    if chart_pick != st.session_state.get("_workspace_last_chart_pick"):
        st.session_state["_workspace_last_chart_pick"] = chart_pick
        if chart_pick is not None:
            _apply_pick(chart_pick, target)
            _reset_chart_selection()
            st.rerun()
    first, second = st.columns(2)
    primary = first.selectbox(
        "Pitch A · selected observation",
        visible_ids,
        format_func=lambda identifier: _label(table, identifier),
        key="workspace_primary_pitch",
        on_change=_reset_table_selection,
    )
    comparison = second.selectbox(
        "Pitch B · compare with",
        all_ids,
        format_func=lambda identifier: _label(table, identifier),
        key="workspace_compare_pitch",
    )
    selection = WorkspaceSelection(primary, comparison)
    athlete = table.loc[table.session_pitch.eq(primary), "user"].iloc[0]
    sibling = next_athlete_pitch(table, primary, comparison)
    swap, same_athlete = st.columns(2)
    swap.button(
        "⇄ Swap A and B",
        key="workspace_swap",
        on_click=_swap_pitches,
        disabled=primary == comparison,
        width="stretch",
    )
    same_athlete.button(
        f"B: next pitch by athlete {athlete}",
        key="workspace_same_athlete",
        on_click=_compare_with,
        args=(sibling,),
        disabled=sibling is None,
        help="Within-athlete variation: cycle Pitch B through this athlete's other recorded pitches.",
        width="stretch",
    )
    if primary == comparison:
        st.info("Both panes identify the same recorded pitch. Choose another Pitch B to compare.")
    recordings: list[tuple[dict[str, np.ndarray], dict] | None] = []
    unavailable = {}
    for side, identifier in (("A", primary), ("B", comparison)):
        entry = catalog.get(identifier)
        if entry is None:
            recordings.append(None)
            unavailable[side] = f"No prepared marker replay for source pitch {identifier}."
            continue
        try:
            recordings.append((_verified_replay(directory, entry), entry))
        except (OSError, ValueError, TypeError, KeyError) as error:
            recordings.append(None)
            unavailable[side] = f"Source pitch {identifier}: replay withheld ({error})."
    st.markdown("#### Compare the recorded marker motion")
    document = comparison_replay_html(recordings[0], recordings[1], selection, unavailable)
    st.iframe(
        document, height="content", alt="Two independently controlled measured-marker replays"
    )
    st.download_button(
        "Download these interactive marker replays (HTML)",
        data=document,
        file_name="recorded-pitch-comparison.html",
        mime="text/html",
        key="workspace_replay_download",
    )
    st.markdown("#### The measurements attached to these exact pitches")
    cohort = table if full_frame is None else workspace_table(full_frame)
    if not {primary, comparison} <= set(cohort.session_pitch):
        cohort = table
    st.caption(
        f"B − A differences and percentiles among the {len(cohort):,} recorded study pitches "
        "describe these observations. They are not effects of a mechanics change, grades, "
        "or risk scores, and the five peaks can occur at different instants."
    )
    observed = compare_recorded_pitches(table, primary, comparison)
    observed["percentile_a"] = list(cohort_percentiles(cohort, primary).values())
    observed["percentile_b"] = list(cohort_percentiles(cohort, comparison).values())
    observed = observed[
        ["measure", "unit", "pitch_a", "percentile_a", "pitch_b", "percentile_b"]
        + ["difference_b_minus_a"]
    ]
    st.dataframe(
        observed.rename(
            columns={
                "measure": "Recorded measurement",
                "unit": "Unit",
                "pitch_a": f"A · {primary}",
                "percentile_a": "A percentile",
                "pitch_b": f"B · {comparison}",
                "percentile_b": "B percentile",
                "difference_b_minus_a": "B − A",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={
            f"A · {primary}": st.column_config.NumberColumn(format="%.1f"),
            f"B · {comparison}": st.column_config.NumberColumn(format="%.1f"),
            "B − A": st.column_config.NumberColumn(format="%+.1f"),
            "A percentile": st.column_config.ProgressColumn(
                format="%.0f", min_value=0, max_value=100
            ),
            "B percentile": st.column_config.ProgressColumn(
                format="%.0f", min_value=0, max_value=100
            ),
        },
    )
    st.download_button(
        "Download selected observations and source terms (JSON)",
        data=selected_observations_json(table, selection),
        file_name="recorded-pitch-comparison-data.json",
        mime="application/json",
        key="workspace_data_download",
    )
    with st.expander("All released fields for these two source records"):
        first_row = table.loc[table.session_pitch.eq(primary)].iloc[0]
        second_row = table.loc[table.session_pitch.eq(comparison)].iloc[0]
        fields = pd.DataFrame(
            {
                "Released field": table.columns,
                f"A · {primary}": [
                    str(value) if pd.notna(value) else "Not observed" for value in first_row
                ],
                f"B · {comparison}": [
                    str(value) if pd.notna(value) else "Not observed" for value in second_row
                ],
            }
        )
        st.dataframe(fields, hide_index=True, width="stretch", height=350)
        st.caption(
            "Source field names and released values. The five focal units are shown above; "
            "consult the pinned source dictionaries for the remaining quantities."
        )
    with st.expander("Markers, source records, and measurement definitions"):
        left, right = st.columns(2)
        for container, side, recording in zip((left, right), ("A", "B"), recordings):
            with container:
                if recording is None:
                    st.info(unavailable[side])
                else:
                    _render_markers(recording, side)
        for name, (label, unit, definition) in MEASURES.items():
            st.markdown(f"**{label} ({unit})**")
            st.write(MEASUREMENT_NOTES.get(name, definition))
        st.caption(
            "Released moments and rotational signals come from the source processing. "
            "These skin-marker displays do not independently reconstruct the biomechanical model."
        )
    with st.expander("Prepared video clips for the original examples"):
        st.caption(
            "These clips are animations of measured markers, not camera footage. "
            "Clips are prepared for only the original examples; the interactive replays above "
            "have their own verified source coverage."
        )
        try:
            movie_directory, movie_manifest = load_motion_manifest(project_root)
            movie_entries = {
                entry["session_pitch"]: entry
                for entry in matching_examples(table, movie_manifest["examples"])
            }
            for container, side, identifier in zip(
                st.columns(2), ("A", "B"), (primary, comparison)
            ):
                with container:
                    st.markdown(f"**Pitch {side} · {identifier}**")
                    if identifier not in movie_entries or identifier not in catalog:
                        st.info("No verified matching MP4 clip for this exact source observation.")
                        continue
                    entry = movie_entries[identifier]
                    try:
                        movie = verified_asset(
                            movie_directory,
                            entry["animation_file"],
                            entry["animation_sha256"],
                            ".mp4",
                        )
                        st.video(str(movie))
                    except (OSError, ValueError, KeyError) as error:
                        st.info(f"The matching clip is unavailable: {error}")
        except (OSError, ValueError, KeyError) as error:
            st.info(f"The original clip catalog is unavailable: {error}")
    st.session_state["_workspace_returned_primary"] = primary
    st.session_state["_workspace_returned_comparison"] = comparison
    return selection
