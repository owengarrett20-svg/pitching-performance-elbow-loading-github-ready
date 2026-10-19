"""Inspect real OBP processed traces and their published scalar summaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from pitching.data import COMMIT
from pitching.trace_examples import SIGNALS


def load_trace_example(project_root: Path, pitch_id: str) -> tuple[pd.DataFrame, dict, dict]:
    base = Path(project_root) / "assets/traces"
    manifest = json.loads((base / "manifest.json").read_text())
    if manifest.get("source_commit") != COMMIT:
        raise ValueError("Trace source revision differs from the reviewed dataset.")
    matches = [item for item in manifest["examples"] if item["session_pitch"] == pitch_id]
    if len(matches) != 1:
        raise ValueError("No unique prepared trace for this pitch.")
    example = matches[0]
    relative = Path(example["file"])
    if relative.name != example["file"] or relative.suffix != ".csv":
        raise ValueError("Invalid prepared trace path.")
    path = base / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != example["sha256"]:
        raise ValueError("Prepared trace checksum differs; restore the reviewed example.")
    frame = pd.read_csv(path, dtype={"session_pitch": "string"})
    if set(frame.session_pitch) != {pitch_id}:
        raise ValueError("Prepared trace pitch ID does not match its manifest.")
    if (
        frame.time.isna().any()
        or frame.time.duplicated().any()
        or not frame.time.is_monotonic_increasing
    ):
        raise ValueError("Prepared trace has an invalid time grid.")
    return frame, example, manifest


def interval_peak(frame: pd.DataFrame, column: str, start: float, stop: float) -> dict:
    """A transparent finite-sample maximum, not a reconstructed upstream algorithm."""
    if start > stop:
        raise ValueError("Interval start must not exceed stop.")
    selected = frame.loc[frame.time.between(start, stop)]
    finite = np.isfinite(selected[column].to_numpy(dtype=float))
    observed = selected.loc[finite]
    peak = None if observed.empty else float(observed[column].max())
    at = None if observed.empty else float(observed.loc[observed[column].idxmax(), "time"])
    return {"peak": peak, "time": at, "n_samples": len(selected), "n_missing": int((~finite).sum())}


def render_trace_lesson(project_root: Path, pitch_id: str) -> None:
    import matplotlib.pyplot as plt

    st.subheader("From a time series to a point-of-interest value")
    st.caption(
        "These are released processed signals for the same pitch ID, not values inferred "
        "from the animation or a single camera. The video clock and trace clock are not synchronized here."
    )
    try:
        frame, example, manifest = load_trace_example(project_root, pitch_id)
    except (OSError, ValueError, KeyError) as exc:
        st.info(f"Prepared processed trace is unavailable: {exc}")
        return
    metric = st.selectbox(
        "Processed measurement",
        list(SIGNALS),
        format_func=lambda value: f"{SIGNALS[value]['label']} ({SIGNALS[value]['unit']})",
        key="trace_metric",
    )
    signal = SIGNALS[metric]
    column = signal["column"]
    left, right = float(frame.time.min()), float(frame.time.max())
    start, stop = st.slider(
        "Trace interval (s)",
        left,
        right,
        (left, right),
        step=0.001,
        key=f"trace_interval_{pitch_id}",
    )
    measured = interval_peak(frame, column, start, stop)
    comparison = next(item for item in example["comparison"] if item["metric"] == metric)
    cards = st.columns(3)
    cards[0].metric(f"Published POI ({signal['unit']})", f"{comparison['published_poi']:.2f}")
    cards[1].metric(
        f"Maximum in interval ({signal['unit']})",
        "No finite samples" if measured["peak"] is None else f"{measured['peak']:.2f}",
    )
    cards[2].metric("Missing samples in interval", measured["n_missing"])
    fig, axis = plt.subplots(figsize=(10, 4), layout="constrained")
    axis.plot(
        frame.time,
        frame[column],
        color="#007C91",
        linewidth=1.6,
        label=f"Released {signal['raw_column']} (sign retained)",
    )
    axis.axvspan(start, stop, color="#007C91", alpha=0.08)
    if measured["time"] is not None:
        axis.scatter(
            [measured["time"]],
            [measured["peak"]],
            s=50,
            color="#C24F25",
            zorder=3,
            label="Maximum in selected interval",
        )
    event_names = {
        "fp_100_time": "Foot plant (100% BW)",
        "MER_time": "Maximum ER",
        "BR_time": "Ball release",
        "MIR_time": "Maximum IR",
    }
    for key, name in event_names.items():
        event = example["events"].get(key)
        if event is not None:
            axis.axvline(
                event, color="gray", linewidth=0.8, linestyle="--", label=f"{name}: {event:.3f}s"
            )
    axis.set(
        xlabel="Original processed trace time (s)", ylabel=f"{signal['label']} ({signal['unit']})"
    )
    axis.legend(loc="best", fontsize=8)
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.caption(
        "Move the interval endpoints to see why the peak depends on the analysis window. "
        "Gaps remain missing. The displayed maximum is a simple finite-sample operation; "
        "agreement with a published POI does not independently validate its filtering, "
        "coordinate definitions, windowing, or inverse dynamics."
    )
    if metric == "max_shoulder_internal_rotational_velo":
        st.info(manifest["shoulder_convention_note"])
    with st.expander("Trace provenance and event definitions"):
        st.write(
            "Foot contact is the source 10% body-weight threshold; foot plant is the 100% "
            "threshold. ER/IR denote shoulder external/internal rotation events. "
            "Marker-derived traces are sampled at 360 Hz in the source."
        )
        st.json(
            {
                "source_commit": manifest["source_commit"],
                "session_pitch": pitch_id,
                "archives": manifest["archives"],
                "events": example["events"],
                "comparison": comparison,
            }
        )
