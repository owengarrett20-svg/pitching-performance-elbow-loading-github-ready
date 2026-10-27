"""The application brief must retain source-bound evidence and its actual limits."""

import hashlib
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.phase2_dashboard import load_phase2_reports
from pitching.research_brief import (
    brief_html,
    brief_markdown,
    brief_metadata_json,
    build_research_brief,
    export_research_brief,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "assets/demo/reports"


@pytest.fixture(scope="module")
def brief():
    return build_research_brief(ROOT, created_utc=datetime(2026, 10, 26, tzinfo=UTC))


def test_brief_counts_scores_and_contrasts_come_from_saved_source(brief):
    analysis = pd.read_csv(REPORTS / "analysis.csv", dtype={"user": str})
    scores = pd.read_csv(REPORTS / "phase2/phase2_model_metrics.csv")
    contrasts = pd.read_csv(REPORTS / "phase2/phase2_comparisons.csv")
    assert brief.cohort["n_pitches"] == len(analysis) == 411
    assert brief.cohort["n_athletes"] == analysis.user.nunique() == 100
    assert brief.cohort["n_sessions"] == analysis.session.nunique()
    assert brief.cohort["pitches_per_athlete_min"] == analysis.groupby("user").size().min()
    assert brief.cohort["pitches_per_athlete_max"] == analysis.groupby("user").size().max()
    pd.testing.assert_frame_equal(brief.metrics, scores, check_dtype=False)
    for summary in brief.primary:
        row = contrasts.loc[
            contrasts.target.eq(summary.target)
            & contrasts.model.eq("ridge_combined")
            & contrasts.reference.eq("ridge_anthropometric")
            & contrasts.metric.eq("athlete_mae")
        ].iloc[0]
        assert summary.difference == pytest.approx(row.estimate)
        assert summary.low == row.ci_low
        assert summary.high == row.ci_high
    assert brief.measurement_summary["all_passed"] is True
    assert brief.measurement_summary["n_checks"] == 12
    assert brief.cohort["source_columns_with_missing"] == 25
    assert brief.settings["n_partitions"] == 10


def test_formats_distinguish_evidence_and_uncertain_elbow_increment(brief):
    document, markdown = brief_html(brief), brief_markdown(brief)
    for text in (document, markdown):
        assert "uncertain" in text
        assert "not preregister" in text
        assert "AI assistance" in text
        assert "professional-sports" in text
        assert "not a peer-reviewed publication" in text
    assert "Increment remains uncertain: interval includes zero" in document
    assert "12 of 12 source comparisons passed" in document
    assert "Independent inverse dynamics" in document and "Not performed" in document
    assert "External cohort validation" in document
    assert document.count('<section class="sheet">') == 2
    assert "<script" not in document and "<link" not in document and "<img" not in document
    assert document.count("<svg") == 2


def test_provenance_matches_exported_evidence_and_analysis_bytes(brief):
    record = json.loads(brief_metadata_json(brief))
    assert (
        record["analysis_sha256"]
        == hashlib.sha256((REPORTS / "analysis.csv").read_bytes()).hexdigest()
    )
    assert (
        record["measurement_audit_csv_sha256"]
        == hashlib.sha256(brief.measurement_rows.to_csv(index=False).encode()).hexdigest()
    )
    assert (
        record["evidence_csv_sha256"]
        == hashlib.sha256(brief.evidence.to_csv(index=False).encode()).hexdigest()
    )
    assert record["measurement_audit_scope"] == "source_scalar_reproduction_only"
    assert record["created_utc"] == "2026-10-26T00:00:00+00:00"
    assert "/workspace/" not in brief_metadata_json(brief)


def test_missing_measurement_assets_never_become_successful_validation(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ValueError("Corrupted asset at /private/operator/path")

    monkeypatch.setattr("pitching.research_brief.audit_measurement_summaries", unavailable)
    result = build_research_brief(ROOT)
    assert result.measurement_summary["all_passed"] is False
    assert result.measurement_rows.empty
    document = brief_html(result)
    assert "12 of 12" not in document
    assert "Source-summary audit unavailable" in document
    assert "/private/operator/path" not in document + brief_metadata_json(result)
    assert len(result.metrics) == 8


@pytest.fixture
def local_reports(tmp_path):
    path = tmp_path / "reports"
    shutil.copytree(REPORTS, path)
    return path


@pytest.mark.parametrize("name", ["audit.json", "missingness.csv"])
def test_unbound_quality_record_is_rejected(local_reports, name):
    path = local_reports / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_research_brief(ROOT, local_reports)


def test_rehashed_but_inconsistent_join_audit_is_not_accepted(local_reports):
    path = local_reports / "audit.json"
    audit = json.loads(path.read_text())
    audit["n_athletes"] += 1
    path.write_text(json.dumps(audit))
    parent_path = local_reports / "run_metadata.json"
    parent = json.loads(parent_path.read_text())
    parent["artifacts_sha256"]["audit.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    parent_path.write_text(json.dumps(parent))
    with pytest.raises(ValueError, match="does not describe"):
        build_research_brief(ROOT, local_reports)


def test_other_source_cannot_be_presented_as_the_pinned_obp_brief(local_reports):
    child_path = local_reports / "phase2/run_metadata.json"
    child = json.loads(child_path.read_text())
    child["source_commit"] = "synthetic-other-source-for-software-test-only"
    child_path.write_text(json.dumps(child))
    parent_path = local_reports / "run_metadata.json"
    parent = json.loads(parent_path.read_text())
    parent["artifacts_sha256"]["phase2/run_metadata.json"] = hashlib.sha256(
        child_path.read_bytes()
    ).hexdigest()
    parent_path.write_text(json.dumps(parent))
    with pytest.raises(ValueError, match="requires the pinned OBP"):
        build_research_brief(ROOT, local_reports)


def test_html_escapes_untrusted_audit_strings(brief):
    # Malicious software-test text, never an observed biomechanics measurement.
    audit = brief.measurement_rows.copy()
    audit.loc[audit.index[0], "label"] = '</td><script>alert("test")</script>'
    document = brief_html(replace(brief, measurement_rows=audit))
    assert "<script" not in document
    assert "&lt;script&gt;" in document


def test_brief_does_not_describe_changed_hyperparameters_as_the_fixed_baselines(monkeypatch):
    # A deliberately perturbed software-test specification, not a research comparison.
    reports = load_phase2_reports(REPORTS)
    spec = deepcopy(reports.spec)
    spec["models"]["ridge_anthropometric"]["alpha"] = 99
    monkeypatch.setattr(
        "pitching.research_brief.load_phase2_reports", lambda *_: replace(reports, spec=spec)
    )
    with pytest.raises(ValueError, match="common ridge penalty"):
        build_research_brief(ROOT, REPORTS)


def test_export_checksums_and_refusal_to_replace_existing_files(tmp_path):
    output = tmp_path / "brief"
    result = export_research_brief(ROOT, output)
    assert len(result["files"]) == 5
    for name, digest in result["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(ValueError, match="must be new"):
        export_research_brief(ROOT, output)
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}


def test_export_does_not_write_inside_a_verified_input(local_reports):
    output = local_reports / "new-brief"
    with pytest.raises(ValueError, match="separate from input reports"):
        export_research_brief(ROOT, output, local_reports)
    assert not output.exists()


def test_exporter_command_runs_the_read_only_builder(tmp_path):
    output = tmp_path / "command-brief"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/export_research_brief.py"),
            "--project-dir",
            str(ROOT),
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Exported 5 verified" in result.stdout
    assert (output / "research-brief.html").is_file()
    assert (
        json.loads((output / "research-brief-provenance.json").read_text())["cohort"]["n_pitches"]
        == 411
    )


def test_rendering_does_not_download_fit_or_bootstrap(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The research brief must be read-only")

    for name in (
        "urllib.request.urlopen",
        "pitching.data.urlopen",
        "pitching.models.evaluate_baselines",
        "pitching.phase2.evaluate_phase2",
        "pitching.phase2.compare_fixed_predictions",
        "sklearn.pipeline.Pipeline.fit",
    ):
        monkeypatch.setattr(name, forbidden)
    app = AppTest.from_string(
        "from pathlib import Path\nfrom pitching.research_brief import render_research_brief\n"
        f"render_research_brief(Path({str(ROOT)!r}),Path({str(REPORTS)!r}))\n",
        default_timeout=30,
    ).run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.error
    assert any(item.label == "Recorded pitches" and item.value == "411" for item in app.metric)
    assert len(app.get("download_button")) == 4
    assert not app.get("file_uploader")
