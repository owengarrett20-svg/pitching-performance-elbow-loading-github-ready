"""Prepare truthful, metadata-linked replays of released C3D skin markers.

These are motion-capture visualizations, not camera footage or a new joint model.
The preparation command is offline: obtain the canonical release archive first.
Only the three exact metadata filenames are extracted after archive verification.
"""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from pitching.data import COMMIT, VARIABLES, join_pitching, read_source, verify_source
from pitching.runtime import configure_plot_cache

RELEASE_TAG = "dataset-v1"
ARCHIVE_NAME = "pitching_c3d.zip"
ARCHIVE_URL = (
    "https://github.com/drivelineresearch/openbiomechanics/releases/download/"
    f"{RELEASE_TAG}/{ARCHIVE_NAME}"
)
ARCHIVE_SHA256 = "2f5277dc63c7f7535fa4b15310d6f38b3f3b761e572896eec529854c8c920d29"
ARCHIVE_BYTES = 184602895
LICENSE_URL = f"https://github.com/drivelineresearch/openbiomechanics/blob/{COMMIT}/LICENSE-DATA.md"
UNIT_SCALES = {"m": 1.0, "mm": 0.001, "cm": 0.01}

# Display lines join observed skin markers. They are not anatomical joint centers.
DISPLAY_LINKS = (
    ("LFHD", "RFHD"),
    ("LFHD", "LBHD"),
    ("RFHD", "RBHD"),
    ("LBHD", "RBHD"),
    ("C7", "CLAV"),
    ("CLAV", "STRN"),
    ("C7", "T10"),
    ("STRN", "T10"),
    ("LSHO", "RSHO"),
    ("LSHO", "LELB"),
    ("LELB", "LWRA"),
    ("LWRA", "LWRB"),
    ("LWRA", "LFIN"),
    ("RSHO", "RELB"),
    ("RELB", "RWRA"),
    ("RWRA", "RWRB"),
    ("RWRA", "RFIN"),
    ("LASI", "RASI"),
    ("LPSI", "RPSI"),
    ("LASI", "LPSI"),
    ("RASI", "RPSI"),
    ("LSHO", "LASI"),
    ("RSHO", "RASI"),
    ("LASI", "LKNE"),
    ("LKNE", "LANK"),
    ("LANK", "LHEE"),
    ("LANK", "LTOE"),
    ("RASI", "RKNE"),
    ("RKNE", "RANK"),
    ("RANK", "RHEE"),
    ("RANK", "RTOE"),
)
BODY_LABELS = frozenset(label for pair in DISPLAY_LINKS for label in pair) | frozenset(
    {
        "RBAK",
        "LBAK",
        "LIC",
        "RIC",
        "LUPA",
        "RUPA",
        "LFRM",
        "RFRM",
        "LTHI",
        "RTHI",
        "LTIB",
        "RTIB",
        "LMELB",
        "RMELB",
        "LMKNE",
        "RMKNE",
        "LMANK",
        "RMANK",
        "LKNEE",
        "RKNEE",
        "LKNEE2",
        "RKNEE2",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(path: Path) -> None:
    """Reject partial or altered downloads before reading any C3D member."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Missing {path}. Download {ARCHIVE_URL} first.")
    if path.stat().st_size != ARCHIVE_BYTES or sha256_file(path) != ARCHIVE_SHA256:
        raise ValueError("Pitching C3D archive checksum/size mismatch; do not use its contents.")


def select_example_rows(analysis: pd.DataFrame) -> pd.DataFrame:
    """Select near the minimum, median, maximum speed, with distinct athletes.

    Equal distances are broken by exact session_pitch in lexical order, making
    selection independent of input row order. Every output row is a source row.
    """
    required = {"session_pitch", "user", "filename_new", *VARIABLES}
    if not required.issubset(analysis.columns):
        raise ValueError("Motion selection needs the validated POI/metadata analysis table.")
    if analysis.session_pitch.duplicated().any() or analysis.filename_new.duplicated().any():
        raise ValueError("Pitch IDs and C3D filenames must have one-to-one metadata mappings.")
    eligible = analysis.loc[np.isfinite(analysis.pitch_speed_mph)].copy()
    if eligible.user.nunique() < 3:
        raise ValueError("At least three athletes with recorded pitch speed are required.")
    used: set[str] = set()
    selected = []
    for role, quantile in (("lower_speed", 0.0), ("near_median_speed", 0.5), ("higher_speed", 1.0)):
        target = float(eligible.pitch_speed_mph.quantile(quantile))
        candidates = eligible.loc[~eligible.user.astype(str).isin(used)].copy()
        candidates["_distance"] = (candidates.pitch_speed_mph - target).abs()
        row = candidates.sort_values(["_distance", "session_pitch"], kind="stable").iloc[0]
        selected_row = row.drop(labels="_distance").to_dict()
        selected_row.update(example_role=role, selection_target_mph=target)
        selected.append(selected_row)
        used.add(str(row.user))
    return pd.DataFrame(selected)


def exact_archive_member(archive: zipfile.ZipFile, filename: str) -> str:
    """Resolve an exact public metadata basename, never an inferred pitch number."""
    if Path(filename).name != filename or "\\" in filename or not filename.lower().endswith(".c3d"):
        raise ValueError("Metadata must specify one C3D basename.")
    matches = [
        name
        for name in archive.namelist()
        if PurePosixPath(name).name == filename and not name.startswith("__MACOSX/")
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one archive member for {filename}; found {len(matches)}."
        )
    return matches[0]


def normalize_motion(c3d: dict, stride: int = 6) -> dict:
    """Convert observed marker coordinates to meters without filling marker gaps.

    ezc3d stores residuals in meta_points, whereas points[3] is homogeneous 1.
    Negative/nonfinite residuals or nonfinite XYZ invalidate the whole point.
    Unknown labels, including ball points, are excluded from this body view.
    """
    if not isinstance(stride, int) or stride < 1:
        raise ValueError("Stride must be a positive integer.")
    params = c3d["parameters"]["POINT"]
    labels = [str(label).strip() for label in params["LABELS"]["value"]]
    units = str(params["UNITS"]["value"][0]).strip()
    if units.lower() not in UNIT_SCALES:
        raise ValueError(f"Unsupported C3D point units: {units!r}.")
    rate = float(params["RATE"]["value"][0])
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("C3D point rate must be finite and positive.")
    points = np.asarray(c3d["data"]["points"], dtype=float)
    if points.ndim != 3 or points.shape[0] < 3 or points.shape[1] != len(labels):
        raise ValueError("C3D point array and labels are inconsistent.")
    if len(set(labels)) != len(labels) or points.shape[2] < 2:
        raise ValueError("C3D labels must be unique and the trial must contain motion frames.")
    residuals = np.asarray(c3d["data"]["meta_points"]["residuals"], dtype=float)
    if residuals.shape != (1, len(labels), points.shape[2]):
        raise ValueError("C3D residual array is inconsistent with marker frames.")
    include = [index for index, label in enumerate(labels) if label in BODY_LABELS]
    if not include:
        raise ValueError("No documented body markers were found in the C3D.")
    kept_labels = [labels[index] for index in include]
    coordinates = points[:3, include, :].transpose(2, 1, 0) * UNIT_SCALES[units.lower()]
    valid_residual = np.isfinite(residuals[0, include, :].T) & (residuals[0, include, :].T >= 0)
    valid = np.isfinite(coordinates).all(axis=2) & valid_residual
    coordinates[~valid] = np.nan
    indices = np.arange(0, points.shape[2], stride)
    downsampled = coordinates[indices]
    index_by_name = {label: index for index, label in enumerate(kept_labels)}
    aliases = {"LKNE": "LKNEE", "RKNE": "RKNEE"}
    links = []
    for first, second in DISPLAY_LINKS:
        first = first if first in index_by_name else aliases.get(first, first)
        second = second if second in index_by_name else aliases.get(second, second)
        if first in index_by_name and second in index_by_name:
            links.append((index_by_name[first], index_by_name[second]))
    return {
        "positions_m": downsampled,
        "times_s": indices.astype(float) / rate,
        "labels": np.asarray(kept_labels, dtype="U"),
        "links": np.asarray(links, dtype=np.int32).reshape(-1, 2),
        "point_rate_hz": rate,
        "units_original": units,
        "n_source_frames": int(points.shape[2]),
        "n_frames": len(indices),
        "missing_points": int((~np.isfinite(downsampled).all(axis=2)).sum()),
        "n_source_missing_points": int((~valid).sum()),
        "excluded_marker_labels": [label for label in labels if label not in BODY_LABELS],
    }


def render_motion(motion: dict, output_path: Path, session_pitch: str, speed: float, fps: int = 30):
    """Render marker-only playback using native ffmpeg, preserving missing points."""
    configure_plot_cache()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter

    positions = motion["positions_m"]
    times = motion["times_s"]
    finite_positions = positions[np.isfinite(positions).all(axis=2)]
    if not finite_positions.size:
        raise ValueError("Cannot render a trial without valid observed marker positions.")
    low, high = finite_positions.min(axis=0), finite_positions.max(axis=0)
    center = (low + high) / 2
    span = max(float((high - low).max()) * 1.12, 0.5)
    fig = plt.figure(figsize=(6.4, 6.4), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=19, azim=-66)
    ax.set(
        xlim=(center[0] - span / 2, center[0] + span / 2),
        ylim=(center[1] - span / 2, center[1] + span / 2),
        zlim=(center[2] - span / 2, center[2] + span / 2),
        xlabel="X: toward home (m)",
        ylabel="Y: toward first (m)",
        zlabel="Z: up (m)",
    )
    ax.set_box_aspect((1, 1, 1))
    fig.suptitle(f"Recorded study pitch {session_pitch} · {speed:.1f} mph", y=0.965, fontsize=12)
    scatter = ax.scatter([], [], [], s=12, color="#0b7497", depthshade=False)
    lines = [ax.plot([], [], [], color="#294758", lw=1.7)[0] for _ in motion["links"]]
    clock = fig.text(0.08, 0.915, "", fontsize=10)
    playback_rate = fps * float(times[1] - times[0]) if len(times) > 1 else 0.0
    fig.text(
        0.5, 0.065, "Actual motion-capture animation · not camera footage", ha="center", fontsize=9
    )
    fig.text(
        0.5,
        0.045,
        f"Observed C3D skin markers · {playback_rate:g}× playback speed",
        ha="center",
        fontsize=8,
    )
    fig.text(
        0.5,
        0.025,
        "Lines connect skin markers; they are not anatomical joint centers.",
        ha="center",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.01, right=0.97, bottom=0.11, top=0.87)
    writer = FFMpegWriter(
        fps=fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "21"]
    )
    try:
        with writer.saving(fig, str(output_path), dpi=100):
            for frame, time in zip(positions, times, strict=True):
                valid = np.isfinite(frame).all(axis=1)
                scatter._offsets3d = tuple(frame[valid, dimension] for dimension in range(3))
                for line, pair in zip(lines, motion["links"], strict=True):
                    line.set_data_3d(frame[pair, 0], frame[pair, 1], frame[pair, 2])
                clock.set_text(f"Time from C3D capture start: {time:.3f} s")
                writer.grab_frame()
    finally:
        plt.close(fig)


def load_motion_manifest(path: Path) -> dict:
    """Read a small manifest, rejecting changed source identity and unsafe paths."""
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("source_commit") != COMMIT:
        raise ValueError("Unsupported motion manifest schema or source revision.")
    if manifest.get("release_tag") != RELEASE_TAG:
        raise ValueError("Motion examples must retain the reviewed dataset release.")
    archive = manifest.get("archive", {})
    if archive != {"url": ARCHIVE_URL, "sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES}:
        raise ValueError("Motion archive provenance does not match the reviewed release.")
    examples = manifest.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("Motion manifest needs at least one example.")
    identifiers = set()
    for example in examples:
        required = {
            "session_pitch",
            "user",
            "filename_new",
            "source_file_sha256",
            "animation_file",
            "animation_sha256",
            "frames_file",
            "frames_sha256",
            "poi",
        }
        if not required.issubset(example):
            raise ValueError("Motion example is missing provenance fields.")
        if example["session_pitch"] in identifiers:
            raise ValueError("Motion manifest contains duplicate pitch IDs.")
        identifiers.add(example["session_pitch"])
        for field in ("animation_file", "frames_file"):
            name = example[field]
            expected_suffix = ".mp4" if field == "animation_file" else ".npz"
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or "\\" in name
                or not name.endswith(expected_suffix)
            ):
                raise ValueError("Motion asset paths must be basenames within assets/motion.")
    return manifest


def prepare_examples(project_root: Path) -> dict:
    """Recreate three public-source-linked videos and safe numeric replay assets."""
    root = Path(project_root).resolve()
    archive_path = root / "data" / "visual-source" / ARCHIVE_NAME
    verify_archive(archive_path)
    verify_source(root / "source_manifest.json", root / "data" / "raw")
    poi, metadata = read_source(root / "data" / "raw")
    analysis, _ = join_pitching(poi, metadata)
    selected = select_example_rows(analysis)
    try:
        import ezc3d
    except ImportError as error:
        raise RuntimeError(
            "Install the optional motion environment with uv sync --extra motion."
        ) from error
    output = root / "assets" / "motion"
    source_output = root / "data" / "visual-source" / "selected"
    output.mkdir(parents=True, exist_ok=True)
    source_output.mkdir(parents=True, exist_ok=True)
    examples = []
    with zipfile.ZipFile(archive_path) as archive:
        for row in selected.to_dict(orient="records"):
            filename = str(row["filename_new"])
            member = exact_archive_member(archive, filename)
            contents = archive.read(member)
            source_path = source_output / filename
            if source_path.exists() and source_path.read_bytes() != contents:
                raise ValueError(
                    f"Preserve/remove differing local C3D before retrying: {source_path}"
                )
            source_path.write_bytes(contents)
            motion = normalize_motion(ezc3d.c3d(str(source_path)), stride=6)
            pitch = str(row["session_pitch"])
            frames_path = output / f"{pitch}.npz"
            animation_path = output / f"{pitch}.mp4"
            np.savez_compressed(
                frames_path,
                **{key: motion[key] for key in ("positions_m", "times_s", "labels", "links")},
            )
            render_motion(motion, animation_path, pitch, float(row["pitch_speed_mph"]), fps=30)
            examples.append(
                {
                    "session_pitch": pitch,
                    "user": str(row["user"]),
                    "filename_new": filename,
                    "example_role": row["example_role"],
                    "selection_target_mph": float(row["selection_target_mph"]),
                    "archive_member": member,
                    "source_file_sha256": hashlib.sha256(contents).hexdigest(),
                    "point_rate_hz": motion["point_rate_hz"],
                    "units_original": motion["units_original"],
                    "n_source_frames": motion["n_source_frames"],
                    "n_frames": motion["n_frames"],
                    "marker_labels": motion["labels"].tolist(),
                    "excluded_marker_labels": motion["excluded_marker_labels"],
                    "animation_file": animation_path.name,
                    "animation_sha256": sha256_file(animation_path),
                    "frames_file": frames_path.name,
                    "frames_sha256": sha256_file(frames_path),
                    "fps": 30,
                    "stride": 6,
                    "playback_rate": 30 * 6 / motion["point_rate_hz"],
                    "missing_points": motion["missing_points"],
                    "n_source_missing_points": motion["n_source_missing_points"],
                    "poi": {
                        key: None if pd.isna(row[key]) else float(row[key]) for key in VARIABLES
                    },
                }
            )
            print(
                f"Prepared study pitch {pitch}: {motion['n_frames']} observed-marker frames",
                flush=True,
            )
    manifest = {
        "schema_version": 1,
        "source_commit": COMMIT,
        "release_tag": RELEASE_TAG,
        "archive": {"url": ARCHIVE_URL, "sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES},
        "license_url": LICENSE_URL,
        "attribution": "Driveline Baseball Research & Development, OpenBiomechanics Project",
        "derivative_license": "CC BY-NC-SA 4.0 plus the upstream additional affiliation exclusion",
        "description": "Downsampled observed C3D skin markers, converted to meters and rendered as video.",
        "time_reference": "Seconds from each C3D capture start; no full-signal event alignment inferred.",
        "missing_policy": "Negative/nonfinite residuals and nonfinite coordinates remain NaN; no interpolation.",
        "examples": examples,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return load_motion_manifest(manifest_path)
