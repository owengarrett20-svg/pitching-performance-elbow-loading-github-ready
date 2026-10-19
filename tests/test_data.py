"""Synthetic unit fixtures exercise failures; real data are separate checks."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pitching.data import (
    COMMIT,
    REPOSITORY,
    VARIABLES,
    DataValidationError,
    audit_dataset,
    fetch_source,
    join_pitching,
    missingness_table,
    verify_source,
)


@pytest.fixture
def tables():
    # Deliberately synthetic: never used as a substitute for OBP observations.
    poi = pd.DataFrame(
        {
            "session_pitch": ["s1_1", "s1_2", "s2_1"],
            "session": ["s1", "s1", "s2"],
            "p_throws": ["R", "R", "L"],
            "pitch_type": ["FF"] * 3,
            **{name: [1.0, 2.0, 3.0] for name in VARIABLES},
        }
    )
    metadata = pd.DataFrame(
        {
            "session_pitch": poi.session_pitch,
            "session": poi.session,
            "user": ["a1", "a1", "a2"],
            "pitch_speed_mph": poi.pitch_speed_mph,
            "session_mass_kg": [90.0] * 3,
            "session_height_m": [1.8] * 3,
            "age_yrs": [20.0] * 3,
            "playing_level": ["college"] * 3,
            "filename_new": ["synthetic"] * 3,
            "modelname_new": ["synthetic"] * 3,
        }
    )
    return poi, metadata


def test_one_to_one_join_preserves_pitches(tables):
    poi, metadata = tables
    joined, audit = join_pitching(poi, metadata.sample(frac=1, random_state=9))
    assert len(joined) == len(poi)
    assert audit["cardinality"] == "one_to_one" and audit["status"] == "passed"
    assert joined.groupby("user").size().to_dict() == {"a1": 2, "a2": 1}
    assert "pitch_speed_mph_metadata" not in joined


@pytest.mark.parametrize("side", [0, 1])
def test_duplicate_pitch_rejected_before_row_multiplication(tables, side):
    modified = list(tables)
    modified[side] = pd.concat([modified[side], modified[side].iloc[[0]]])
    with pytest.raises(DataValidationError, match="unique") as error:
        join_pitching(*modified)
    key = "poi" if side == 0 else "metadata"
    assert error.value.report[key]["duplicate_key_rows"] == 2


@pytest.mark.parametrize("column", ["session_pitch", "user"])
def test_missing_identifier_rejected(tables, column):
    poi, metadata = tables
    metadata.loc[0, column] = None
    with pytest.raises(DataValidationError):
        join_pitching(poi, metadata)


def test_unmatched_pitch_is_reported(tables):
    poi, metadata = tables
    with pytest.raises(DataValidationError, match="coverage") as error:
        join_pitching(poi, metadata.iloc[1:])
    assert error.value.report["poi_only_keys"] == ["s1_1"]


@pytest.mark.parametrize("column", ["session", "pitch_speed_mph"])
def test_conflicting_redundant_fields_fail(tables, column):
    poi, metadata = tables
    metadata.loc[0, column] = "other" if column == "session" else 99.0
    with pytest.raises(DataValidationError, match="disagree|differs"):
        join_pitching(poi, metadata)


def test_missing_target_not_filled_from_metadata(tables):
    poi, metadata = tables
    poi.loc[0, "pitch_speed_mph"] = np.nan
    joined, audit = join_pitching(poi, metadata)
    assert pd.isna(joined.loc[0, "pitch_speed_mph"])
    assert audit["duplicate_speed_missing_pairs"] == 1


def test_invalid_numeric_measurement_is_not_silently_coerced(tables):
    poi, metadata = tables
    poi["elbow_varus_moment"] = ["not measured", "2", "3"]
    with pytest.raises(DataValidationError, match="numeric"):
        join_pitching(poi, metadata)


def test_session_cannot_map_to_multiple_athletes(tables):
    poi, metadata = tables
    metadata.loc[1, "user"] = "another-athlete"
    with pytest.raises(DataValidationError, match="multiple athletes"):
        join_pitching(poi, metadata)


def test_missingness_reports_empty_and_nonfinite_without_modification():
    frame = pd.DataFrame({"a": [1.0, np.nan, np.inf], "b": ["x", "", None]})
    before = frame.copy(deep=True)
    report = missingness_table(frame, "synthetic").set_index("column")
    assert report.loc["a", "n_missing"] == 1
    assert report.loc["a", "n_infinite"] == 1
    assert report.loc["b", "n_missing"] == 2
    assert report.loc["b", "pct_missing"] == pytest.approx(200 / 3)
    pd.testing.assert_frame_equal(frame, before)


def _manifest(tmp_path, content):
    manifest = {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "files": [
            {
                "path": "fixture.csv",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_download_is_pinned_verified_and_cached_without_network_on_repeat(tmp_path, monkeypatch):
    contents = b"synthetic_test_fixture\n1\n"
    manifest = _manifest(tmp_path, contents)
    calls = []

    def fake_request(url, timeout):
        calls.append(url)
        assert timeout > 0
        return io.BytesIO(contents)

    monkeypatch.setattr("pitching.data.urlopen", fake_request)
    cache = tmp_path / "cache"
    fetch_source(manifest, cache)
    fetch_source(manifest, cache)
    assert len(calls) == 1
    assert COMMIT in calls[0]
    assert verify_source(manifest, cache)["verified_files"] == 1


def test_checksum_mismatch_never_written_or_overwrites_local_edits(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, b"expected")
    monkeypatch.setattr("pitching.data.urlopen", lambda *a, **k: io.BytesIO(b"corrupt"))
    cache = tmp_path / "cache"
    with pytest.raises(DataValidationError, match="Checksum"):
        fetch_source(manifest, cache)
    assert not (cache / "fixture.csv").exists()
    cache.mkdir(exist_ok=True)
    (cache / "fixture.csv").write_bytes(b"local edits")
    with pytest.raises(DataValidationError, match="Checksum"):
        fetch_source(manifest, cache)
    assert (cache / "fixture.csv").read_bytes() == b"local edits"


@pytest.mark.integration
def test_official_pinned_dataset_join_and_missingness():
    root = Path(__file__).resolve().parents[1]
    cache = root / "data/raw"
    if not (cache / "baseball_pitching/data/poi/poi_metrics.csv").is_file():
        pytest.skip("Run `uv run pitching fetch` for the real-data integration check.")
    verify_source(root / "source_manifest.json", cache)
    data, audit, missingness = audit_dataset(cache)
    assert len(data) == 411 and data.user.nunique() == 100
    assert audit["duplicate_speed_conflicts"] == 0
    requested = missingness[missingness.table.eq("analysis") & missingness.column.isin(VARIABLES)]
    assert requested.n_missing.sum() == 0
    assert set(data.pitch_type) == {"FF"}
