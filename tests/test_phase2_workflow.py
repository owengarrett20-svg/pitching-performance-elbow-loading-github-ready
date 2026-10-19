"""Frozen-plan control and real-data study completion/export integration."""

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from pitching.deployment import export_demo_snapshot, verified_demo_reports
from pitching.phase2_dashboard import load_phase2_reports
from pitching.phase2_workflow import load_phase2_plan, run_phase2_workflow

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plan_project(tmp_path):
    destination = tmp_path / "analysis/phase2_plan.json"
    destination.parent.mkdir()
    shutil.copyfile(ROOT / "analysis/phase2_plan.json", destination)
    return tmp_path


def _change_plan(root, change):
    path = root / "analysis/phase2_plan.json"
    plan = json.loads(path.read_bytes())
    change(plan)
    path.write_text(json.dumps(plan))


def test_recorded_plan_controls_the_runtime_and_retains_its_exact_bytes(plan_project):
    plan, payload = load_phase2_plan(plan_project)
    assert payload == (plan_project / "analysis/phase2_plan.json").read_bytes()
    assert plan["primary_metric"] == "athlete_mae"
    assert plan["primary_comparison"]["improvement_direction"] == "negative"
    assert plan["bootstrap"]["refit_within_resample"] is False


@pytest.mark.parametrize(
    "change,match",
    [
        (
            lambda p: p["feature_sets"]["combined"].append("pitch_speed_mph"),
            "forbidden predictor",
        ),
        (lambda p: p.update(ridge_alpha=1), "fixed alpha"),
        (lambda p: p.update(group_column="session_pitch"), "athlete-grouped"),
        (lambda p: p["planned_comparisons"].pop(), "every implemented"),
        (lambda p: p["bootstrap"].update(unit="pitch"), "resampling unit"),
        (lambda p: p["bootstrap"].update(refit_within_resample=True), "bootstrap scope"),
        (lambda p: p.update(sensitivity_seeds=[42, 42]), "unique"),
        (lambda p: p["bootstrap"].update(interval_quantiles=[0.05, 0.95]), "quantiles"),
    ],
)
def test_unsupported_plan_changes_fail_before_analysis(plan_project, change, match):
    _change_plan(plan_project, change)
    with pytest.raises(ValueError, match=match):
        load_phase2_plan(plan_project)


@pytest.mark.integration
def test_full_study_reproduces_baseline_and_exports_all_phase2_reports(tmp_path, monkeypatch):
    cache = ROOT / "data/raw"
    if not (cache / "baseball_pitching/data/poi/poi_metrics.csv").is_file():
        pytest.skip("Run `uv run --frozen pitching fetch` for the verified real-data study.")
    output = tmp_path / "reports"
    metadata = run_phase2_workflow(ROOT, cache, output, offline=True)
    assert metadata["status"] == "completed"
    assert metadata["phase1_reproduction"]["passed"] is True
    assert metadata["phase1_reproduction"]["compared_rows"] == 411 * 2 * 2
    assert (
        metadata["plan_sha256"]
        == hashlib.sha256((ROOT / "analysis/phase2_plan.json").read_bytes()).hexdigest()
    )
    loaded = load_phase2_reports(output)
    assert len(loaded.metrics) == 8
    assert loaded.metrics.n_pitches.eq(411).all()
    assert loaded.metrics.n_athletes.eq(100).all()
    assert len(loaded.comparisons) == 2 * 6 * 2
    assert loaded.sensitivity.partition_seed.nunique() == 10
    assert len(loaded.verified_bytes) >= 24
    for name, expected in metadata["artifacts_sha256"].items():
        path = output / "phase2" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    assignments = pd.read_csv(output / "phase2/phase2_sensitivity_fold_assignments.csv")
    assert assignments.groupby(["partition_seed", "user"]).fold.nunique().eq(1).all()
    assert len(assignments) == 411 * 10

    # A simulated clean publication tree contains only producing code/inputs,
    # plus the explicit export. Never replace the repository's actual snapshot.
    published = tmp_path / "publication"
    parent = json.loads((output / "run_metadata.json").read_bytes())
    names = set(parent["project_code_sha256"]) | {
        "uv.lock",
        "source_manifest.json",
        "analysis/phase2_plan.json",
    }
    for name in names:
        destination = published / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    snapshot = export_demo_snapshot(published, output)
    assert "reports/phase2/phase2_report.md" in snapshot["files"]
    assert "reports/phase2/phase2_bootstrap_samples.csv.gz" in snapshot["files"]
    assert load_phase2_reports(verified_demo_reports(published)).metrics.n_pitches.eq(411).all()

    # Even if output files remain intact, changing the active scientific plan
    # must prevent those reports from being exported as a current study.
    _change_plan(published, lambda plan: plan["bootstrap"].update(seed=123))
    with pytest.raises(ValueError, match="input checksum mismatch"):
        export_demo_snapshot(published, output)

    def interrupted(*args, **kwargs):
        raise ValueError("simulated Phase 2 interruption")

    monkeypatch.setattr("pitching.phase2.evaluate_phase2", interrupted)
    monkeypatch.setattr("pitching.cli.exploratory_plots", lambda *a, **k: [])
    monkeypatch.setattr("pitching.cli.error_plots", lambda *a, **k: [])
    with pytest.raises(ValueError, match="simulated Phase 2 interruption"):
        run_phase2_workflow(ROOT, cache, output, offline=True)
    assert not (output / "phase2/run_metadata.json").exists()
    parent = json.loads((output / "run_metadata.json").read_bytes())
    assert "phase2/run_metadata.json" not in parent["artifacts_sha256"]
    with pytest.raises(FileNotFoundError, match="No completed Phase 2"):
        load_phase2_reports(output)
