"""Pitcher-versus-pitch variation must use exact formulas and keep pitches with athletes."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.athlete_variation import (
    GRAVITY,
    NORMALIZED,
    athlete_lines,
    normalized_elbow_moment,
    variation_study,
    variation_table,
)

ROOT = Path(__file__).resolve().parents[1]


def synthetic(within: float = 2.0, between: float = 5.0) -> pd.DataFrame:
    """Explicitly synthetic athletes: exact within- and between-athlete slopes."""
    rows = []
    for index, center in enumerate([80.0, 84.0, 88.0, 92.0]):
        for offset in (-1.0, 0.0, 1.0):
            rows.append(
                {
                    "session_pitch": f"test-{index}-{offset:+.0f}",
                    "user": f"test-athlete-{index}",
                    "pitch_speed_mph": center + offset,
                    "elbow_varus_moment": between * center + within * offset,
                    "session_mass_kg": 100 / GRAVITY,
                    "session_height_m": 1.0,
                }
            )
    return pd.DataFrame(rows)


def test_normalization_uses_body_weight_times_height_and_rejects_invalid_sizes():
    frame = pd.DataFrame(
        {
            "elbow_varus_moment": [100.0, 100.0, 100.0, np.nan],
            "session_mass_kg": [100 / GRAVITY, 0.0, 80.0, 80.0],
            "session_height_m": [2.0, 1.8, -1.0, 1.8],
        }
    )
    result = normalized_elbow_moment(frame)
    assert result.iloc[0] == pytest.approx(50.0)
    assert result.iloc[1:].isna().all()


def test_exact_within_and_between_slopes_are_recovered():
    study = variation_study(synthetic(), draws=200, seed=1).set_index("statistic")
    assert study.loc["within_slope_elbow_varus_moment", "estimate"] == pytest.approx(2.0)
    assert study.loc["between_slope_elbow_varus_moment", "estimate"] == pytest.approx(5.0)
    assert study.loc["slope_difference_elbow_varus_moment", "estimate"] == pytest.approx(-3.0)
    # Unit body weight × height makes the normalized moment equal to raw moment / 100 × 100.
    assert study.loc[f"within_slope_{NORMALIZED}", "estimate"] == pytest.approx(2.0)


def test_icc_matches_balanced_one_way_anova():
    frame = synthetic()
    study = variation_study(frame, draws=50, seed=1).set_index("statistic")
    groups = frame.groupby("user").pitch_speed_mph
    k, n = groups.ngroups, 3
    msb = n * ((groups.mean() - frame.pitch_speed_mph.mean()) ** 2).sum() / (k - 1)
    msw = ((frame.pitch_speed_mph - groups.transform("mean")) ** 2).sum() / (len(frame) - k)
    expected = (msb - msw) / (msb + (n - 1) * msw)
    assert study.loc["icc_pitch_speed_mph", "estimate"] == pytest.approx(expected)


def test_incomplete_pitches_are_excluded_not_imputed():
    frame = synthetic()
    frame.loc[0, "elbow_varus_moment"] = np.nan
    frame.loc[1, "session_mass_kg"] = 0.0
    table = variation_table(frame)
    assert len(table) == len(frame) - 2
    assert not table[["elbow_varus_moment", NORMALIZED]].isna().any().any()


def test_resampling_is_seeded_and_intervals_bracket_released_estimates():
    frame = pd.read_csv(
        ROOT / "assets/demo/reports/analysis.csv", dtype={"user": str, "session_pitch": str}
    )
    first = variation_study(frame, draws=400, seed=7)
    second = variation_study(frame, draws=400, seed=7)
    pd.testing.assert_frame_equal(first, second)
    assert first.attrs["pitches"] == 411 and first.attrs["athletes"] == 100
    assert ((first.low <= first.estimate) & (first.estimate <= first.high)).all()


def test_too_few_athletes_or_missing_fields_are_refused():
    with pytest.raises(ValueError, match="three athletes"):
        variation_study(synthetic().query("user != 'test-athlete-0' and user != 'test-athlete-1'"))
    with pytest.raises(ValueError, match="missing fields"):
        variation_study(synthetic().drop(columns="session_height_m"))


def test_athlete_lines_cover_each_athletes_own_speed_range():
    lines = athlete_lines(variation_table(synthetic()), "elbow_varus_moment")
    assert len(lines) == 8
    first = lines.loc[lines.user.eq("test-athlete-0")]
    assert first.pitch_speed_mph.tolist() == [79.0, 81.0]
    assert first.elbow_varus_moment.tolist() == pytest.approx([398.0, 402.0])


def test_documented_results_match_the_released_computation():
    frame = pd.read_csv(
        ROOT / "assets/demo/reports/analysis.csv", dtype={"user": str, "session_pitch": str}
    )
    study = variation_study(frame).set_index("statistic")
    document = (ROOT / "docs/ATHLETE_VARIATION.md").read_text(encoding="utf-8")
    for name in (f"within_slope_{NORMALIZED}", f"between_slope_{NORMALIZED}"):
        row = study.loc[name]
        assert f"{row.estimate:.3f} [{row.low:.3f}, {row.high:.3f}]" in document


def test_hosted_study_view_renders_the_variation_analysis():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60)
    app.query_params["page"] = "study"
    app.run()
    app.radio(key="study_mode").set_value("Pitcher vs. pitch variation").run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("between pitchers" in item.label.lower() for item in app.metric)
    app.radio(key="variation_outcome").set_value("elbow_varus_moment").run()
    assert not app.exception, [item.value for item in app.exception]
