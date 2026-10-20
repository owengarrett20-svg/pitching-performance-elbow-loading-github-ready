"""Explorer fixtures are synthetic records, never additions to research data."""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.pitch_explorer import (
    DATA_TERMS,
    SOURCE_COMMIT,
    build_scatter_chart,
    compare_recorded_pitches,
    prepare_scatter_data,
    recorded_pitch_export,
    selected_pitch_from_event,
)


@pytest.fixture
def recorded():
    """Invented test measurements exercise identity, missingness, and mean units."""
    return pd.DataFrame(
        {
            "session_pitch": ["test-a1", "test-a2", "test-b1", "test-b2"],
            "user": ["test-athlete-a", "test-athlete-a", "test-athlete-b", "test-athlete-b"],
            "pitch_speed_mph": [80.0, 84.0, 90.0, 92.0],
            "elbow_varus_moment": [70.0, np.nan, 100.0, 110.0],
            "max_shoulder_internal_rotational_velo": [4000.0, 4200.0, 4600.0, 4700.0],
            "max_rotation_hip_shoulder_separation": [30.0, 35.0, 40.0, 45.0],
            "max_torso_rotational_velo": [700.0, 750.0, 800.0, 850.0],
        },
        index=[7, 7, 99, 99],
    )


def test_pair_plot_preserves_pitch_identity_and_drops_only_incomplete_pairs(recorded):
    before = recorded.copy(deep=True)
    plotted = prepare_scatter_data(recorded, "pitch_speed_mph", "elbow_varus_moment")
    assert plotted.session_pitch.tolist() == ["test-a1", "test-b1", "test-b2"]
    assert plotted.pitch_speed_mph.tolist() == [80, 90, 92]
    assert plotted.elbow_varus_moment.tolist() == [70, 100, 110]
    pd.testing.assert_frame_equal(recorded, before)


def test_same_axis_and_nonfinite_values_never_duplicate_columns_or_fill_values(recorded):
    recorded.loc[recorded.session_pitch.eq("test-a1"), "pitch_speed_mph"] = np.inf
    result = prepare_scatter_data(recorded, "pitch_speed_mph", "pitch_speed_mph")
    assert not result.columns.duplicated().any()
    assert result.session_pitch.tolist() == ["test-a2", "test-b1", "test-b2"]
    assert pd.isna(result.loc[result.session_pitch.eq("test-a2"), "elbow_varus_moment"]).all()


def test_athlete_means_use_the_same_complete_pitches_for_both_axes(recorded):
    means = prepare_scatter_data(
        recorded, "pitch_speed_mph", "elbow_varus_moment", athlete_means=True
    ).set_index("user")
    assert "session_pitch" not in means
    assert means.loc["test-athlete-a", "pitch_speed_mph"] == 80
    assert means.loc["test-athlete-a", "n_pitches"] == 1
    assert means.loc["test-athlete-b", "pitch_speed_mph"] == 91
    assert means.loc["test-athlete-b", "elbow_varus_moment"] == 105
    assert means.loc["test-athlete-b", "n_pitches"] == 2


@pytest.mark.parametrize("means", [False, True])
def test_all_missing_pairs_are_an_empty_chart_not_invented_zeros(recorded, means):
    recorded["elbow_varus_moment"] = np.nan
    plotted = prepare_scatter_data(
        recorded, "pitch_speed_mph", "elbow_varus_moment", athlete_means=means
    )
    assert plotted.empty


def test_unknown_measure_and_duplicate_pitch_identity_are_rejected(recorded):
    with pytest.raises(ValueError, match="five declared"):
        prepare_scatter_data(recorded, "age_yrs", "elbow_varus_moment")
    with pytest.raises(ValueError, match="appear once"):
        prepare_scatter_data(
            pd.concat([recorded, recorded.iloc[[0]]]), "pitch_speed_mph", "elbow_varus_moment"
        )


def test_two_pitch_comparison_preserves_missing_values_and_difference_direction(recorded):
    compared = compare_recorded_pitches(recorded, "test-a1", "test-b1").set_index("measure")
    assert compared.loc["Pitch speed", "difference_b_minus_a"] == 10
    assert compared.loc["Elbow varus moment", "difference_b_minus_a"] == 30
    missing = compare_recorded_pitches(recorded, "test-a2", "test-b1").set_index("measure")
    assert pd.isna(missing.loc["Elbow varus moment", "pitch_a"])
    assert pd.isna(missing.loc["Elbow varus moment", "difference_b_minus_a"])
    with pytest.raises(ValueError, match="must exist"):
        compare_recorded_pitches(recorded, "unknown", "test-b1")


def test_event_selection_names_one_valid_pitch_and_never_uses_row_indexes():
    valid = ["test-a1", "test-b1"]
    assert (
        selected_pitch_from_event(
            {"selection": {"pitch_pick": [{"session_pitch": "test-b1"}]}}, valid
        )
        == "test-b1"
    )
    assert (
        selected_pitch_from_event(
            {"selection": {"pitch_pick": {"session_pitch": ["test-a1"]}}}, valid
        )
        == "test-a1"
    )
    for event in (
        None,
        {"selection": []},
        {"selection": {"pitch_pick": [{"_vgsid_": 1}]}},
        {"selection": {"pitch_pick": [{"session_pitch": "../../unknown"}]}},
        {"selection": {"pitch_pick": [{"session_pitch": 1}]}},
        {"selection": {"pitch_pick": [{"session_pitch": "test-a1"}, {"session_pitch": "test-b1"}]}},
    ):
        assert selected_pitch_from_event(event, valid) is None


def test_chart_selection_exists_for_individual_pitches_only(recorded):
    first = prepare_scatter_data(recorded, "pitch_speed_mph", "elbow_varus_moment")
    spec = build_scatter_chart(first, "pitch_speed_mph", "elbow_varus_moment").to_dict()
    assert next(item for item in spec["params"] if item["name"] == "pitch_pick")["select"][
        "fields"
    ] == ["session_pitch"]
    assert spec["encoding"]["x"]["title"] == "Pitch speed (mph)"
    highlighted = build_scatter_chart(
        first, "pitch_speed_mph", "elbow_varus_moment", selected_pitch_id="test-b1"
    ).to_dict()
    assert next(item for item in highlighted["params"] if item["name"] == "pitch_pick")[
        "value"
    ] == [{"session_pitch": "test-b1"}]
    means = prepare_scatter_data(
        recorded, "pitch_speed_mph", "elbow_varus_moment", athlete_means=True
    )
    mean_spec = build_scatter_chart(
        means, "pitch_speed_mph", "elbow_varus_moment", athlete_means=True
    ).to_dict()
    assert "pitch_pick" not in [item["name"] for item in mean_spec["params"]]
    assert "session_pitch" not in json.dumps(mean_spec["encoding"])


def test_download_keeps_recorded_ids_missingness_and_source_terms(recorded):
    exported = pd.read_csv(io.BytesIO(recorded_pitch_export(recorded)))
    assert exported.session_pitch.tolist() == recorded.session_pitch.tolist()
    assert exported.user.tolist() == recorded.user.tolist()
    assert pd.isna(exported.loc[1, "elbow_varus_moment"])
    assert exported.source_commit.eq(SOURCE_COMMIT).all()
    assert exported.data_terms.eq(DATA_TERMS).all()


def _app(tmp_path: Path, frame: pd.DataFrame, extra: str = "") -> AppTest:
    """Render only the owned component with explicitly synthetic source records."""
    script = tmp_path / "explorer_app.py"
    script.write_text(
        "import io\nimport pandas as pd\nimport streamlit as st\n"
        "from pitching.pitch_explorer import render_pitch_explorer\n"
        f"frame = pd.read_json(io.StringIO({frame.to_json(orient='split')!r}), orient='split')\n"
        + extra
        + "selected = render_pitch_explorer(frame, full_frame=frame)\n"
        + "st.caption(f'Synthetic selected ID: {selected}')\n",
        encoding="utf-8",
    )
    return AppTest.from_file(str(script), default_timeout=25)


def test_ui_selects_recorded_pitch_and_switches_to_athlete_means(recorded, tmp_path):
    app = _app(tmp_path, recorded).run()
    assert not app.exception, [item.value for item in app.exception]
    assert {item.label: item.value for item in app.metric}["Pitches in this view"] == "4"
    app.selectbox(key="explorer_pitch").select("test-b1").run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("Synthetic selected ID: test-b1" in item.value for item in app.caption)
    assert {item.label: item.value for item in app.metric}["Pitch speed (mph)"] == "90.0"
    app.radio(key="explorer_unit").set_value("One athlete's average").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="explorer_pitch").value == "test-b1"
    assert any("An average is not a single recorded pitch" in item.value for item in app.caption)
    app.selectbox(key="explorer_x").select("elbow_varus_moment").run()
    assert not app.exception, [item.value for item in app.exception]


def test_ui_filtering_clears_an_unavailable_pitch_selection(recorded, tmp_path):
    app = _app(
        tmp_path,
        recorded,
        "if st.checkbox('Synthetic subset', key='test_subset'):\n"
        "    frame = frame[frame.user.eq('test-athlete-a')]\n",
    ).run()
    app.selectbox(key="explorer_pitch").select("test-b1").run()
    app.checkbox(key="test_subset").set_value(True).run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="explorer_pitch").value == "test-a1"
    assert app.selectbox(key="explorer_compare_b").value in {"test-a1", "test-a2"}


def test_ui_empty_view_is_graceful_without_an_invented_pitch(recorded, tmp_path):
    app = _app(tmp_path, recorded.iloc[:0]).run()
    assert not app.exception
    assert any("No recorded pitches match" in item.value for item in app.info)
    assert not list(app.selectbox)


def test_ui_missing_pair_shows_no_chart_but_keeps_observed_pitch_card(recorded, tmp_path):
    recorded["elbow_varus_moment"] = np.nan
    app = _app(tmp_path, recorded).run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("No pitches have both selected" in item.value for item in app.info)
    assert {item.label: item.value for item in app.metric}[
        "Elbow varus moment (N·m)"
    ] == "Not observed"


def test_parent_persisting_returned_pitch_does_not_override_a_new_dropdown(recorded, tmp_path):
    script = tmp_path / "roundtrip.py"
    script.write_text(
        "import io\nimport pandas as pd\nimport streamlit as st\n"
        "from pitching.pitch_explorer import render_pitch_explorer\n"
        f"frame = pd.read_json(io.StringIO({recorded.to_json(orient='split')!r}), orient='split')\n"
        "if st.button('Synthetic external selection', key='external'):\n"
        "    st.session_state['root_pitch'] = 'test-b2'\n"
        "result = render_pitch_explorer(frame, selected_pitch_id=st.session_state.get('root_pitch'))\n"
        "st.session_state['root_pitch'] = result\n",
        encoding="utf-8",
    )
    app = AppTest.from_file(str(script), default_timeout=25).run()
    assert not app.exception
    assert app.selectbox(key="explorer_pitch").value == "test-a1"
    app.selectbox(key="explorer_pitch").select("test-b1").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="explorer_pitch").value == "test-b1"
    assert app.session_state["root_pitch"] == "test-b1"
    app.selectbox(key="explorer_pitch").select("test-a2").run()
    assert app.selectbox(key="explorer_pitch").value == "test-a2"
    assert app.session_state["root_pitch"] == "test-a2"
    app.button(key="external").click().run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="explorer_pitch").value == "test-b2"
