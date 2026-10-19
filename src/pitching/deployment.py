"""Export and verify a small, read-only reference snapshot for hosted Streamlit.

These are the real pipeline's derived reports, not another training path. Export
is explicit; importing this module or reading a snapshot never downloads data,
fits a model, or writes files. Checksums detect accidental corruption and stale
exports; they are not a signature or independent validation of the research.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from pitching.data import COMMIT, REPOSITORY

_GENERATOR = "pitching.deployment.export_demo_snapshot"
_REQUIRED_ARTIFACTS = {
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
}
_EXTRA_REPORTS = {"run_metadata.json", "ATTRIBUTION.md", "audit.md"}
_REQUIRED_FILES = {f"reports/{name}" for name in _REQUIRED_ARTIFACTS | _EXTRA_REPORTS}


def _relative_name(name: str) -> PurePosixPath:
    """Accept only canonical, relative POSIX names on every host platform."""
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError(f"Unsafe snapshot path: {name!r}")
    relative = PurePosixPath(name)
    if (
        relative.is_absolute()
        or any(part in {".", ".."} or ":" in part for part in relative.parts)
        or relative.as_posix() != name
        or name == "."
    ):
        raise ValueError(f"Unsafe snapshot path: {name!r}")
    return relative


def _safe_path(base: Path, name: str) -> Path:
    relative = _relative_name(name)
    if base.is_symlink():
        raise ValueError(f"Snapshot directories must not be symlinks: {base}")
    destination = base
    for part in relative.parts:
        destination = destination / part
        if destination.is_symlink():
            raise ValueError(f"Snapshot paths must not be symlinks: {name}")
    if not destination.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"Snapshot path escapes its directory: {name}")
    return destination


def _json_object(contents: bytes, label: str) -> dict:
    try:
        value = json.loads(contents)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON in {label}.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object.")  # noqa: TRY004 - serialized content
    return value


def _metadata(contents: bytes) -> dict:
    metadata = _json_object(contents, "run_metadata.json")
    if metadata.get("status") != "completed":
        raise ValueError("Reference reports require a completed pipeline run.")
    if metadata.get("source_commit") != COMMIT:
        raise ValueError("Reference reports must use the reviewed, pinned OBP source commit.")
    artifacts = metadata.get("artifacts_sha256")
    if not isinstance(artifacts, dict) or not _REQUIRED_ARTIFACTS.issubset(artifacts):
        raise ValueError("Pipeline metadata is missing required artifact checksums.")
    for name, digest in artifacts.items():
        _relative_name(name)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"Invalid pipeline checksum for {name}.")
    return metadata


def _digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _verify_run_inputs(root: Path, metadata: dict) -> None:
    code = metadata.get("project_code_sha256")
    if not isinstance(code, dict) or not code:
        raise ValueError("Pipeline metadata must identify the code that produced its reports.")
    expected_files = {
        **code,
        "source_manifest.json": metadata.get("input_manifest_sha256"),
        "uv.lock": metadata.get("uv_lock_sha256"),
    }
    analysis_inputs = metadata.get("analysis_inputs_sha256", {})
    if not isinstance(analysis_inputs, dict):
        raise ValueError("Pipeline analysis input checksums must be an object.")  # noqa: TRY004
    expected_files.update(analysis_inputs)
    for name, expected in expected_files.items():
        if _digest(_safe_path(root, name).read_bytes()) != expected:
            raise ValueError(f"Pipeline input checksum mismatch: {name}. Regenerate reports.")


def export_demo_snapshot(project_root: Path, reports_dir: Path | None = None) -> dict:
    """Copy a complete, checksum-verified local run into ``assets/demo``.

    Existing unmanaged directories are preserved by refusing to export into them.
    A repeat export updates owned files and leaves any unrelated files untouched.
    Verification finishes before any existing snapshot is changed. Publish the
    resulting manifest and its listed files together in one Git commit.
    """
    root = Path(project_root).resolve()
    source = Path(reports_dir) if reports_dir is not None else root / "reports"
    metadata_bytes = _safe_path(source, "run_metadata.json").read_bytes()
    metadata = _metadata(metadata_bytes)
    _verify_run_inputs(root, metadata)
    names = sorted(set(metadata["artifacts_sha256"]) | _EXTRA_REPORTS)
    contents = {}
    for name in names:
        payload = (
            metadata_bytes if name == "run_metadata.json" else _safe_path(source, name).read_bytes()
        )
        expected = metadata["artifacts_sha256"].get(name)
        if expected is not None and _digest(payload) != expected:
            raise ValueError(f"Pipeline artifact checksum mismatch: {name}. Regenerate reports.")
        contents[f"reports/{name}"] = payload

    target = _safe_path(root, "assets/demo")
    manifest_path = _safe_path(target, "manifest.json")
    if target.exists() and any(target.iterdir()):
        if not manifest_path.is_file():
            raise ValueError("Refusing to overwrite an unmanaged assets/demo directory.")
        previous = _json_object(manifest_path.read_bytes(), "snapshot manifest")
        if previous.get("generator") != _GENERATOR or previous.get("schema_version") != 1:
            raise ValueError("Refusing to overwrite an unmanaged assets/demo directory.")
    # Check every destination before creating or replacing any files.
    destinations = {name: _safe_path(target, name) for name in contents}
    manifest = {
        "schema_version": 1,
        "generator": _GENERATOR,
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "report_directory": "reports",
        "description": (
            "Verified reference reports from the pinned OpenBiomechanics pitching dataset. "
            "Hosted viewing is read-only; no data are downloaded and no models are fitted. "
            "Use the local pipeline to reproduce or regenerate these derived artifacts."
        ),
        "license_url": f"{REPOSITORY}/blob/{COMMIT}/LICENSE-DATA.md",
        "attribution": (
            "Driveline Baseball Research & Development, OpenBiomechanics Project. "
            "Derived tables, figures, and athlete-held-out model results retain upstream "
            "CC BY-NC-SA 4.0 and additional professional-organization restrictions; "
            "see reports/ATTRIBUTION.md and docs/LICENSING.md."
        ),
        "files": {
            name: {"sha256": _digest(payload), "bytes": len(payload)}
            for name, payload in contents.items()
        },
    }
    for name, destination in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents[name])
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


def verified_demo_reports(project_root: Path) -> Path:
    """Verify the entire committed reference snapshot and return its report path.

    Reject incomplete, stale, modified, or unsafe snapshots. This function is
    read-only and intentionally does not fall back to fetching data or training.
    """
    root = Path(project_root).resolve()
    target = _safe_path(root, "assets/demo")
    manifest = _json_object(_safe_path(target, "manifest.json").read_bytes(), "snapshot manifest")
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported reference snapshot schema version.")
    if manifest.get("source_commit") != COMMIT or manifest.get("source_repository") != REPOSITORY:
        raise ValueError("Reference snapshot must identify the reviewed, pinned OBP revision.")
    if manifest.get("report_directory") != "reports":
        raise ValueError("Reference snapshot report_directory must be 'reports'.")
    files = manifest.get("files")
    if not isinstance(files, dict) or not _REQUIRED_FILES.issubset(files):
        raise ValueError("Reference snapshot is missing required reports.")
    payloads = {}
    for name, entry in files.items():
        relative = _relative_name(name)
        if len(relative.parts) < 2 or relative.parts[0] != "reports":
            raise ValueError(f"Reference snapshot file must be within reports/: {name}")
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid reference snapshot file entry: {name}")  # noqa: TRY004
        payload = _safe_path(target, name).read_bytes()
        if _digest(payload) != entry.get("sha256") or len(payload) != entry.get("bytes"):
            raise ValueError(f"Reference snapshot checksum/size mismatch: {name}")
        payloads[name] = payload
    metadata = _metadata(payloads["reports/run_metadata.json"])
    for name, expected in metadata["artifacts_sha256"].items():
        snapshot_name = f"reports/{name}"
        if snapshot_name not in files or files[snapshot_name]["sha256"] != expected:
            raise ValueError(f"Reference snapshot and pipeline artifact checksums disagree: {name}")
    return _safe_path(target, "reports")
