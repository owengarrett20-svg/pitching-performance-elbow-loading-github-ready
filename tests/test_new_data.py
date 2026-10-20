"""Explicitly synthetic fixtures exercise local schema preparation, never research results."""

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pitching.models import FEATURES, TARGETS
from pitching.new_data import (
    CANONICAL_COLUMNS,
    DEFINITIONS,
    SIGNED_COLUMNS,
    UNITS,
    NewDataValidationError,
    load_prepared_dataset,
    main,
    prepare_dataset,
    validate_mapping,
)


@pytest.fixture
def mapping():
    aliases = {"session_pitch": "pitch_id", "user": "athlete_id", "session": "session_id"}
    result = {
        "schema_version": 1,
        "dataset": {
            "name": "Explicitly synthetic adapter unit-test fixture",
            "population": "Invented records for software tests only",
            "collection_protocol": "No measurements collected; synthetic software fixture",
            "athlete_id_namespace": "synthetic-adapter-tests",
            "rights": {"authorized": True, "basis": "Invented test-only records"},
        },
        "columns": {},
    }
    for name in CANONICAL_COLUMNS:
        entry = {
            "source": aliases.get(name, name),
            "unit": UNITS[name],
            "definition": DEFINITIONS[name],
            "definition_confirmed": True,
        }
        if name in SIGNED_COLUMNS:
            entry.update(
                sign_convention="Synthetic fixture already uses the declared canonical sign",
                canonical_sign_confirmed=True,
            )
        result["columns"][name] = entry
    return result


@pytest.fixture
def observations():
    return pd.DataFrame(
        {
            "pitch_id": ["0001", "0002", "NA"],
            "athlete_id": ["001", "001", "1"],
            "session_id": ["session-A", "session-A", "session-B"],
            "age_yrs": [20.0, 20.0, 21.0],
            "session_mass_kg": [80.0, 80.0, 85.0],
            "session_height_m": [1.8, 1.8, 1.9],
            "max_shoulder_internal_rotational_velo": [4000.0, 4100.0, 4300.0],
            "max_rotation_hip_shoulder_separation": [25.0, 30.0, 35.0],
            "max_torso_rotational_velo": [900.0, 950.0, 1000.0],
            "pitch_speed_mph": [80.0, 81.0, 85.0],
            "elbow_varus_moment": [80.0, 82.0, 100.0],
            "unmapped_note": ["test fixture"] * 3,
        }
    )


def write_inputs(tmp_path, mapping, observations):
    source = tmp_path / "synthetic.csv"
    spec = tmp_path / "mapping.json"
    observations.to_csv(source, index=False)
    spec.write_text(json.dumps(mapping))
    return source, spec


def prepared(tmp_path, mapping, observations):
    source, spec = write_inputs(tmp_path, mapping, observations)
    output = tmp_path / "prepared"
    result = prepare_dataset(source, spec, output)
    return output, result


def rewrite_bound_artifact(directory, name, payload):
    """A rehashed mutation tests semantic consistency beyond a simple checksum failure."""
    (directory / name).write_bytes(payload)
    path = directory / "provenance.json"
    provenance = json.loads(path.read_text())
    provenance["artifacts_sha256"][name] = hashlib.sha256(payload).hexdigest()
    path.write_text(json.dumps(provenance))


def test_roundtrip_preserves_identifier_strings_and_reports_only_observed_rows(
    tmp_path, mapping, observations, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preparation must not fit a model or access a network")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("sklearn.linear_model.Ridge.fit", forbidden)
    output, provenance = prepared(tmp_path, mapping, observations)
    table, loaded = load_prepared_dataset(output)
    assert list(table) == list(CANONICAL_COLUMNS)
    assert table.session_pitch.tolist() == ["0001", "0002", "NA"]
    assert table.user.tolist() == ["001", "001", "1"]
    assert len(table) == 3
    assert table.user.nunique() == 2
    assert loaded == provenance
    assert provenance["analysis_status"].startswith("Prepared input only")
    audit = json.loads((output / "audit.json").read_text())
    assert audit["unmapped_source_column_count"] == 1
    assert audit["n_pitches"] == 3 and audit["n_athletes"] == 2
    assert not any(item["sign_changed"] for item in audit["conversions"])


@pytest.mark.parametrize(
    ("name", "unit", "value", "expected"),
    [
        ("session_mass_kg", "lb", 200, 90.718474),
        ("session_height_m", "cm", 185, 1.85),
        ("max_shoulder_internal_rotational_velo", "rad/s", np.pi, 180),
        ("max_torso_rotational_velo", "rad/s", np.pi / 2, 90),
        ("max_rotation_hip_shoulder_separation", "rad", np.pi / 6, 30),
        ("pitch_speed_mph", "m/s", 40, 89.4774516821761),
    ],
)
def test_only_documented_equivalent_units_are_converted(
    tmp_path, mapping, observations, name, unit, value, expected
):
    mapping["columns"][name]["unit"] = unit
    observations[name] = value
    output, _ = prepared(tmp_path, mapping, observations)
    table, _ = load_prepared_dataset(output)
    np.testing.assert_allclose(table[name], expected, rtol=1e-12)
    audit = json.loads((output / "audit.json").read_text())
    conversion = next(item for item in audit["conversions"] if item["column"] == name)
    assert conversion["input_unit"] == unit
    assert conversion["canonical_unit"] == UNITS[name]


def test_missing_tokens_remain_missing_and_targets_are_never_filled(
    tmp_path, mapping, observations
):
    observations["pitch_speed_mph"] = ["", "N/A", "null"]
    observations["elbow_varus_moment"] = ["NaN", "none", "80"]
    observations[FEATURES[-1]] = ["NA", "", "1000"]
    output, _ = prepared(tmp_path, mapping, observations)
    table, _ = load_prepared_dataset(output)
    assert table.pitch_speed_mph.isna().all()
    assert table.elbow_varus_moment.isna().sum() == 2
    assert table[FEATURES[-1]].isna().sum() == 2
    assert table.session_pitch.iloc[2] == "NA"
    audit = json.loads((output / "audit.json").read_text())
    assert audit["missing_target_rows"] == {"pitch_speed_mph": 3, "elbow_varus_moment": 2}


@pytest.mark.parametrize(
    "edit",
    [
        lambda mapping: mapping["dataset"]["rights"].update(authorized=False),
        lambda mapping: mapping["dataset"]["rights"].update(basis=""),
        lambda mapping: mapping["dataset"].update(collection_protocol="EDIT_protocol"),
        lambda mapping: mapping["dataset"].update(athlete_id_namespace=" synthetic "),
        lambda mapping: mapping["columns"][FEATURES[3]].update(definition_confirmed=False),
        lambda mapping: mapping["columns"][FEATURES[3]].update(canonical_sign_confirmed=False),
        lambda mapping: mapping["columns"][TARGETS[1]].update(definition="external_valgus_moment"),
        lambda mapping: mapping["columns"][FEATURES[4]].update(definition="foot_plant_angle"),
        lambda mapping: mapping["columns"][TARGETS[1]].update(unit="ft*lb"),
        lambda mapping: mapping["columns"][FEATURES[0]].update(source="pitch_speed_mph"),
        lambda mapping: mapping.update(schema_version=True),
    ],
)
def test_unreviewed_or_semantically_incompatible_mapping_is_rejected(mapping, edit):
    edit(mapping)
    with pytest.raises(NewDataValidationError):
        validate_mapping(mapping)


@pytest.mark.parametrize(
    ("column", "values", "message"),
    [
        ("pitch_id", ["duplicate", "duplicate", "other"], "one row per pitch"),
        ("pitch_id", ["", "0002", "NA"], "missing or empty"),
        ("athlete_id", ["001 ", "001", "1"], "untrimmed"),
        ("session_id", ["shared", "shared", "shared"], "one athlete"),
        ("pitch_speed_mph", [80, "bad", 85], "invalid numeric"),
        ("pitch_speed_mph", [80, "inf", 85], "nonfinite"),
        ("pitch_speed_mph", [80, 0, 85], "positive"),
        ("session_mass_kg", [80, -1, 85], "positive"),
        ("age_yrs", [20, -1, 21], "negative"),
    ],
)
def test_invalid_rows_stop_preparation_without_creating_output(
    tmp_path, mapping, observations, column, values, message
):
    observations[column] = values
    source, spec = write_inputs(tmp_path, mapping, observations)
    with pytest.raises(NewDataValidationError, match=message):
        prepare_dataset(source, spec, tmp_path / "prepared")
    assert not (tmp_path / "prepared").exists()


def test_conversion_overflow_is_rejected(tmp_path, mapping, observations):
    mapping["columns"][FEATURES[3]]["unit"] = "rad/s"
    observations[FEATURES[3]] = 1e308
    source, spec = write_inputs(tmp_path, mapping, observations)
    with pytest.raises(NewDataValidationError, match="overflow"):
        prepare_dataset(source, spec, tmp_path / "prepared")


@pytest.mark.parametrize("source", ["a,a\n1,2\n", "a,b\n1,2,3\n", "a,b\n"])
def test_malformed_or_empty_csv_is_rejected(tmp_path, mapping, source):
    data, spec = write_inputs(tmp_path, mapping, pd.DataFrame())
    data.write_text(source)
    with pytest.raises(NewDataValidationError):
        prepare_dataset(data, spec, tmp_path / "prepared")


def test_json_duplicate_keys_and_nonfinite_constants_are_rejected(tmp_path, mapping, observations):
    data, spec = write_inputs(tmp_path, mapping, observations)
    for text in ['{"schema_version":1,"schema_version":2}', '{"value":NaN}']:
        spec.write_text(text)
        with pytest.raises(NewDataValidationError):
            prepare_dataset(data, spec, tmp_path / "prepared")


def test_existing_outputs_and_input_collisions_are_preserved(tmp_path, mapping, observations):
    source, spec = write_inputs(tmp_path, mapping, observations)
    source_before = source.read_bytes()
    existing = tmp_path / "existing"
    existing.mkdir()
    for output in [existing, source, spec, source.parent]:
        with pytest.raises(NewDataValidationError, match="already exists"):
            prepare_dataset(source, spec, output)
    assert source.read_bytes() == source_before
    assert not list(existing.iterdir())


def test_partial_write_failure_removes_only_new_output(
    tmp_path, mapping, observations, monkeypatch
):
    source, spec = write_inputs(tmp_path, mapping, observations)
    original = Path.write_bytes

    def fail_audit(path, contents):
        if path.name == "audit.json":
            raise OSError("Explicit synthetic write failure")
        return original(path, contents)

    monkeypatch.setattr(Path, "write_bytes", fail_audit)
    with pytest.raises(OSError, match="synthetic write failure"):
        prepare_dataset(source, spec, tmp_path / "prepared")
    assert not (tmp_path / "prepared").exists()
    assert source.is_file() and spec.is_file()


def test_changed_artifact_or_missing_manifest_entry_is_rejected(tmp_path, mapping, observations):
    output, _ = prepared(tmp_path, mapping, observations)
    canonical = output / "canonical.csv"
    canonical.write_bytes(canonical.read_bytes() + b"\n")
    with pytest.raises(NewDataValidationError, match="checksum mismatch"):
        load_prepared_dataset(output)
    provenance = json.loads((output / "provenance.json").read_text())
    del provenance["artifacts_sha256"]["canonical.csv"]
    (output / "provenance.json").write_text(json.dumps(provenance))
    with pytest.raises(NewDataValidationError, match="incomplete"):
        load_prepared_dataset(output)


@pytest.mark.parametrize("change", ["count", "missingness", "conversions", "status"])
def test_rehashed_audit_still_has_to_agree_with_canonical_data(
    tmp_path, mapping, observations, change
):
    output, _ = prepared(tmp_path, mapping, observations)
    audit = json.loads((output / "audit.json").read_text())
    if change == "count":
        audit["n_pitches"] = 999
    elif change == "missingness":
        audit["missing_target_rows"]["pitch_speed_mph"] = 999
    elif change == "conversions":
        audit["conversions"][0]["multiplier"] = 2
    else:
        audit["status"] = "unfinished"
    rewrite_bound_artifact(output, "audit.json", json.dumps(audit).encode())
    with pytest.raises(NewDataValidationError):
        load_prepared_dataset(output)


def test_rehashed_missingness_report_still_has_to_agree(tmp_path, mapping, observations):
    output, _ = prepared(tmp_path, mapping, observations)
    rewrite_bound_artifact(output, "missingness.csv", b"invented,missingness\n")
    with pytest.raises(NewDataValidationError, match="missingness report"):
        load_prepared_dataset(output)


def test_bad_digest_and_dataset_metadata_mismatch_are_rejected(tmp_path, mapping, observations):
    output, _ = prepared(tmp_path, mapping, observations)
    path = output / "provenance.json"
    original = json.loads(path.read_text())
    bad = copy.deepcopy(original)
    bad["source_csv_sha256"] = "not a checksum"
    path.write_text(json.dumps(bad))
    with pytest.raises(NewDataValidationError, match="SHA-256"):
        load_prepared_dataset(output)
    bad = copy.deepcopy(original)
    bad["dataset"]["athlete_id_namespace"] = "different-namespace"
    path.write_text(json.dumps(bad))
    with pytest.raises(NewDataValidationError, match="provenance differs"):
        load_prepared_dataset(output)


def test_cli_returns_failure_without_creating_results_for_unreviewed_template(
    tmp_path, mapping, observations, capsys
):
    mapping["dataset"]["rights"]["authorized"] = False
    source, spec = write_inputs(tmp_path, mapping, observations)
    code = main(
        ["audit", "--csv", str(source), "--mapping", str(spec), "--output", str(tmp_path / "out")]
    )
    assert code == 1
    assert "rights attestation" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
