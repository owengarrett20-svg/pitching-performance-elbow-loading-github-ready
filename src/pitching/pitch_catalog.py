"""Source-linked measured-marker recordings for the released pitching cohort.

The browser reads only prepared numerical assets. Preparation is a separate,
offline operation using the checksum-verified upstream C3D release. These are
skin-marker replays, not camera recordings, joint-center models, or synchronized
processed-signal reconstructions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd

from pitching.data import COMMIT, VARIABLES
from pitching.motion_examples import (
    ARCHIVE_BYTES,
    ARCHIVE_SHA256,
    ARCHIVE_URL,
    BODY_LABELS,
    LICENSE_URL,
    RELEASE_TAG,
    exact_archive_member,
    normalize_motion,
    sha256_file,
    verify_archive,
)
from pitching.video_lab import MotionAssetError, load_marker_frames, verified_asset

GENERATOR = "pitching.pitch_catalog.prepare_pitch_catalog"
CATALOG_DIRECTORY = "pitch_catalog"
ANALYSIS_RELATIVE_PATH = "assets/demo/reports/analysis.csv"
_FRAME_KEYS = ("positions_m", "times_s", "labels", "links")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object(payload: bytes) -> dict:
    def unique_pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate catalog JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeDecodeError) as error:
        raise MotionAssetError("The marker catalog is not valid unique-key JSON.") from error
    if not isinstance(value, dict):
        raise MotionAssetError("The marker catalog must contain an object.")
    return value


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _basename(value: Any, suffix: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(character in value for character in ("/", "\\", ":", "\x00"))
        and Path(value).name == value
        and Path(value).suffix.lower() == suffix
    )


def _analysis(root: Path) -> tuple[pd.DataFrame, bytes]:
    path = root / ANALYSIS_RELATIVE_PATH
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise MotionAssetError("The catalog source analysis must stay within its project.")
    try:
        payload = path.read_bytes()
        table = pd.read_csv(
            path, dtype={"session_pitch": "string", "user": "string", "filename_new": "string"}
        )
    except (OSError, ValueError, pd.errors.ParserError) as error:
        raise MotionAssetError(
            "The released analysis table is unavailable for catalog matching."
        ) from error
    required = {"session_pitch", "user", "filename_new", *VARIABLES}
    if not required.issubset(table) or table.empty:
        raise MotionAssetError("The marker catalog requires the released pitch-level analysis.")
    for name in ("session_pitch", "user", "filename_new"):
        if table[name].isna().any() or table[name].str.strip().eq("").any():
            raise MotionAssetError("Catalog source identifiers must be present.")
    if table.session_pitch.duplicated().any() or table.filename_new.duplicated().any():
        raise MotionAssetError("Catalog source pitch IDs and filenames must be one to one.")
    return table, payload


def _identity(entry: dict, source: pd.Series) -> None:
    if any(
        not isinstance(entry.get(name), str) or entry[name] != str(source[name])
        for name in ("session_pitch", "user", "filename_new")
    ):
        raise MotionAssetError(
            "Catalog pitch, athlete, or C3D filename differs from source metadata."
        )
    if not _basename(entry["filename_new"], ".c3d"):
        raise MotionAssetError("Catalog source C3D filenames must be basenames.")


def normalize_catalog_motion(c3d: dict, stride: int = 6) -> tuple[dict, list[str], dict[str, str]]:
    """Retain source labels while removing one explicit trajectory namespace.

    Three released trials use ``Skeleton_001_<marker>`` for the same documented
    marker labels. This operation changes label strings only. It neither moves
    coordinates nor turns display links into an anatomical skeleton.
    """
    labels = [str(label).strip() for label in c3d["parameters"]["POINT"]["LABELS"]["value"]]
    aliases: dict[str, str] = {}
    namespaces: set[str] = set()
    for label in labels:
        match = re.fullmatch(r"(Skeleton_[0-9]+_)([A-Za-z0-9]+)", label)
        if match and match[2] in BODY_LABELS:
            namespaces.add(match[1])
            aliases[label] = match[2]
    if len(namespaces) > 1 or (namespaces and any(label in BODY_LABELS for label in labels)):
        raise ValueError("Ambiguous or multiple subject namespaces; marker labels were not merged.")
    renamed = [aliases.get(label, label) for label in labels]
    if len(set(renamed)) != len(renamed):
        raise ValueError("Source marker aliases are not one to one.")
    if aliases:
        aliased = dict(c3d)
        parameters = dict(c3d["parameters"])
        point = dict(parameters["POINT"])
        parameter = dict(point["LABELS"])
        parameter["value"] = renamed
        point["LABELS"] = parameter
        parameters["POINT"] = point
        aliased["parameters"] = parameters
    else:
        aliased = c3d
    return normalize_motion(aliased, stride=stride), labels, aliases


def _entry(entry: dict, source: pd.Series) -> None:
    _identity(entry, source)
    for name in ("source_file_sha256", "frames_sha256"):
        if not _sha(entry.get(name)):
            raise MotionAssetError(f"Catalog recording has an invalid {name}.")
    if not _basename(entry.get("frames_file"), ".npz"):
        raise MotionAssetError("Catalog arrays must be local NPZ basenames.")
    if entry["frames_file"] != f"{entry['session_pitch']}.npz":
        raise MotionAssetError("Catalog array filename does not identify its source pitch.")
    member = entry.get("archive_member")
    if (
        not isinstance(member, str)
        or "\\" in member
        or PurePosixPath(member).is_absolute()
        or ".." in PurePosixPath(member).parts
        or PurePosixPath(member).name != entry["filename_new"]
    ):
        raise MotionAssetError("Catalog source archive member is invalid.")
    for name in ("n_frames", "n_source_frames", "stride"):
        if type(entry.get(name)) is not int or entry[name] < 1:
            raise MotionAssetError(f"Catalog recording has an invalid {name}.")
    if entry["n_source_frames"] < 2 or entry["n_frames"] != math.ceil(
        entry["n_source_frames"] / entry["stride"]
    ):
        raise MotionAssetError("Catalog source/display sample counts are inconsistent.")
    for name in ("point_rate_hz", "playback_rate"):
        value = entry.get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise MotionAssetError(f"Catalog recording has an invalid {name}.")
    units = entry.get("units_original")
    if not isinstance(units, str) or units.lower() not in {"m", "cm", "mm"}:
        raise MotionAssetError("Catalog source coordinate units are unsupported.")
    labels = entry.get("marker_labels")
    if (
        not isinstance(labels, list)
        or not labels
        or any(not isinstance(label, str) or not label.strip() for label in labels)
        or len(set(labels)) != len(labels)
    ):
        raise MotionAssetError("Catalog marker labels must be present and unique.")
    raw_labels, aliases = entry.get("source_marker_labels"), entry.get("marker_label_aliases")
    if (
        not isinstance(raw_labels, list)
        or not raw_labels
        or any(not isinstance(label, str) or not label.strip() for label in raw_labels)
        or len(set(raw_labels)) != len(raw_labels)
        or not isinstance(aliases, dict)
    ):
        raise MotionAssetError(
            "Catalog source marker labels and explicit aliases must be retained."
        )
    namespaces = set()
    for raw_label, display_label in aliases.items():
        match = re.fullmatch(r"(Skeleton_[0-9]+_)([A-Za-z0-9]+)", raw_label)
        if (
            not match
            or match[2] not in BODY_LABELS
            or match[2] != display_label
            or raw_label not in raw_labels
            or display_label not in labels
        ):
            raise MotionAssetError(
                "Catalog source marker alias is outside its reviewed namespace rule."
            )
        namespaces.add(match[1])
    if (
        len(namespaces) > 1
        or len(set(aliases.values())) != len(aliases)
        or (namespaces and any(label in BODY_LABELS for label in raw_labels))
    ):
        raise MotionAssetError("Catalog marker aliases cannot merge subject namespaces.")
    expected_labels = [aliases.get(label, label) for label in raw_labels]
    expected_labels = [label for label in expected_labels if label in BODY_LABELS]
    if expected_labels != labels:
        raise MotionAssetError(
            "Catalog displayed marker labels do not follow their declared source aliases."
        )
    for name, count in (
        ("missing_points", "n_frames"),
        ("n_source_missing_points", "n_source_frames"),
    ):
        value = entry.get(name)
        if type(value) is not int or not 0 <= value <= entry[count] * len(labels):
            raise MotionAssetError(f"Catalog recording has an invalid {name}.")
    poi = entry.get("poi")
    if not isinstance(poi, dict) or set(poi) != set(VARIABLES):
        raise MotionAssetError("Catalog recording must retain all five released POI fields.")
    for name in VARIABLES:
        expected = source[name]
        actual = poi[name]
        if pd.isna(expected):
            matches = actual is None
        else:
            matches = (
                type(actual) in (int, float)
                and math.isfinite(actual)
                and np.isclose(actual, float(expected), atol=1e-9, rtol=1e-12)
            )
        if not matches:
            raise MotionAssetError("Catalog POI values differ from the matched source pitch.")


def _quality(examples: list[dict], unavailable: list[dict], n_rows: int) -> dict:
    return {
        "n_analysis_pitches": n_rows,
        "n_available_recordings": len(examples),
        "n_unavailable_recordings": len(unavailable),
        "n_athletes_with_recordings": len({entry["user"] for entry in examples}),
        "source_rates_hz": sorted({entry["point_rate_hz"] for entry in examples}),
        "source_units": sorted({entry["units_original"] for entry in examples}),
        "marker_counts": sorted({len(entry["marker_labels"]) for entry in examples}),
        "n_recordings_with_missing_display_points": sum(
            entry["missing_points"] > 0 for entry in examples
        ),
        "n_missing_display_points": sum(entry["missing_points"] for entry in examples),
        "n_missing_source_points": sum(entry["n_source_missing_points"] for entry in examples),
        "n_display_frames": sum(entry["n_frames"] for entry in examples),
        "n_source_frames": sum(entry["n_source_frames"] for entry in examples),
        "n_recordings_with_namespace_aliases": sum(
            bool(entry["marker_label_aliases"]) for entry in examples
        ),
        "prepared_npz_bytes": sum(entry["frames_bytes"] for entry in examples),
    }


def load_pitch_catalog(project_root: Path) -> tuple[Path, dict]:
    """Validate source-bound catalog metadata; no files are downloaded or fitted."""
    root = Path(project_root).resolve()
    directory = root / "assets" / CATALOG_DIRECTORY
    path = directory / "manifest.json"
    if directory.is_symlink() or path.is_symlink() or not directory.resolve().is_relative_to(root):
        raise MotionAssetError("The marker catalog must stay within its project directory.")
    try:
        manifest = _object(path.read_bytes())
    except OSError as error:
        raise MotionAssetError("The expanded marker catalog is unavailable locally.") from error
    archive = {"url": ARCHIVE_URL, "sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES}
    if (
        manifest.get("schema_version") != 1
        or manifest.get("kind") != "observed_skin_marker_catalog"
        or manifest.get("generator") != GENERATOR
        or manifest.get("source_commit") != COMMIT
        or manifest.get("release_tag") != RELEASE_TAG
        or manifest.get("archive") != archive
        or manifest.get("license_url") != LICENSE_URL
    ):
        raise MotionAssetError("The marker catalog does not match its reviewed source and schema.")
    table, analysis_bytes = _analysis(root)
    if manifest.get("analysis_sha256") != _digest(analysis_bytes):
        raise MotionAssetError("The marker catalog is bound to a different source analysis.")
    if manifest.get("source_manifest_sha256") != _digest(
        (root / "source_manifest.json").read_bytes()
    ):
        raise MotionAssetError("The marker catalog source manifest has changed.")
    examples, unavailable = manifest.get("examples"), manifest.get("unavailable")
    if not isinstance(examples, list) or not isinstance(unavailable, list) or not examples:
        raise MotionAssetError("The catalog must list prepared and unavailable source recordings.")
    source = table.set_index("session_pitch", drop=False)
    identifiers: set[str] = set()
    for item in examples + unavailable:
        if not isinstance(item, dict):
            raise MotionAssetError("Catalog recordings must contain metadata objects.")
        pitch = item.get("session_pitch")
        if not isinstance(pitch, str) or pitch not in source.index or pitch in identifiers:
            raise MotionAssetError("Catalog source pitch IDs are absent or duplicated.")
        identifiers.add(pitch)
        _identity(item, source.loc[pitch])
    if identifiers != set(table.session_pitch):
        raise MotionAssetError("The catalog must account for every released analysis pitch.")
    for entry in examples:
        _entry(entry, source.loc[entry["session_pitch"]])
        if type(entry.get("frames_bytes")) is not int or entry["frames_bytes"] <= 0:
            raise MotionAssetError("Catalog recording has an invalid array byte count.")
    for entry in unavailable:
        if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            raise MotionAssetError("An unavailable recording must retain its preparation reason.")
    if manifest.get("quality_summary") != _quality(examples, unavailable, len(table)):
        raise MotionAssetError("Catalog quality totals differ from their source recordings.")
    return directory, manifest


def catalog_examples(frame: pd.DataFrame, manifest: dict) -> list[dict]:
    """Return recordings matching both selected pitch and athlete, with no substitutes."""
    if not {"session_pitch", "user"}.issubset(frame):
        return []
    pairs = {
        (str(pitch), str(user))
        for pitch, user in frame[["session_pitch", "user"]].itertuples(index=False, name=None)
        if pd.notna(pitch) and pd.notna(user)
    }
    return [
        entry for entry in manifest["examples"] if (entry["session_pitch"], entry["user"]) in pairs
    ]


def load_catalog_frames(directory: Path, entry: dict) -> dict[str, np.ndarray]:
    """Verify numerical assets, labels, timing, and missingness before rendering."""
    path = verified_asset(directory, entry["frames_file"], entry["frames_sha256"], ".npz")
    if path.stat().st_size != entry["frames_bytes"]:
        raise MotionAssetError("Catalog numerical asset byte count differs from its manifest.")
    arrays = load_marker_frames(path, entry["n_frames"])
    if arrays["positions_m"].dtype != np.float64 or arrays["times_s"].dtype != np.float64:
        raise MotionAssetError(
            "Catalog coordinates and times must retain float64 numerical values."
        )
    absent = np.isnan(arrays["positions_m"])
    if np.any(absent.any(axis=2) != absent.all(axis=2)):
        raise MotionAssetError(
            "An invalid source marker sample must retain all three coordinates as missing."
        )
    if arrays["labels"].tolist() != entry["marker_labels"]:
        raise MotionAssetError("Catalog numerical marker labels differ from their source manifest.")
    expected = np.arange(0, entry["n_source_frames"], entry["stride"]) / entry["point_rate_hz"]
    if not np.array_equal(arrays["times_s"], expected):
        raise MotionAssetError("Catalog display times differ from the declared source sampling.")
    missing = int((~np.isfinite(arrays["positions_m"]).all(axis=2)).sum())
    if missing != entry["missing_points"]:
        raise MotionAssetError("Catalog missing-point count differs from its numerical asset.")
    if not np.isfinite(arrays["positions_m"]).all(axis=2).any():
        raise MotionAssetError("The recording contains no complete observed skin markers.")
    return arrays


def prepare_pitch_catalog(
    project_root: Path, archive_path: Path, output_dir: Path | None = None
) -> dict:
    """Prepare every exact metadata-linked recording from the verified offline archive.

    The destination must not exist. A staging directory is renamed only after
    all candidates have been examined. Source files are temporary and never
    included in the public derivative catalog.
    """
    root, archive_path = Path(project_root).resolve(), Path(archive_path).resolve()
    verify_archive(archive_path)
    from pitching.deployment import verified_demo_reports

    verified_demo_reports(root)
    table, analysis_bytes = _analysis(root)
    output = Path(output_dir).resolve() if output_dir else root / "assets" / CATALOG_DIRECTORY
    if output.exists():
        raise ValueError("Preserve the existing catalog; prepare into a new output directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        import ezc3d
    except ImportError as error:
        raise RuntimeError(
            "Install the optional motion dependency with uv sync --extra motion."
        ) from error
    stage = Path(tempfile.mkdtemp(prefix=".pitch-catalog-", dir=output.parent))
    examples: list[dict] = []
    unavailable: list[dict] = []
    try:
        with (
            tempfile.TemporaryDirectory(prefix="obp-c3d-") as temporary,
            zipfile.ZipFile(archive_path) as archive,
        ):
            for row in table.sort_values("session_pitch", kind="stable").to_dict(orient="records"):
                identity = {
                    name: str(row[name]) for name in ("session_pitch", "user", "filename_new")
                }
                pitch, filename = identity["session_pitch"], identity["filename_new"]
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", pitch):
                    raise ValueError(
                        "Pitch identifiers cannot safely name prepared numerical assets."
                    )
                try:
                    member = exact_archive_member(archive, filename)
                    contents = archive.read(member)
                    source_path = Path(temporary) / filename
                    source_path.write_bytes(contents)
                    motion, source_labels, aliases = normalize_catalog_motion(
                        ezc3d.c3d(str(source_path)), stride=6
                    )
                    source_path.unlink()
                    if not np.isfinite(motion["positions_m"]).all(axis=2).any():
                        raise ValueError("No complete observed skin-marker coordinates")
                    frames_path = stage / f"{pitch}.npz"
                    np.savez_compressed(frames_path, **{key: motion[key] for key in _FRAME_KEYS})
                    entry = {
                        **identity,
                        "archive_member": member,
                        "source_file_sha256": _digest(contents),
                        "point_rate_hz": motion["point_rate_hz"],
                        "units_original": motion["units_original"],
                        "n_source_frames": motion["n_source_frames"],
                        "n_frames": motion["n_frames"],
                        "marker_labels": motion["labels"].tolist(),
                        "source_marker_labels": source_labels,
                        "marker_label_aliases": aliases,
                        "excluded_marker_labels": motion["excluded_marker_labels"],
                        "frames_file": frames_path.name,
                        "frames_sha256": sha256_file(frames_path),
                        "frames_bytes": frames_path.stat().st_size,
                        "stride": 6,
                        "playback_rate": 0.5,
                        "missing_points": motion["missing_points"],
                        "n_source_missing_points": motion["n_source_missing_points"],
                        "poi": {
                            name: None if pd.isna(row[name]) else float(row[name])
                            for name in VARIABLES
                        },
                    }
                    _entry(entry, pd.Series(row))
                    load_catalog_frames(stage, entry)
                    examples.append(entry)
                except (ValueError, RuntimeError, KeyError, OSError) as error:
                    (stage / f"{pitch}.npz").unlink(missing_ok=True)
                    unavailable.append(
                        {
                            **identity,
                            "reason": f"{type(error).__name__}: {error}".replace(
                                temporary, "<temporary>"
                            ),
                        }
                    )
        manifest = {
            "schema_version": 1,
            "kind": "observed_skin_marker_catalog",
            "generator": GENERATOR,
            "generator_code_sha256": sha256_file(Path(__file__)),
            "normalizer_code_sha256": sha256_file(Path(__file__).with_name("motion_examples.py")),
            "source_commit": COMMIT,
            "release_tag": RELEASE_TAG,
            "archive": {"url": ARCHIVE_URL, "sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES},
            "analysis_sha256": _digest(analysis_bytes),
            "source_manifest_sha256": sha256_file(root / "source_manifest.json"),
            "license_url": LICENSE_URL,
            "attribution": "Driveline Baseball Research & Development, OpenBiomechanics Project",
            "derivative_license": "CC BY-NC-SA 4.0 plus the upstream additional affiliation exclusion",
            "description": "Downsampled observed C3D skin-marker coordinates in meters for playable browser replays; no camera footage.",
            "marker_label_policy": "Retain original labels. Remove a single unambiguous Skeleton_<digits>_ trajectory namespace only for known body-marker suffixes; preserve a reversible raw-to-display label map. Coordinates are unchanged and multiple subject namespaces are rejected.",
            "time_reference": "Seconds from each C3D capture start; no event or processed-signal alignment inferred.",
            "missing_policy": "Negative/nonfinite residuals or nonfinite coordinates remain NaN; no filling or interpolation.",
            "examples": examples,
            "unavailable": unavailable,
            "quality_summary": _quality(examples, unavailable, len(table)),
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        (stage / "ATTRIBUTION.md").write_text(
            "# Measured-marker replay catalog\n\n"
            "Source: Driveline Baseball Research & Development, OpenBiomechanics Project.\n\n"
            f"{ARCHIVE_URL}\n\nSource release archive SHA-256: `{ARCHIVE_SHA256}`.\n\n"
            "Changes: exact metadata-linked C3Ds selected; observed skin-marker coordinates converted "
            "to meters and retained every sixth source sample; guide links and numerical arrays "
            "prepared for an interactive display. Missing points remain missing.\n\n"
            "Some source trajectories carry a single Skeleton_<digits>_ subject namespace. "
            "That namespace is removed only from known body-marker display labels, with "
            "the complete original labels and reversible alias map retained. Coordinates, "
            "sampling, and signs are unchanged; different subjects are never merged.\n\n"
            "These are motion-capture marker replays, not camera recordings or validated skeletal models. "
            "Their clocks have not been aligned to released processed signals or pitch events.\n\n"
            "Data and derivatives retain CC BY-NC-SA 4.0 plus the upstream additional professional-sports / "
            "financial-analysis affiliation exclusion. Original software licensing does not grant data rights.\n\n"
            f"Full terms: {LICENSE_URL}\n",
            encoding="utf-8",
        )
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return manifest
