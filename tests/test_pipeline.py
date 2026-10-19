"""Real-data offline integration: generated artifacts and completion semantics."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from pitching.cli import run_workflow

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_offline_pipeline_produces_current_verified_reports(tmp_path, monkeypatch):
    cache = ROOT / "data/raw"
    if not (cache / "baseball_pitching/data/poi/poi_metrics.csv").is_file():
        pytest.skip("Run `uv run pitching fetch` for the real-data integration workflow.")
    metadata = run_workflow(ROOT, cache, tmp_path, offline=True)
    assert metadata["status"] == "completed"
    for name, expected in metadata["project_code_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for name, expected in metadata["artifacts_sha256"].items():
        path = tmp_path / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        if path.suffix == ".png":
            assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            assert path.stat().st_size > 1000
    predictions = pd.read_csv(tmp_path / "oof_predictions.csv")
    assert len(predictions) == 411 * 2 * 2
    assert not predictions.duplicated(["session_pitch", "target", "model"]).any()
    assert predictions.groupby("user").fold.nunique().eq(1).all()
    splits = json.loads((tmp_path / "split_audit.json").read_text())
    assert all(set(split["train_athletes"]).isdisjoint(split["test_athletes"]) for split in splits)
    assert len(list((tmp_path / "figures").glob("*.png"))) == 5
    assert "CC BY-NC-SA" in (tmp_path / "ATTRIBUTION.md").read_text()

    def fail_model(*args, **kwargs):
        raise ValueError("simulated interrupted model refresh")

    monkeypatch.setattr("pitching.cli.evaluate_baselines", fail_model)
    monkeypatch.setattr("pitching.cli.exploratory_plots", lambda *a, **k: [])
    with pytest.raises(ValueError, match="interrupted"):
        run_workflow(ROOT, cache, tmp_path, offline=True)
    assert not (tmp_path / "run_metadata.json").exists()
