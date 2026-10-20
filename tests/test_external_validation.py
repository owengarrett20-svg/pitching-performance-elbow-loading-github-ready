"""Synthetic TEST-ONLY cohorts exercise a workflow, never provide research evidence."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pitching.external_validation import (
    evaluate_external,
    freeze_models,
    load_frozen_bundle,
    main,
    predict_frozen,
)
from pitching.models import FEATURES, RIDGE_ALPHA, TARGETS
from pitching.new_data import CANONICAL_COLUMNS, DEFINITIONS, SIGNED_COLUMNS, UNITS, prepare_dataset
from pitching.phase2 import FEATURE_SETS


def synthetic_cohort(prefix="development", offset=0.0):
    """Invented measurements for unit tests only; no observational claim."""
    index = np.arange(8, dtype=float)
    return pd.DataFrame(
        {
            "session_pitch": [f"{prefix}-p{i}" for i in range(8)],
            "user": [f"{prefix}-a{i}" for i in [0, 0, 0, 1, 2, 2, 2, 2]],
            "session": [f"{prefix}-s{i}" for i in [0, 0, 0, 1, 2, 2, 2, 2]],
            "age_yrs": 19 + index * 0.5 + offset,
            "session_mass_kg": 75 + index * 2 + offset,
            "session_height_m": 1.7 + index * 0.015 + offset * 0.001,
            "max_shoulder_internal_rotational_velo": 3500 + index**2 * 9 + offset,
            "max_rotation_hip_shoulder_separation": 20 + index * 1.3 + offset,
            "max_torso_rotational_velo": 800 + index * 23 + offset,
            "pitch_speed_mph": 78 + index * 1.2 + offset * 0.1,
            "elbow_varus_moment": 70 + index**2 * 0.8 + offset * 0.1,
        }
    )


def synthetic_mapping(namespace):
    return {
        "schema_version": 1,
        "dataset": {
            "name": "Invented TEST ONLY table",
            "population": "No real athletes; software-test fixture",
            "collection_protocol": "Invented numeric values solely for automated tests",
            "athlete_id_namespace": namespace,
            "rights": {"authorized": True, "basis": "Invented test fixture; no observational data"},
        },
        "columns": {
            name: {
                "source": name,
                "unit": UNITS[name],
                "definition": DEFINITIONS[name],
                "definition_confirmed": True,
                **(
                    {
                        "sign_convention": "Synthetic canonical sign, TEST ONLY",
                        "canonical_sign_confirmed": True,
                    }
                    if name in SIGNED_COLUMNS
                    else {}
                ),
            }
            for name in CANONICAL_COLUMNS
        },
    }


def synthetic_protocol(development_namespace="test-shared", external_namespace="test-shared"):
    return {
        "schema_version": 1,
        "study_id": "synthetic-test-only",
        "research_question": "Software verification, not a biomechanics finding",
        "intended_external_population": "Invented test rows only",
        "evaluation_design": "independent_new_athletes",
        "prediction_context": "same_pitch_post_motion",
        "development_identity_namespace": development_namespace,
        "external_identity_namespace": external_namespace,
        "external_athletes_disjoint_attested": True,
        "external_outcomes_unseen_at_freeze_attested": True,
        "measurement_compatibility_reviewed": True,
    }


def prepare(tmp_path, frame, label, namespace="test-shared"):
    csv_path = tmp_path / f"{label}.csv"
    mapping_path = tmp_path / f"{label}-mapping.json"
    frame.to_csv(csv_path, index=False)
    mapping_path.write_text(json.dumps(synthetic_mapping(namespace)))
    prepared = tmp_path / label
    prepare_dataset(csv_path, mapping_path, prepared)
    return prepared


def freeze(tmp_path, frame=None, protocol=None):
    frame = synthetic_cohort() if frame is None else frame
    protocol = synthetic_protocol() if protocol is None else protocol
    prepared = prepare(tmp_path, frame, "development", protocol["development_identity_namespace"])
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol))
    bundle = tmp_path / "frozen"
    freeze_models(prepared, protocol_path, bundle)
    return bundle


def rewrite_bundle_file(bundle, name, value):
    """Rehash a changed component to exercise semantic, not just checksum, checks."""
    payload = json.dumps(value).encode()
    (bundle / name).write_bytes(payload)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][name] = hashlib.sha256(payload).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


@pytest.mark.parametrize("all_missing_feature", [False, True])
def test_numerical_bundle_matches_training_only_sklearn_preprocessing(
    tmp_path, all_missing_feature
):
    development = synthetic_cohort()
    development.loc[[0, 4], FEATURES[0]] = np.nan
    development.loc[1, TARGETS[0]] = np.nan
    if all_missing_feature:
        development[FEATURES[2]] = np.nan
    external = synthetic_cohort("external", 3.0)
    # A newly missing column gets the training statistic but no new indicator.
    external.loc[0, FEATURES[1]] = np.nan
    external.loc[3, FEATURES[0]] = np.nan
    bundle = freeze(tmp_path, development)
    models, _, metadata, _ = load_frozen_bundle(bundle)
    actual = predict_frozen(models, external[list(FEATURES)])
    for target in TARGETS:
        valid = development[target].notna()
        assert metadata["training_summary"][target]["n_observed_pitches"] == int(valid.sum())
        for name, allowed in FEATURE_SETS.items():
            if name == "dummy_mean":
                expected = np.repeat(development.loc[valid, target].mean(), len(external))
            else:
                reference = Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median", add_indicator=True, keep_empty_features=True
                            ),
                        ),
                        ("scaler", StandardScaler()),
                        ("regressor", Ridge(alpha=RIDGE_ALPHA)),
                    ]
                ).fit(development.loc[valid, list(allowed)], development.loc[valid, target])
                expected = reference.predict(external[list(allowed)])
            np.testing.assert_allclose(actual[target, name], expected, rtol=1e-12, atol=1e-10)


def test_external_evaluation_never_fits_and_missing_targets_do_not_change_predictions(
    tmp_path, monkeypatch
):
    bundle = freeze(tmp_path)
    external = synthetic_cohort("external", 2)
    external.loc[[0, 1, 2], TARGETS[0]] = np.nan
    external[TARGETS[1]] = np.nan
    prepared = prepare(tmp_path, external, "external")

    def forbidden(*args, **kwargs):
        raise AssertionError("Evaluation cannot fit or learn from external rows")

    for cls in [Pipeline, Ridge, DummyRegressor, SimpleImputer, StandardScaler]:
        monkeypatch.setattr(cls, "fit", forbidden)
    output = tmp_path / "evaluation"
    manifest = evaluate_external(prepared, bundle, output)
    predictions = pd.read_csv(output / "external_predictions.csv")
    metrics = pd.read_csv(output / "external_metrics.csv")
    assert len(predictions) == len(external) * len(TARGETS) * len(FEATURE_SETS)
    assert predictions.predicted.notna().all()
    missing = metrics.loc[metrics.target.eq(TARGETS[1])]
    assert missing.status.eq("no_observed_outcomes").all()
    assert missing.n_pitches.eq(0).all()
    assert missing.mae.isna().all() and missing.r2.isna().all()
    observed = metrics.loc[metrics.target.eq(TARGETS[0])]
    assert observed.n_pitches.eq(5).all()
    assert observed.n_athletes.eq(2).all()
    audit = json.loads((output / "evaluation_audit.json").read_bytes())
    assert audit["training_performed"] is False and audit["target_imputation_performed"] is False
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    models, _, _, _ = load_frozen_bundle(bundle)
    before = predict_frozen(models, external)
    external[list(TARGETS)] = 123456.0
    after = predict_frozen(models, external)
    for key in before:
        np.testing.assert_array_equal(before[key], after[key])


def test_primary_error_weights_athletes_equally_and_shift_uses_training_ranges(tmp_path):
    bundle = freeze(tmp_path)
    external = synthetic_cohort("external", 2)
    external[FEATURES[0]] = 99.0  # Explicit synthetic distribution shift.
    external[TARGETS[0]] = [200, 200, 200, 80, 80, 80, 80, 80]
    prepared = prepare(tmp_path, external, "external")
    output = tmp_path / "evaluation"
    evaluate_external(prepared, bundle, output)
    predictions = pd.read_csv(output / "external_predictions.csv")
    metrics = pd.read_csv(output / "external_metrics.csv")
    for target in TARGETS:
        for name in FEATURE_SETS:
            selected = predictions.loc[predictions.target.eq(target) & predictions.model.eq(name)]
            metric = metrics.loc[metrics.target.eq(target) & metrics.model.eq(name)].iloc[0]
            assert metric.athlete_mae == pytest.approx(
                selected.groupby("user").absolute_error.mean().mean()
            )
            assert metric.mae == pytest.approx(selected.absolute_error.mean())
    row = metrics.loc[metrics.target.eq(TARGETS[0]) & metrics.model.eq("dummy_mean")].iloc[0]
    assert row.athlete_mae != pytest.approx(row.mae)
    shift = pd.read_csv(output / "covariate_shift.csv")
    assert (
        shift.loc[shift.feature.eq(FEATURES[0]), "external_n_outside_development_range"].eq(8).all()
    )


@pytest.mark.parametrize("collision", ["athlete", "pitch", "complete_measurements"])
def test_detectable_development_reuse_is_rejected(tmp_path, collision):
    bundle = freeze(tmp_path)
    external = synthetic_cohort("external", 2)
    if collision == "athlete":
        external["user"] = [f"development-a{i}" for i in [0, 0, 0, 1, 2, 2, 2, 2]]
    elif collision == "pitch":
        external.loc[0, "session_pitch"] = "development-p0"
    else:
        external[list(FEATURES) + list(TARGETS)] = synthetic_cohort()[
            list(FEATURES) + list(TARGETS)
        ]
    prepared = prepare(tmp_path, external, "external")
    with pytest.raises(ValueError, match="overlap|reuse"):
        evaluate_external(prepared, bundle, tmp_path / "evaluation")
    assert not (tmp_path / "evaluation").exists()


def test_different_namespaces_are_attested_not_claimed_automatically_independent(tmp_path):
    bundle = freeze(
        tmp_path, protocol=synthetic_protocol("development-namespace", "external-namespace")
    )
    external = synthetic_cohort(
        "development", 2
    )  # Raw ID collisions across namespaces are possible.
    prepared = prepare(tmp_path, external, "external", "external-namespace")
    output = tmp_path / "evaluation"
    evaluate_external(prepared, bundle, output)
    audit = json.loads((output / "evaluation_audit.json").read_bytes())
    assert audit["identity_check"]["same_namespace"] is False
    assert audit["identity_check"]["known_shared_namespace_athlete_overlap"] is None
    assert any("cannot establish" in warning for warning in audit["warnings"])


@pytest.mark.parametrize(
    "field",
    [
        "external_athletes_disjoint_attested",
        "external_outcomes_unseen_at_freeze_attested",
        "measurement_compatibility_reviewed",
    ],
)
def test_uncompleted_attestations_do_not_produce_a_frozen_bundle(tmp_path, field):
    protocol = synthetic_protocol()
    protocol[field] = False
    with pytest.raises(ValueError, match="attest"):
        freeze(tmp_path, protocol=protocol)
    assert not (tmp_path / "frozen").exists()


def test_checksum_failure_and_duplicate_json_keys_fail_before_prediction(tmp_path):
    bundle = freeze(tmp_path)
    models_path = bundle / "models.json"
    models_path.write_bytes(models_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        load_frozen_bundle(bundle)
    manifest = bundle / "manifest.json"
    manifest.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        load_frozen_bundle(bundle)


@pytest.mark.parametrize(
    "fault",
    [
        "boolean_coefficient",
        "indicator_index",
        "negative_scale",
        "provenance_hash",
        "rights",
        "training_count",
        "range",
        "contract",
    ],
)
def test_rehashed_but_inconsistent_bundles_fail_semantic_checks(tmp_path, fault):
    bundle = freeze(tmp_path)
    if fault in {"boolean_coefficient", "indicator_index", "negative_scale"}:
        models = json.loads((bundle / "models.json").read_bytes())
        parameters = models[TARGETS[0]]["ridge_combined"]
        if fault == "boolean_coefficient":
            parameters["coefficients"][0] = True
        elif fault == "indicator_index":
            parameters["missing_indicator_features"] = [True]
        else:
            parameters["scaler_scale"][0] = -1.0
        rewrite_bundle_file(bundle, "models.json", models)
    else:
        metadata = json.loads((bundle / "freeze_metadata.json").read_bytes())
        if fault == "provenance_hash":
            metadata["development_source_sha256"] = "0" * 64
        elif fault == "rights":
            metadata["development_data_rights"] = {
                "authorized": True,
                "basis": "Changed declaration",
            }
        elif fault == "training_count":
            metadata["training_summary"][TARGETS[0]]["n_observed_pitches"] = 999
        elif fault == "range":
            metadata["training_summary"][TARGETS[0]]["predictor_profiles"][FEATURES[0]][
                "maximum"
            ] = -99
        else:
            metadata["measurement_contract"][FEATURES[0]]["canonical_unit"] = "days"
        rewrite_bundle_file(bundle, "freeze_metadata.json", metadata)
    with pytest.raises(ValueError):
        load_frozen_bundle(bundle)


def test_output_collisions_refuse_to_overwrite_inputs_or_prior_results(tmp_path):
    bundle = freeze(tmp_path)
    prepared = prepare(tmp_path, synthetic_cohort("external", 2), "external")
    with pytest.raises(ValueError, match="separate"):
        evaluate_external(prepared, bundle, bundle)
    output = tmp_path / "evaluation"
    evaluate_external(prepared, bundle, output)
    original = (output / "external_metrics.csv").read_bytes()
    with pytest.raises(ValueError, match="nonempty"):
        evaluate_external(prepared, bundle, output)
    assert (output / "external_metrics.csv").read_bytes() == original


def test_cli_freeze_error_is_an_explicit_failure_not_success(tmp_path, capsys):
    assert (
        main(
            [
                "freeze",
                "--prepared",
                str(tmp_path / "absent"),
                "--protocol",
                str(tmp_path / "absent.json"),
                "--output",
                str(tmp_path / "frozen"),
            ]
        )
        == 1
    )
    assert "workflow stopped" in capsys.readouterr().out
    assert not (tmp_path / "frozen").exists()
