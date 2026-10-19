"""Trace transformations preserve missing observations and source conventions."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pitching.trace_examples import EVENTS, add_convention_aliases, join_traces
from pitching.trace_viewer import interval_peak, load_trace_example


def _trace():
    return pd.DataFrame(
        {
            "session_pitch": ["synthetic"] * 3,
            "time": [0.0, 0.1, 0.2],
            **{event: [0.1] * 3 for event in EVENTS},
        }
    )


def test_join_rejects_missing_samples_or_conflicting_events():
    left = _trace().assign(torso_pelvis_angle_z=[1.0, 2.0, 3.0])
    right = _trace().assign(shoulder_velo_z=[10.0, 20.0, 30.0])
    joined = join_traces(left, right)
    assert len(joined) == 3
    with pytest.raises(ValueError, match="time grids differ"):
        join_traces(left, right.iloc[:-1])
    right.loc[0, "BR_time"] = 0.15
    with pytest.raises(ValueError, match="Conflicting BR_time"):
        join_traces(left, right)


def test_convention_aliases_preserve_native_sign_and_missing_values():
    source = _trace().assign(
        torso_pelvis_angle_z=[10.0, 30.0, 20.0],
        shoulder_velo_z=[np.nan, -5.0, 25.0],
        torso_velo_z=[np.nan, 3.0, 4.0],
        elbow_moment_y=[np.nan, 10.0, 20.0],
    )
    result = add_convention_aliases(source)
    np.testing.assert_equal(
        result.shoulder_internal_rotation_velocity_deg_s.to_numpy(),
        source.shoulder_velo_z.to_numpy(),
    )
    assert pd.isna(result.loc[0, "elbow_varus_moment_nm"])
    assert result.loc[2, "elbow_varus_moment_nm"] == 20.0
    assert "hip_shoulder_separation_deg" not in source


def test_interval_peak_depends_on_window_and_never_fills_gaps():
    frame = _trace().assign(value=[np.nan, 30.0, 20.0])
    assert interval_peak(frame, "value", 0.0, 0.2) == {
        "peak": 30.0,
        "time": 0.1,
        "n_samples": 3,
        "n_missing": 1,
    }
    assert interval_peak(frame, "value", 0.2, 0.2)["peak"] == 20.0
    assert interval_peak(frame, "value", 0.0, 0.0)["peak"] is None
    with pytest.raises(ValueError):
        interval_peak(frame, "value", 0.2, 0.0)


def test_prepared_real_trace_peaks_agree_with_published_examples():
    root = Path(__file__).resolve().parents[1]
    if not (root / "assets/traces/manifest.json").is_file():
        pytest.skip("Prepared visual assets are absent.")
    for pitch_id in ("1393_3", "1623_3", "2916_4"):
        frame, entry, _ = load_trace_example(root, pitch_id)
        for comparison in entry["comparison"]:
            measured = interval_peak(
                frame, comparison["display_column"], frame.time.min(), frame.time.max()
            )
            assert measured["peak"] == pytest.approx(comparison["published_poi"], abs=1e-4)
