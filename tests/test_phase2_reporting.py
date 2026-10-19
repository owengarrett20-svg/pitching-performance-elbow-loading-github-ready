"""Synthetic saved-result fixtures exercise interpretation without research data."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from pitching.phase2_reporting import write_phase2_report


@pytest.fixture
def saved_results(tmp_path: Path) -> tuple[Path, dict]:
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "analysis/phase2_plan.json").read_text())
    plan = copy.deepcopy(plan)
    # This small synthetic fixture is deliberately unlike the research cohort.
    plan["sensitivity_seeds"] = [42, 43, 44]
    scores = []
    values = {
        "pitch_speed_mph": {
            "dummy_mean": 4.0,
            "ridge_anthropometric": 3.0,
            "ridge_kinematic": 3.5,
            "ridge_combined": 2.0,
        },
        "elbow_varus_moment": {
            "dummy_mean": 8.0,
            "ridge_anthropometric": 5.0,
            "ridge_kinematic": 7.0,
            "ridge_combined": 6.0,
        },
    }
    for target in plan["targets"]:
        for model in plan["models"]:
            error = values[target][model]
            scores.append(
                {
                    "target": target,
                    "model": model,
                    "n_pitches": 10,
                    "n_athletes": 3,
                    "athlete_mae": error,
                    "mae": error + 0.25,
                    "rmse": error + 0.5,
                    "r2": 0.2,
                }
            )
    pd.DataFrame(scores).to_csv(tmp_path / "phase2_model_metrics.csv", index=False)
    comparisons = []
    for target in plan["targets"]:
        for pair in plan["planned_comparisons"]:
            difference = values[target][pair["model"]] - values[target][pair["reference"]]
            for metric in plan["bootstrap"]["metrics"]:
                half_width = 0.8 if target == "pitch_speed_mph" else 1.5
                comparisons.append(
                    {
                        "target": target,
                        "model": pair["model"],
                        "reference": pair["reference"],
                        "metric": metric,
                        "estimate": difference,
                        "ci_low": difference - half_width,
                        "ci_high": difference + half_width,
                        "n_athletes": 3,
                        "bootstrap_replicates": plan["bootstrap"]["n_resamples"],
                    }
                )
    pd.DataFrame(comparisons).to_csv(tmp_path / "phase2_comparisons.csv", index=False)
    sensitivity = []
    combined_by_seed = {
        "pitch_speed_mph": {42: 2.0, 43: 3.5, 44: 2.5},
        "elbow_varus_moment": {42: 6.0, 43: 4.0, 44: 7.0},
    }
    for seed in plan["sensitivity_seeds"]:
        for row in scores:
            updated = {**row, "partition_seed": seed}
            if row["model"] == "ridge_combined":
                error = combined_by_seed[row["target"]][seed]
                updated.update(athlete_mae=error, mae=error + 0.25, rmse=error + 0.5)
            sensitivity.append(updated)
    pd.DataFrame(sensitivity).to_csv(tmp_path / "phase2_sensitivity_metrics.csv", index=False)
    (tmp_path / "phase2_plan.json").write_text(json.dumps(plan))
    return tmp_path, plan


def test_report_preserves_direction_sample_size_and_uncertainty_scope(saved_results):
    report_dir, plan = saved_results
    paths = write_phase2_report(report_dir, plan)
    assert paths[0] == report_dir / "phase2_report.md"
    assert len(paths) == 4
    report = paths[0].read_text(encoding="utf-8")
    assert "| Pitch speed | 10 | 3 |" in report
    assert "| Elbow varus moment | 10 | 3 |" in report
    assert "411" not in report
    assert "**Pitch speed:** the combined model had lower" in report
    assert "**Elbow varus moment:** the combined model had higher" in report
    assert "-1.000 mph" in report
    assert "1.000 N·m" in report
    assert "Its conditional interval does not include zero" in report
    assert "Its conditional interval includes zero" in report
    assert "-1.000 to 0.500 mph; negative in 2 of 3 saved partitions" in report
    assert "-1.000 to 2.000 N·m; negative in 1 of 3 saved partitions" in report
    for scope in (
        "conditional on fixed out-of-fold predictions",
        "no refitting within bootstrap",
        "model-refitting, model-selection, and full training-set uncertainty",
        "Overlapping cross-validation training folds",
        "not independent experiments",
        "not a preregistered study",
        "no injury labels",
        "No p-values",
        "significant shareholder of a professional sports organization",
        "phase2_plan.json",
    ):
        assert scope in report
    for path in paths[1:]:
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(path) as figure:
            figure.verify()
        with Image.open(path) as figure:
            assert figure.width >= 1200
            assert figure.height >= 700


def test_report_rejects_reversed_candidate_difference_before_output(saved_results):
    report_dir, plan = saved_results
    comparison_path = report_dir / "phase2_comparisons.csv"
    comparisons = pd.read_csv(comparison_path)
    comparisons.loc[0, "estimate"] *= -1
    comparisons.to_csv(comparison_path, index=False)
    with pytest.raises(ValueError, match="model-minus-reference"):
        write_phase2_report(report_dir, plan)
    assert not (report_dir / "figures").exists()
    assert not (report_dir / "phase2_report.md").exists()


def test_report_requires_all_planned_contrasts(saved_results):
    report_dir, plan = saved_results
    comparison_path = report_dir / "phase2_comparisons.csv"
    comparisons = pd.read_csv(comparison_path)
    comparisons.iloc[1:].to_csv(comparison_path, index=False)
    with pytest.raises(ValueError, match="planned result keys"):
        write_phase2_report(report_dir, plan)


def test_report_rejects_sensitivity_sample_change(saved_results):
    report_dir, plan = saved_results
    sensitivity_path = report_dir / "phase2_sensitivity_metrics.csv"
    sensitivity = pd.read_csv(sensitivity_path)
    sensitivity.loc[0, "n_athletes"] = 2
    sensitivity.to_csv(sensitivity_path, index=False)
    with pytest.raises(ValueError, match="same eligible sample"):
        write_phase2_report(report_dir, plan)


def test_undefined_r_squared_is_reported_as_undefined(saved_results):
    report_dir, plan = saved_results
    metric_path = report_dir / "phase2_model_metrics.csv"
    scores = pd.read_csv(metric_path)
    scores.loc[0, "r2"] = float("nan")
    scores.to_csv(metric_path, index=False)
    report = write_phase2_report(report_dir, plan)[0].read_text(encoding="utf-8")
    assert "| undefined |" in report
    assert "R² is undefined" in report
