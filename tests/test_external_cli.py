"""Synthetic TEST-ONLY end-to-end CLI inputs verify software, not external evidence."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from pitching.cli import main
from pitching.models import FEATURES, TARGETS
from pitching.new_data import CANONICAL_COLUMNS, DEFINITIONS, SIGNED_COLUMNS, UNITS


def synthetic_mapping():
    """A completed declaration for invented unit-test rows only."""
    return {
        "schema_version": 1,
        "dataset": {
            "name": "Synthetic TEST-ONLY CLI fixture",
            "population": "No observational cohort; invented test records",
            "collection_protocol": "Software test fixture; no measurements collected",
            "athlete_id_namespace": "synthetic-cli-tests",
            "rights": {"authorized": True, "basis": "Synthetic TEST-ONLY generated records"},
        },
        "columns": {
            name: {
                "source": name,
                "unit": UNITS[name],
                "definition": DEFINITIONS[name],
                "definition_confirmed": True,
                **(
                    {
                        "sign_convention": "Synthetic canonical sign for software testing only",
                        "canonical_sign_confirmed": True,
                    }
                    if name in SIGNED_COLUMNS
                    else {}
                ),
            }
            for name in CANONICAL_COLUMNS
        },
    }


def synthetic_protocol():
    return {
        "schema_version": 1,
        "study_id": "synthetic-cli-test-only",
        "research_question": "Verify public CLI integration; no scientific inference",
        "intended_external_population": "Invented test rows only",
        "evaluation_design": "independent_new_athletes",
        "prediction_context": "same_pitch_post_motion",
        "development_identity_namespace": "synthetic-cli-tests",
        "external_identity_namespace": "synthetic-cli-tests",
        "external_athletes_disjoint_attested": True,
        "external_outcomes_unseen_at_freeze_attested": True,
        "measurement_compatibility_reviewed": True,
    }


def synthetic_table(prefix, groups, offset=0):
    index = np.arange(len(groups), dtype=float)
    return pd.DataFrame(
        {
            "session_pitch": [f"{prefix}-pitch-{value:03d}" for value in range(len(groups))],
            "user": [f"{prefix}-athlete-{value:03d}" for value in groups],
            "session": [f"{prefix}-assessment-{value:03d}" for value in groups],
            "age_yrs": 18 + index / 4 + offset,
            "session_mass_kg": 70 + index + offset,
            "session_height_m": 1.7 + index / 100,
            "max_shoulder_internal_rotational_velo": 3500 + 7 * index**2 + offset,
            "max_rotation_hip_shoulder_separation": 20 + index / 2 + offset,
            "max_torso_rotational_velo": 800 + 13 * index + offset,
            "pitch_speed_mph": 75 + index + offset,
            "elbow_varus_moment": 70 + index**2 / 2 + offset,
        }
    )


def audit_arguments(csv, mapping, output):
    return [
        "new-data",
        "audit",
        "--csv",
        str(csv),
        "--mapping",
        str(mapping),
        "--output",
        str(output),
    ]


def directory_hashes(directory):
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir()
        if path.is_file()
    }


def test_real_cli_audit_freeze_audit_evaluate_preserves_private_boundaries(tmp_path, monkeypatch):
    """The exact documented command chain operates offline outside the source checkout."""
    monkeypatch.chdir(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Evaluation must neither access a network nor fit a model")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    studies = tmp_path / "local_studies"
    studies.mkdir()
    mapping = studies / "mapping.json"
    mapping.write_text(json.dumps(synthetic_mapping()))
    protocol = studies / "protocol.json"
    protocol.write_text(json.dumps(synthetic_protocol()))
    development = synthetic_table("development", [1] * 4 + [2] * 4 + [3] * 4)
    development.loc[0, FEATURES[0]] = np.nan
    development.loc[1, TARGETS[0]] = np.nan
    source = studies / "development.csv"
    development.to_csv(source, index=False)
    prepared_development = studies / "prepared-development"
    assert main(audit_arguments(source, mapping, prepared_development)) == 0
    bundle = studies / "frozen"
    assert (
        main(
            [
                "external",
                "freeze",
                "--prepared",
                str(prepared_development),
                "--protocol",
                str(protocol),
                "--output",
                str(bundle),
            ]
        )
        == 0
    )
    frozen_before = directory_hashes(bundle)
    # The evaluation input is created only after the development bundle exists.
    external = synthetic_table("external", [1, 1, 1, 2, 3, 3], offset=5)
    external.loc[0, TARGETS[0]] = np.nan
    external.loc[[1, 2], TARGETS[1]] = np.nan
    external.loc[3, FEATURES[1]] = np.nan
    external_source = studies / "external.csv"
    external.to_csv(external_source, index=False)
    prepared_external = studies / "prepared-external"
    assert main(audit_arguments(external_source, mapping, prepared_external)) == 0
    for location in (
        "sklearn.pipeline.Pipeline.fit",
        "sklearn.linear_model.Ridge.fit",
        "sklearn.dummy.DummyRegressor.fit",
        "sklearn.impute.SimpleImputer.fit",
        "sklearn.preprocessing.StandardScaler.fit",
    ):
        monkeypatch.setattr(location, forbidden)
    output = studies / "evaluation"
    evaluate = [
        "external",
        "evaluate",
        "--prepared",
        str(prepared_external),
        "--bundle",
        str(bundle),
        "--output",
        str(output),
    ]
    assert main(evaluate) == 0
    assert directory_hashes(bundle) == frozen_before
    metrics = pd.read_csv(output / "external_metrics.csv")
    predictions = pd.read_csv(output / "external_predictions.csv", dtype={"user": str})
    assert len(metrics) == 8  # Four fixed models × two outcomes.
    assert len(predictions) == 6 * 8  # Missing outcomes still receive predictions.
    assert metrics.n_prediction_rows.eq(6).all()
    assert metrics.n_athletes.eq(3).all()
    for target, missing, count in ((TARGETS[0], 1, 5), (TARGETS[1], 2, 4)):
        rows = metrics.loc[metrics.target.eq(target)]
        assert len(rows) == 4
        assert rows.n_missing_outcomes.eq(missing).all()
        assert rows.n_pitches.eq(count).all()
        for _, row in rows.iterrows():
            error_rows = predictions.loc[
                predictions.target.eq(target)
                & predictions.model.eq(row.model)
                & predictions.observed.notna()
            ]
            assert row.athlete_mae == pytest.approx(
                error_rows.groupby("user").absolute_error.mean().mean()
            )
    unobserved = predictions.loc[predictions.observed.isna()]
    assert np.isfinite(unobserved.predicted).all()
    assert unobserved.residual.isna().all()
    assert unobserved.absolute_error.isna().all()
    audit = json.loads((output / "evaluation_audit.json").read_text())
    assert audit["n_external_pitches"] == 6
    assert audit["n_external_athletes"] == 3
    assert audit["training_performed"] is False
    assert audit["target_imputation_performed"] is False
    assert audit["identity_check"]["known_shared_namespace_athlete_overlap"] == 0
    assert audit["external_dataset"]["name"] == "Synthetic TEST-ONLY CLI fixture"
    manifest = json.loads((output / "evaluation_manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "reports").exists()
    # A repeated batch command must fail without replacing the previous result.
    before = directory_hashes(output)
    assert main(evaluate) == 1
    assert directory_hashes(output) == before


def test_cli_audit_failure_and_existing_output_do_not_replace_files(tmp_path, capsys):
    mapping = synthetic_mapping()
    mapping["dataset"]["rights"]["authorized"] = False
    spec = tmp_path / "mapping.json"
    spec.write_text(json.dumps(mapping))
    source = tmp_path / "synthetic.csv"
    synthetic_table("development", [1, 1, 2, 2]).to_csv(source, index=False)
    output = tmp_path / "prepared"
    source_before = source.read_bytes()
    assert main(audit_arguments(source, spec, output)) == 1
    assert "rights attestation" in capsys.readouterr().err
    assert not output.exists()
    assert source.read_bytes() == source_before
    output.mkdir()
    sentinel = output / "private-existing.txt"
    sentinel.write_text("Preserve this explicitly synthetic test sentinel")
    mapping["dataset"]["rights"]["authorized"] = True
    spec.write_text(json.dumps(mapping))
    before = directory_hashes(output)
    assert main(audit_arguments(source, spec, output)) == 1
    assert directory_hashes(output) == before
    assert source.read_bytes() == source_before
