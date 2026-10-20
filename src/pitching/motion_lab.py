"""Inspect measured markers and released signals without inventing a shared clock.

The self-contained viewer projects measured 3D points for display only. Its
projection, guide links, and marker groups are not a biomechanical reconstruction.
No network request, filtering, model fitting, or inverse dynamics runs here.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from pitching.trace_examples import SIGNALS
from pitching.trace_viewer import interval_peak, load_trace_example
from pitching.video_lab import (
    SOURCE_BASE,
    SOURCE_COMMIT,
    load_marker_frames,
    load_motion_manifest,
    matching_examples,
    verified_asset,
)

_REGIONS = {
    "Head": {"LFHD", "RFHD", "LBHD", "RBHD"},
    "Upper limbs": {
        "LSHO",
        "RSHO",
        "LUPA",
        "RUPA",
        "LELB",
        "RELB",
        "LMELB",
        "RMELB",
        "LFRM",
        "RFRM",
        "LWRA",
        "RWRA",
        "LWRB",
        "RWRB",
        "LFIN",
        "RFIN",
    },
    "Trunk": {
        "C7",
        "CLAV",
        "STRN",
        "T10",
        "LBAK",
        "RBAK",
        "LASI",
        "RASI",
        "LPSI",
        "RPSI",
        "LIC",
        "RIC",
    },
    "Lower limbs": {
        "LTHI",
        "RTHI",
        "LKNE",
        "RKNE",
        "LMKNE",
        "RMKNE",
        "LTIB",
        "RTIB",
        "LANK",
        "RANK",
        "LMANK",
        "RMANK",
        "LHEE",
        "RHEE",
        "LTOE",
        "RTOE",
    },
}

MEASUREMENT_NOTES = {
    "max_rotation_hip_shoulder_separation": (
        "The released signal is torso orientation relative to the pelvis around the source "
        "z coordinate. The operation below selects its largest finite value in the chosen "
        "window. It is not a projected shoulder/hip-line angle or necessarily the angle at foot plant."
    ),
    "max_shoulder_internal_rotational_velo": (
        "The source supplies shoulder_velo_z as a processed rotational velocity. Its sign is "
        "retained. Three-dimensional angular velocity is not generally a componentwise "
        "derivative of Euler angles; this viewer does not reproduce the source processing."
    ),
    "max_torso_rotational_velo": (
        "The source supplies torso_velo_z as a processed axial rotational velocity in deg/s. "
        "A finite-sample maximum summarizes the chosen window. Peak magnitudes alone do not "
        "establish the timing of an energy-transfer sequence."
    ),
    "elbow_varus_moment": (
        "The source supplies elbow_moment_y as an internal net joint moment. Producing a "
        "moment requires an appropriate dynamics model, motion, external forces, inertial "
        "parameters, and timing. A visible elbow angle does not compute this signal. It is "
        "not an isolated ligament force, injury probability, or a safe-loading threshold."
    ),
}


def marker_regions(labels: list[str] | np.ndarray) -> dict[str, list[int]]:
    """Return explicit skin-marker groups, retaining unclassified markers in the full view."""
    names = [str(value) for value in labels]
    return {
        "All markers": list(range(len(names))),
        **{
            name: [index for index, label in enumerate(names) if label in members]
            for name, members in _REGIONS.items()
        },
    }


def viewer_payload(arrays: dict[str, np.ndarray], entry: dict[str, Any]) -> dict[str, Any]:
    """Create strict JSON-ready display data, preserving every missing coordinate as null."""
    points = arrays["positions_m"]
    complete = np.isfinite(points).all(axis=2)
    finite_points = points[complete]
    if finite_points.size:
        low, high = finite_points.min(axis=0), finite_points.max(axis=0)
        center = ((low + high) / 2).tolist()
        radius = max(float((high - low).max()) / 2, 0.25) * 1.15
    else:
        center, radius = [0.0, 0.0, 0.0], 1.0
    positions = np.where(np.isfinite(points), points, None).tolist()
    labels = [str(value) for value in arrays["labels"]]
    return {
        "pitch": str(entry["session_pitch"]),
        "athlete": str(entry["user"]),
        "positions": positions,
        "times": arrays["times_s"].tolist(),
        "labels": labels,
        "links": arrays["links"].tolist(),
        "regions": marker_regions(labels),
        "center": center,
        "radius": radius,
        "source_rate": float(entry["point_rate_hz"]),
    }


def marker_viewer_html(arrays: dict[str, np.ndarray], entry: dict[str, Any]) -> str:
    """An offline, keyboard-accessible canvas replay with no external script dependencies.

    JSON escapes '<' so even a hostile marker label cannot terminate the script
    element. Dynamic text uses textContent; source strings never become HTML.
    """
    payload = json.dumps(viewer_payload(arrays, entry), allow_nan=False, separators=(",", ":"))
    for character, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        payload = payload.replace(character, escaped)
    payload = payload.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    heading = html.escape(f"Recorded pitch {entry['session_pitch']} · athlete {entry['user']}")
    page = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Measured-marker motion lab</title><style>
*{box-sizing:border-box}body{margin:0;color:#172b3a;background:white;font:14px system-ui,sans-serif}
.lab{max-width:1000px;margin:auto;padding:10px;border:1px solid #d7e0e5;border-radius:12px}
h2{font-size:17px;margin:0 0 5px}.muted{color:#4f6473;font-size:12px;line-height:1.5;margin:4px 0}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}label{font-size:12px;display:flex;gap:5px;align-items:center}
button,select{font:inherit;color:inherit;background:#f4f7f9;border:1px solid #b9cbd5;border-radius:6px;padding:6px;min-height:34px}
button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #e5a359;outline-offset:2px}
button{cursor:pointer}#play{background:#007c91;color:white;border-color:#007c91}
.range{width:100%;accent-color:#007c91;min-height:30px}canvas{width:100%;display:block;touch-action:none;border-radius:8px;background:#f7fafb}
.status{font-variant-numeric:tabular-nums;min-height:38px;line-height:1.5;font-size:12px}
a{color:#006e84}.license{font-size:11px;color:#4f6473;line-height:1.4;margin-top:9px}
@media(max-width:500px){.lab{padding:8px}.row{gap:6px}label,select,button{font-size:12px}select{max-width:180px}}
</style></head><body><main class="lab">
<h2>__HEADING__</h2><p class="muted">Measured skin markers · drag the view to rotate · source coordinates in meters</p>
<div class="row"><label>Highlight <select id="region" aria-label="Highlight marker region"></select></label>
<label>Inspect <select id="marker" aria-label="Inspect a measured marker"></select></label>
<label><input type="checkbox" id="labels">Labels</label></div>
<canvas id="view" role="img" aria-label="Rotatable measured-marker view; use camera buttons and the frame slider for keyboard controls"></canvas>
<div class="row"><button id="front">X–Z view</button><button id="side">Y–Z view</button><button id="reset">Reset view</button>
<button id="zin" aria-label="Zoom in">+</button><button id="zout" aria-label="Zoom out">−</button></div>
<label for="frame">Marker replay frame</label><input id="frame" class="range" aria-label="Marker replay frame" type="range" min="0" value="0" step="1">
<div class="row"><button id="prev" aria-label="Previous marker frame">Previous</button><button id="play">Play</button>
<button id="next" aria-label="Next marker frame">Next</button><label>Speed <select id="speed" aria-label="Marker replay speed"><option value="0.25">0.25×</option><option value="0.5" selected>0.5×</option><option value="1">1×</option></select></label></div>
<div id="status" class="status" aria-live="polite"></div>
<p class="muted">Marker clock: seconds from the C3D start. Guide links are visual aids, not anatomical joint centers. Missing markers stay missing.</p>
<p class="muted"><strong>Marker–signal timing is not verified.</strong> This control does not move a processed-signal cursor or label a release frame.</p>
<div class="license">Source: Driveline Baseball Research &amp; Development, OpenBiomechanics Project.
<a href="__SOURCE__" target="_blank" rel="noopener">Pinned source</a> ·
<a href="__LICENSE__" target="_blank" rel="noopener">CC BY-NC-SA 4.0 + professional-sports / financial-analysis affiliation restriction</a>.
Changes: selected, downsampled, projected marker replay. No camera footage or new dynamics calculation.</div>
</main><script>
const D=__DATA__;
const el=id=>document.getElementById(id),cv=el('view'),ctx=cv.getContext('2d');
let current=0,az=-.9,elev=.22,zoom=1,playing=false,last=null,carry=0,drag=null;
const region=el('region'),marker=el('marker'),slider=el('frame');slider.max=D.positions.length-1;
for(const name of Object.keys(D.regions)){const o=document.createElement('option');o.value=name;o.textContent=name;region.append(o)}
const none=document.createElement('option');none.value='-1';none.textContent='No marker selected';marker.append(none);
D.labels.forEach((name,i)=>{const o=document.createElement('option');o.value=i;o.textContent=name;marker.append(o)});
function valid(p){return p&&p.every(v=>typeof v==='number'&&Number.isFinite(v))}
function project(p){const q=p.map((v,i)=>v-D.center[i]),ca=Math.cos(az),sa=Math.sin(az),ce=Math.cos(elev),se=Math.sin(elev),x=ca*q[0]-sa*q[1],y=sa*q[0]+ca*q[1];return [x,se*y+ce*q[2],ce*y-se*q[2]]}
function draw(){
 const w=Math.max(200,cv.clientWidth),h=Math.max(220,Math.min(365,w*.72)),dpr=window.devicePixelRatio||1;
 if(cv.width!==Math.round(w*dpr)||cv.height!==Math.round(h*dpr)){cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr);cv.style.height=h+'px'}
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);const scale=Math.min(w,h)*.43/D.radius*zoom;
 const screen=p=>{const q=project(p);return[w/2+q[0]*scale,h*.52-q[1]*scale,q[2]]};
 const pts=D.positions[current],active=new Set(D.regions[region.value]),selected=Number(marker.value);
 const floorZ=D.center[2]-D.radius*.86,span=D.radius*.9;
 ctx.lineWidth=1;ctx.strokeStyle='#e3ebef';
 for(let k=-2;k<=2;k++){for(let a=0;a<2;a++){const t=k/2*span,p=D.center.slice(),q=D.center.slice();p[2]=q[2]=floorZ;p[a]-=span;q[a]+=span;p[1-a]+=t;q[1-a]+=t;const A=screen(p),B=screen(q);ctx.beginPath();ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);ctx.stroke()}}
 for(const link of D.links){const [a,b]=link;if(!valid(pts[a])||!valid(pts[b]))continue;const A=screen(pts[a]),B=screen(pts[b]);ctx.strokeStyle=(active.has(a)&&active.has(b))?'#577686':'#cbd7de';ctx.lineWidth=1.6;ctx.beginPath();ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);ctx.stroke()}
 const indices=pts.map((p,i)=>i).filter(i=>valid(pts[i])).sort((a,b)=>screen(pts[a])[2]-screen(pts[b])[2]);
 for(const i of indices){const p=screen(pts[i]);ctx.beginPath();ctx.arc(p[0],p[1],i===selected?6:active.has(i)?3.7:2.5,0,Math.PI*2);ctx.fillStyle=i===selected?'#d77727':active.has(i)?'#007c91':'#aebfc9';ctx.fill();if(el('labels').checked||i===selected){ctx.font='11px system-ui';ctx.fillStyle='#172b3a';ctx.fillText(D.labels[i],p[0]+6,p[1]-5)}}
 const origin=[w-66,h-45],axisLength=26;
 for(const [i,name,color]of[[0,'X','#a9493c'],[1,'Y','#417b42'],[2,'Z','#356da0']]){const base=D.center.slice(),end=D.center.slice();end[i]+=1;const b=project(base),e=project(end),dx=(e[0]-b[0])*axisLength,dy=-(e[1]-b[1])*axisLength;ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(...origin);ctx.lineTo(origin[0]+dx,origin[1]+dy);ctx.stroke();ctx.fillStyle=color;ctx.font='11px system-ui';ctx.fillText(name,origin[0]+dx+3,origin[1]+dy+3)}
 let s='Displayed sample '+(current+1)+' / '+D.positions.length+' · marker time '+D.times[current].toFixed(3)+' s · '+indices.length+' / '+D.labels.length+' complete markers';
 if(selected>=0){const p=pts[selected];s+='\n'+D.labels[selected]+': '+(valid(p)?p.map((v,i)=>['X','Y','Z'][i]+' '+v.toFixed(3)+' m').join(' · '):'missing coordinates')}
 el('status').textContent=s;el('status').style.whiteSpace='pre-line';slider.value=current;
}
function stop(){playing=false;el('play').textContent='Play';last=null;carry=0}
function step(n){stop();current=Math.max(0,Math.min(D.positions.length-1,current+n));draw()}
el('prev').onclick=()=>step(-1);el('next').onclick=()=>step(1);slider.oninput=()=>{stop();current=Number(slider.value);draw()};
el('play').onclick=()=>{playing=!playing;last=null;carry=0;if(playing&&current===D.positions.length-1)current=0;el('play').textContent=playing?'Pause':'Play';draw()};
region.onchange=draw;marker.onchange=draw;el('labels').onchange=draw;
el('front').onclick=()=>{az=0;elev=.12;draw()};el('side').onclick=()=>{az=Math.PI/2;elev=.12;draw()};el('reset').onclick=()=>{az=-.9;elev=.22;zoom=1;draw()};
el('zin').onclick=()=>{zoom=Math.min(2.5,zoom*1.15);draw()};el('zout').onclick=()=>{zoom=Math.max(.5,zoom/1.15);draw()};
cv.onpointerdown=e=>{drag=[e.clientX,e.clientY];cv.setPointerCapture(e.pointerId)};
cv.onpointermove=e=>{if(!drag)return;az+=(e.clientX-drag[0])*.01;elev=Math.max(-1.4,Math.min(1.4,elev+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw()};
cv.onpointerup=cv.onpointercancel=()=>{drag=null};
function tick(now){if(playing){if(last===null)last=now;carry+=(now-last)/1000*Number(el('speed').value);last=now;let changed=false;while(current<D.times.length-1&&carry>=D.times[current+1]-D.times[current]){carry-=D.times[current+1]-D.times[current];current++;changed=true}if(current===D.times.length-1)stop();if(changed)draw()}requestAnimationFrame(tick)}
new ResizeObserver(draw).observe(cv.parentElement);draw();requestAnimationFrame(tick);
</script></body></html>"""
    return (
        page.replace("__HEADING__", heading)
        .replace("__SOURCE__", f"{SOURCE_BASE}/baseball_pitching/README.md")
        .replace("__LICENSE__", f"{SOURCE_BASE}/LICENSE-DATA.md")
        .replace("__DATA__", payload)
    )


def clock_audit(arrays: dict[str, np.ndarray], trace: pd.DataFrame, entry: dict) -> dict:
    """Describe time-grid evidence without promoting a numerical match to verified alignment."""
    sample_rate = float(entry["point_rate_hz"])
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("The source marker sample rate must be finite and positive.")
    time = pd.to_numeric(trace["time"], errors="raise").to_numpy(dtype=float)
    if not len(time) or not np.isfinite(time).all() or np.any(np.diff(time) <= 0):
        raise ValueError("The processed trace must have a finite, increasing time grid.")
    return {
        "status": "unverified",
        "marker_clock": "seconds relative to C3D start; downsampled display",
        "trace_clock": "original processed CSV time",
        "source_marker_samples": int(entry["n_source_frames"]),
        "processed_samples": len(time),
        "displayed_marker_samples": len(arrays["times_s"]),
        "source_rate_hz": sample_rate,
        "trace_matches_zero_based_source_grid": bool(
            len(time) == entry["n_source_frames"]
            and np.allclose(time, np.arange(len(time)) / sample_rate, atol=5.1e-5, rtol=0)
        ),
        "interpretation": (
            "Equal sample counts and a compatible grid support source compatibility, "
            "but do not independently establish a shared time origin, processing delay, "
            "or event-to-marker mapping. No synchronized cursor is enabled."
        ),
    }


def marker_coordinate_table(arrays: dict[str, np.ndarray], index: int) -> pd.DataFrame:
    """Return one observed display sample with missing coordinates intact."""
    if not 0 <= index < len(arrays["times_s"]):
        raise ValueError("Marker sample is outside the prepared recording.")
    table = pd.DataFrame(arrays["positions_m"][index], columns=["X (m)", "Y (m)", "Z (m)"])
    table.insert(0, "Marker", arrays["labels"])
    table["Complete coordinates"] = np.isfinite(arrays["positions_m"][index]).all(axis=1)
    return table


def _trace_chart(
    frame: pd.DataFrame, column: str, unit: str, index: int, start: float, stop: float
):
    values = pd.to_numeric(frame[column], errors="raise").replace([np.inf, -np.inf], np.nan)
    chart_data = pd.DataFrame({"time": frame.time, "value": values})
    chart_data["segment"] = chart_data.value.isna().cumsum()
    finite = chart_data.dropna(subset=["value"])
    curve = (
        alt.Chart(finite)
        .mark_line(color="#007C91", strokeWidth=2)
        .encode(
            x=alt.X("time:Q", title="Processed trace time (s)"),
            y=alt.Y("value:Q", title=f"Value ({unit})", scale=alt.Scale(zero=False)),
            detail="segment:N",
            tooltip=[
                alt.Tooltip("time:Q", title="Source time (s)", format=".4f"),
                alt.Tooltip("value:Q", title=f"Value ({unit})", format=".3f"),
            ],
        )
    )
    window = (
        alt.Chart(pd.DataFrame({"start": [start], "stop": [stop]}))
        .mark_rect(color="#007C91", opacity=0.07)
        .encode(x="start:Q", x2="stop:Q")
    )
    cursor = (
        alt.Chart(pd.DataFrame({"time": [float(frame.time.iloc[index])]}))
        .mark_rule(color="#D77727", strokeWidth=2)
        .encode(x="time:Q")
    )
    return (window + curve + cursor).properties(height=270)


def _jump_to_peak(frame: pd.DataFrame, column: str, key: str, start: float, stop: float) -> None:
    selected = frame.loc[frame.time.between(start, stop)]
    finite = np.isfinite(selected[column].to_numpy(dtype=float))
    if finite.any():
        st.session_state[key] = int(selected.loc[finite, column].idxmax())


def _render_trace_lab(project_root: Path, entry: dict, arrays: dict[str, np.ndarray]) -> None:
    st.subheader("Inspect the released signal")
    st.caption("This cursor uses the processed-trace clock and does not control the marker replay.")
    try:
        frame, trace_entry, manifest = load_trace_example(project_root, entry["session_pitch"])
        if str(trace_entry.get("user")) != entry["user"]:
            raise ValueError("Trace athlete does not match the selected marker recording.")
        if len(frame) != trace_entry["n_samples"]:
            raise ValueError("Trace sample count does not match its manifest.")
        audit = clock_audit(arrays, frame, entry)
    except (OSError, ValueError, KeyError) as error:
        st.info(f"Prepared processed signals are unavailable: {error}")
        return
    metric = st.selectbox(
        "Measurement to inspect",
        list(SIGNALS),
        format_func=lambda name: f"{SIGNALS[name]['label']} ({SIGNALS[name]['unit']})",
        key="lab_trace_metric",
    )
    signal = SIGNALS[metric]
    st.write(MEASUREMENT_NOTES[metric])
    start, stop = st.slider(
        "Analysis window on the processed-trace clock (s)",
        float(frame.time.min()),
        float(frame.time.max()),
        (float(frame.time.min()), float(frame.time.max())),
        step=0.001,
        key=f"lab_trace_window_{entry['session_pitch']}",
    )
    peak = interval_peak(frame, signal["column"], start, stop)
    comparison = next(item for item in trace_entry["comparison"] if item["metric"] == metric)
    first, second, third = st.columns(3)
    first.metric(f"Published POI ({signal['unit']})", f"{comparison['published_poi']:.2f}")
    second.metric(
        f"Window maximum ({signal['unit']})",
        "Missing" if peak["peak"] is None else f"{peak['peak']:.2f}",
    )
    third.metric("Missing samples in window", peak["n_missing"])
    key = f"lab_trace_sample_{entry['session_pitch']}"
    st.button(
        "Jump the trace cursor to this window's maximum",
        disabled=peak["peak"] is None,
        on_click=_jump_to_peak,
        args=(frame, signal["column"], key, start, stop),
        key="lab_trace_peak",
    )
    index = st.slider("Processed trace sample", 0, len(frame) - 1, 0, key=key)
    value = float(frame[signal["column"]].iloc[index])
    text = f"{value:.3f} {signal['unit']}" if np.isfinite(value) else "missing"
    st.caption(
        f"Source sample {index} · processed time {frame.time.iloc[index]:.4f} s · value {text}."
    )
    st.altair_chart(
        _trace_chart(frame, signal["column"], signal["unit"], index, start, stop), width="stretch"
    )
    st.caption(
        "Calculation: retain finite observations in the selected window, then take their "
        "largest signed value. Gaps stay missing. Agreement with the released POI does not "
        "independently validate filtering, coordinate definitions, or inverse dynamics."
    )
    if metric == "max_shoulder_internal_rotational_velo":
        st.info(manifest["shoulder_convention_note"])
    with st.expander("Source events, trace provenance, and timing audit"):
        st.write(
            "Event times below belong to the processed-trace clock only. Foot contact and "
            "foot plant use the source's 10% and 100% body-weight thresholds. ER/IR mean "
            "shoulder external/internal rotation. No event is assigned to a marker frame."
        )
        st.json({"events_on_trace_clock": trace_entry["events"], "clock_audit": audit})
        st.json(
            {
                "source_commit": manifest["source_commit"],
                "archives": manifest["archives"],
                "comparison": comparison,
            }
        )


def render_motion_lab(
    frame: pd.DataFrame, project_root: Path, selected_pitch_id: str | None = None
) -> str | None:
    """Render one eligible recording, returning its actual ID for parent URL synchronization."""
    st.subheader("Motion and measurement lab")
    st.write(
        "Inspect a recorded delivery in 3D, then explore how a released signal becomes a "
        "point-of-interest value. These are measured skin markers and processed source signals."
    )
    try:
        directory, manifest = load_motion_manifest(project_root)
        entries = matching_examples(frame, manifest["examples"])
        if not entries:
            st.info(
                "No prepared recording matches both pitch and athlete in the current filters. Clear the filters to inspect the three examples."
            )
            return None
        by_id = {item["session_pitch"]: item for item in entries}
        key = "lab_motion_pitch"
        previous = st.session_state.get("_lab_last_returned")
        if selected_pitch_id in by_id and selected_pitch_id != previous:
            st.session_state[key] = selected_pitch_id
        elif st.session_state.get(key) not in by_id:
            st.session_state.pop(key, None)
        if selected_pitch_id is not None and selected_pitch_id not in by_id:
            st.info(
                f"Pitch {selected_pitch_id} has no prepared recording in this view. The viewer identifies the available pitch actually displayed."
            )
        chosen = st.selectbox(
            "Recorded lab pitch",
            list(by_id),
            format_func=lambda name: (
                f"Pitch {name} · athlete {by_id[name]['user']} · {by_id[name]['poi']['pitch_speed_mph']:.1f} mph"
            ),
            key=key,
        )
        entry = by_id[chosen]
        archive = verified_asset(directory, entry["frames_file"], entry["frames_sha256"], ".npz")
        arrays = load_marker_frames(archive, entry["n_frames"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.warning(f"The prepared motion lab cannot be displayed: {error}")
        return None
    st.session_state["_lab_last_returned"] = chosen
    st.info(
        "Marker–signal timing is not verified. The replay and signal inspector have "
        "independent controls; no ball-release frame or synchronized cursor is inferred."
    )
    document = marker_viewer_html(arrays, entry)
    components.html(document, height=820, scrolling=True)
    st.download_button(
        "Download this interactive marker replay (HTML)",
        data=document,
        file_name=f"obp-marker-lab-{chosen}.html",
        mime="text/html",
        key="lab_marker_download",
    )
    st.caption(
        f"Source marker sampling: {entry['point_rate_hz']:g} Hz · {entry['n_source_frames']} "
        f"source samples · {entry['n_frames']} displayed samples. Playback uses the "
        "prepared sample timestamps. The HTML file works offline."
    )
    with st.expander("Keyboard-accessible coordinate inspector and source details"):
        st.caption(
            "This independent table inspector does not change the replay's client-side frame slider."
        )
        index = st.slider(
            "Coordinate-table marker sample",
            0,
            len(arrays["times_s"]) - 1,
            0,
            key=f"lab_marker_table_{chosen}",
        )
        st.caption(f"Marker clock: {arrays['times_s'][index]:.4f} s from C3D start.")
        st.dataframe(marker_coordinate_table(arrays, index), hide_index=True, width="stretch")
        st.json(
            {
                "session_pitch": chosen,
                "user": entry["user"],
                "source_file": entry["filename_new"],
                "source_sha256": entry["source_file_sha256"],
                "prepared_frames_sha256": entry["frames_sha256"],
                "source_commit": SOURCE_COMMIT,
            }
        )
    _render_trace_lab(project_root, entry, arrays)
    return chosen
