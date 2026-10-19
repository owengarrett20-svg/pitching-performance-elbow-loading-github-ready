"""Synthetic-only checks of splitting, missingness, and leakage protections."""

import json

import numpy as np
import pandas as pd
import pytest

from pitching.models import FEATURES, TARGETS, evaluate_baselines, save_model_results


@pytest.fixture
def synthetic_pitches():
    """Artificial fixture values, not observations from OpenBiomechanics."""
    rng = np.random.default_rng(123)
    n_athletes, repeats = 12, 3
    n = n_athletes * repeats
    frame = pd.DataFrame(
        {
            "user": np.repeat([f"athlete-{i:02d}" for i in range(n_athletes)], repeats),
            "session_pitch": [f"synthetic-pitch-{i}" for i in range(n)],
            "session": np.repeat([f"session-{i}" for i in range(n_athletes)], repeats),
            "pitch_speed_mph": 75 + rng.normal(size=n) * 3,
            "elbow_varus_moment": 65 + rng.normal(size=n) * 8,
        }
    )
    for feature in FEATURES:
        frame[feature] = rng.normal(size=n)
    frame.loc[::5, FEATURES[0]] = np.nan
    return frame


def test_athlete_disjoint_folds_are_shared_by_both_targets(synthetic_pitches):
    result = evaluate_baselines(synthetic_pitches, n_splits=3, seed=42)
    assert result.fold_assignments.groupby("user")["fold"].nunique().eq(1).all()
    assert len(result.fold_assignments) == len(synthetic_pitches)
    for split in result.split_audit:
        assert set(split["train_athletes"]).isdisjoint(split["test_athletes"])
        assert split["athlete_overlap"] == 0
    folds = result.predictions.groupby("session_pitch")["fold"].nunique()
    assert folds.eq(1).all()
    assert set(result.predictions.target) == set(TARGETS)
    assert len(result.predictions) == len(synthetic_pitches) * len(TARGETS) * 2


def test_dummy_uses_observed_training_mean_and_never_imputes_targets(synthetic_pitches):
    data = synthetic_pitches.copy()
    data.loc[0, TARGETS[0]] = np.nan
    data.loc[1, TARGETS[1]] = np.inf
    result = evaluate_baselines(data, n_splits=3)
    assignment = result.fold_assignments.set_index("session_pitch")["fold"]
    for target in TARGETS:
        observed_mask = np.isfinite(data[target])
        for model in ("dummy_mean", "ridge"):
            selected = result.predictions.query("target == @target and model == @model")
            assert set(selected.session_pitch) == set(data.loc[observed_mask, "session_pitch"])
        dummy = result.predictions.query("target == @target and model == 'dummy_mean'")
        for fold, heldout in dummy.groupby("fold"):
            training = data["session_pitch"].map(assignment).ne(fold) & observed_mask
            expected = data.loc[training, target].mean()
            np.testing.assert_allclose(heldout.predicted, expected)
    assert result.feature_manifest["excluded_target_rows"] == dict.fromkeys(TARGETS, 1)


def test_feature_allowlist_prevents_target_and_identifier_leakage(synthetic_pitches):
    original = evaluate_baselines(synthetic_pitches, n_splits=3)
    changed = synthetic_pitches.copy()
    # A metadata speed duplicate can be a perfect predictor and must still be
    # ignored. Other outcomes and file paths are forbidden predictors as well.
    changed["pitch_speed_mph_metadata"] = changed[TARGETS[0]]
    changed["filename"] = changed[TARGETS[0]].map(lambda value: f"/{value}/trial.c3d")
    changed[TARGETS[1]] = changed[TARGETS[0]] * 100
    rechecked = evaluate_baselines(changed, n_splits=3)
    assert tuple(original.feature_manifest["features"]) == FEATURES
    assert not set(FEATURES) & {"user", "session", "session_pitch", *TARGETS}
    before = original.predictions.query("target == 'pitch_speed_mph'").predicted
    after = rechecked.predictions.query("target == 'pitch_speed_mph'").predicted
    np.testing.assert_array_equal(before, after)


def test_heldout_values_cannot_change_fitted_preprocessing(synthetic_pitches):
    first = evaluate_baselines(synthetic_pitches, n_splits=3)
    heldout_ids = first.fold_assignments.query("fold == 1").session_pitch.tolist()
    data = synthetic_pitches.copy()
    focus_id, outlier_id = heldout_ids[:2]
    data.loc[data.session_pitch.eq(focus_id), FEATURES[0]] = np.nan
    reference = evaluate_baselines(data, n_splits=3)
    changed = data.copy()
    # This changes test distribution, including where a global scaler/median
    # would be fit. An unchanged held-out pitch must retain its prediction.
    changed.loc[changed.session_pitch.eq(outlier_id), list(FEATURES)] = 1e12
    rechecked = evaluate_baselines(changed, n_splits=3)
    query = "session_pitch == @focus_id and model == 'ridge'"
    np.testing.assert_array_equal(
        reference.predictions.query(query).predicted,
        rechecked.predictions.query(query).predicted,
    )


def test_all_missing_training_features_and_infinities_are_supported(synthetic_pitches):
    data = synthetic_pitches.copy()
    data[FEATURES[1]] = np.nan
    data.loc[0, FEATURES[2]] = np.inf
    data.loc[1, FEATURES[2]] = -np.inf
    # Nonunique external indexes must not cause prediction/outcome misalignment.
    data.index = np.zeros(len(data), dtype=int)
    result = evaluate_baselines(data, n_splits=3)
    assert np.isfinite(result.predictions.predicted).all()
    assert result.feature_manifest["nonfinite_feature_counts"][FEATURES[2]] == 2
    for fold in result.split_audit:
        for target in TARGETS:
            assert FEATURES[1] in fold["targets"][target]["all_missing_train_features"]


def test_metrics_include_macro_athlete_error(synthetic_pitches):
    result = evaluate_baselines(synthetic_pitches, n_splits=3)
    for row in result.metrics.itertuples():
        selected = result.predictions.query("target == @row.target and model == @row.model")
        assert row.n_pitches == len(selected)
        assert row.n_athletes == selected.user.nunique()
        assert row.mae == pytest.approx(selected.absolute_error.mean())
        assert row.rmse == pytest.approx(np.sqrt((selected.residual**2).mean()))
        assert row.athlete_mae == pytest.approx(
            selected.groupby("user").absolute_error.mean().mean()
        )
    np.testing.assert_allclose(
        result.predictions.residual,
        result.predictions.observed - result.predictions.predicted,
    )


def test_failures_are_explanatory(synthetic_pitches):
    with pytest.raises(ValueError, match="Missing required model columns"):
        evaluate_baselines(synthetic_pitches.drop(columns=[FEATURES[0]]), n_splits=3)
    with pytest.raises(ValueError, match="at least 20 athletes"):
        evaluate_baselines(synthetic_pitches, n_splits=20)
    data = synthetic_pitches.copy()
    data[TARGETS[0]] = np.nan
    with pytest.raises(ValueError, match="No finite observed target"):
        evaluate_baselines(data, n_splits=3)
    data.loc[data.user.eq("athlete-00"), TARGETS[0]] = 80
    with pytest.raises(ValueError, match="at least two athletes"):
        evaluate_baselines(data, n_splits=3)
    data = synthetic_pitches.copy()
    data.loc[0, "session_pitch"] = data.loc[1, "session_pitch"]
    with pytest.raises(ValueError, match="one pitch per row"):
        evaluate_baselines(data, n_splits=3)


def test_reproducibility_and_saved_audit_artifacts(synthetic_pitches, tmp_path):
    first = evaluate_baselines(synthetic_pitches, n_splits=3, seed=79)
    second = evaluate_baselines(synthetic_pitches, n_splits=3, seed=79)
    pd.testing.assert_frame_equal(first.predictions, second.predictions)
    pd.testing.assert_frame_equal(first.fold_assignments, second.fold_assignments)
    save_model_results(first, tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == {
        "oof_predictions.csv",
        "model_metrics.csv",
        "fold_metrics.csv",
        "fold_assignments.csv",
        "split_audit.json",
        "model_spec.json",
    }
    assert json.loads((tmp_path / "split_audit.json").read_text()) == first.split_audit
    spec = json.loads((tmp_path / "model_spec.json").read_text())
    assert spec["models"]["ridge"]["alpha"] == 10
    assert spec["seed"] == 79
