"""Deployment integrity fixtures are synthetic bytes, never research observations."""

import hashlib
import json
from pathlib import Path

import pytest

from pitching.data import COMMIT
from pitching.deployment import export_demo_snapshot, verified_demo_reports

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = [
    "analysis.csv",
    "audit.json",
    "missingness.csv",
    "descriptive_summary.csv",
    "oof_predictions.csv",
    "model_metrics.csv",
    "fold_metrics.csv",
    "fold_assignments.csv",
    "split_audit.json",
    "model_spec.json",
    "figures/test.png",
]


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


@pytest.fixture
def project(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    for name in ARTIFACTS:
        path = reports / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic integrity fixture: {name}\n".encode())
    for name in ("ATTRIBUTION.md", "audit.md"):
        (reports / name).write_text("Synthetic test fixture, not a research report.\n")
    for name in ("app.py", "source_manifest.json", "uv.lock"):
        (tmp_path / name).write_text(f"synthetic input fixture: {name}\n")
    metadata = {
        "status": "completed",
        "source_commit": COMMIT,
        "project_code_sha256": {"app.py": digest((tmp_path / "app.py").read_bytes())},
        "input_manifest_sha256": digest((tmp_path / "source_manifest.json").read_bytes()),
        "uv_lock_sha256": digest((tmp_path / "uv.lock").read_bytes()),
        "artifacts_sha256": {name: digest((reports / name).read_bytes()) for name in ARTIFACTS},
    }
    (reports / "run_metadata.json").write_text(json.dumps(metadata))
    return tmp_path


def rewrite_manifest(project, change):
    path = project / "assets/demo/manifest.json"
    manifest = json.loads(path.read_text())
    change(manifest)
    path.write_text(json.dumps(manifest))


def rewrite_snapshot_metadata(project, change):
    path = project / "assets/demo/reports/run_metadata.json"
    metadata = json.loads(path.read_text())
    change(metadata)
    path.write_text(json.dumps(metadata))
    rewrite_manifest(
        project,
        lambda manifest: manifest["files"].update(
            {
                "reports/run_metadata.json": {
                    "sha256": digest(path.read_bytes()),
                    "bytes": path.stat().st_size,
                }
            }
        ),
    )


def test_round_trip_is_complete_read_only_and_idempotent(project):
    manifest = export_demo_snapshot(project)
    reports = verified_demo_reports(project)
    assert reports == project / "assets/demo/reports"
    assert manifest["source_commit"] == COMMIT
    assert "LICENSE-DATA.md" in manifest["license_url"]
    assert "CC BY-NC-SA" in manifest["attribution"]
    assert len(manifest["files"]) == len(ARTIFACTS) + 3
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in reports.rglob("*")
        if path.is_file()
    }
    assert verified_demo_reports(project) == reports
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}
    assert export_demo_snapshot(project) == manifest
    assert not (project / "data").exists()


@pytest.mark.parametrize("name", ["analysis.csv", "figures/test.png"])
def test_export_rejects_stale_source_reports_before_changing_snapshot(project, name):
    export_demo_snapshot(project)
    manifest_path = project / "assets/demo/manifest.json"
    previous = manifest_path.read_bytes()
    (project / "reports" / name).write_text("modified fixture")
    with pytest.raises(ValueError, match="artifact checksum mismatch"):
        export_demo_snapshot(project)
    assert manifest_path.read_bytes() == previous
    assert verified_demo_reports(project).is_dir()


@pytest.mark.parametrize("name", ["app.py", "source_manifest.json", "uv.lock"])
def test_export_rejects_stale_code_or_inputs(project, name):
    (project / name).write_text("changed after report generation")
    with pytest.raises(ValueError, match="input checksum mismatch"):
        export_demo_snapshot(project)
    assert not (project / "assets/demo").exists()


def test_export_preserves_unmanaged_directories_and_unknown_files(project):
    target = project / "assets/demo"
    target.mkdir(parents=True)
    (target / "notes.txt").write_text("preserve me")
    with pytest.raises(ValueError, match="unmanaged"):
        export_demo_snapshot(project)
    assert (target / "notes.txt").read_text() == "preserve me"
    (target / "notes.txt").unlink()
    export_demo_snapshot(project)
    (target / "notes.txt").write_text("preserve me too")
    export_demo_snapshot(project)
    assert (target / "notes.txt").read_text() == "preserve me too"


def test_export_rejects_unsafe_source_artifact_paths_before_writing(project):
    marker = project / "reports/run_metadata.json"
    metadata = json.loads(marker.read_text())
    metadata["artifacts_sha256"]["../outside.csv"] = "0" * 64
    marker.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Unsafe snapshot path"):
        export_demo_snapshot(project)
    assert not (project / "assets/demo").exists()


def test_export_requires_source_attribution_before_writing(project):
    (project / "reports/ATTRIBUTION.md").unlink()
    with pytest.raises(FileNotFoundError):
        export_demo_snapshot(project)
    assert not (project / "assets/demo").exists()


@pytest.mark.parametrize("field,value", [("status", "failed"), ("source_commit", "wrong")])
def test_export_requires_completed_pinned_reports(project, field, value):
    marker = project / "reports/run_metadata.json"
    metadata = json.loads(marker.read_text())
    metadata[field] = value
    marker.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="completed|pinned"):
        export_demo_snapshot(project)


def test_verifier_rejects_corrupted_report(project):
    export_demo_snapshot(project)
    (project / "assets/demo/reports/analysis.csv").write_text("modified fixture")
    with pytest.raises(ValueError, match="checksum/size mismatch"):
        verified_demo_reports(project)


def test_verifier_rejects_missing_snapshot_file(project):
    export_demo_snapshot(project)
    (project / "assets/demo/reports/missingness.csv").unlink()
    with pytest.raises(FileNotFoundError):
        verified_demo_reports(project)


@pytest.mark.parametrize("name", ["reports/analysis.csv", "reports/run_metadata.json"])
def test_verifier_requires_all_snapshot_reports(project, name):
    export_demo_snapshot(project)
    rewrite_manifest(project, lambda manifest: manifest["files"].pop(name))
    with pytest.raises(ValueError, match="missing required reports"):
        verified_demo_reports(project)


@pytest.mark.parametrize("field,value", [("status", "failed"), ("source_commit", "wrong")])
def test_verifier_checks_pipeline_completion_and_revision(project, field, value):
    export_demo_snapshot(project)
    rewrite_snapshot_metadata(project, lambda metadata: metadata.update({field: value}))
    with pytest.raises(ValueError, match="completed|pinned"):
        verified_demo_reports(project)


def test_verifier_checks_agreement_with_pipeline_artifact_hashes(project):
    export_demo_snapshot(project)
    rewrite_snapshot_metadata(
        project, lambda metadata: metadata["artifacts_sha256"].update({"analysis.csv": "0" * 64})
    )
    with pytest.raises(ValueError, match="checksums disagree"):
        verified_demo_reports(project)


@pytest.mark.parametrize(
    "name",
    ["../escape", "/tmp/escape", "reports/../escape", "reports\\escape", "reports/C:/escape"],
)
def test_verifier_rejects_unsafe_manifest_paths(project, name):
    export_demo_snapshot(project)
    rewrite_manifest(
        project,
        lambda manifest: manifest["files"].update({name: {"sha256": "0" * 64, "bytes": 0}}),
    )
    with pytest.raises(ValueError, match="Unsafe snapshot path"):
        verified_demo_reports(project)


def test_verifier_rejects_symlinked_report(project):
    export_demo_snapshot(project)
    path = project / "assets/demo/reports/analysis.csv"
    path.unlink()
    path.symlink_to(project / "reports/analysis.csv")
    with pytest.raises(ValueError, match="symlinks"):
        verified_demo_reports(project)


@pytest.mark.parametrize(
    "field,value",
    [("schema_version", 99), ("source_commit", "wrong"), ("report_directory", "../reports")],
)
def test_verifier_requires_supported_pinned_manifest(project, field, value):
    export_demo_snapshot(project)
    rewrite_manifest(project, lambda manifest: manifest.update({field: value}))
    with pytest.raises(ValueError, match="schema|pinned|report_directory"):
        verified_demo_reports(project)


def test_committed_real_snapshot_if_present():
    if not (ROOT / "assets/demo/manifest.json").is_file():
        pytest.skip("Run scripts/export_demo_snapshot.py after the real pipeline.")
    reports = verified_demo_reports(ROOT)
    assert (reports / "analysis.csv").is_file()
    assert (reports / "oof_predictions.csv").is_file()
