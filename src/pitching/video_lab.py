"""A local, integrity-checked viewer for OBP motion and measurement explanations.

Marker animations represent measured three-dimensional skin-marker positions.
They are not camera footage, pose-estimation results, or reconstructions of
joint loading. Rendering this module never downloads data or fits a model.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

SOURCE_COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
SOURCE_BASE = f"https://github.com/drivelineresearch/openbiomechanics/blob/{SOURCE_COMMIT}"
CAMERA_VIEW = "https://drive.google.com/file/d/1sa2wrKhEHXsEvM59PQdixIDVa_e5QEDI/view"
CAMERA_PREVIEW = "https://drive.google.com/file/d/1sa2wrKhEHXsEvM59PQdixIDVa_e5QEDI/preview"


class MotionAssetError(ValueError):
    """A local asset is missing, untrusted, or inconsistent with its manifest."""


def _local_asset(directory: Path, filename: str, suffix: str) -> Path:
    """Require a basename and reject symlinks resolving outside the asset directory."""
    if (
        not isinstance(filename, str)
        or not filename
        or "/" in filename
        or "\\" in filename
        or Path(filename).name != filename
        or Path(filename).suffix.lower() != suffix
    ):
        raise MotionAssetError(f"Expected a local {suffix} asset basename.")
    resolved = (directory / filename).resolve()
    if not resolved.is_relative_to(directory.resolve()):
        raise MotionAssetError("The motion asset resolves outside its expected directory.")
    return resolved


def verified_asset(directory: Path, filename: str, expected_sha256: str, suffix: str) -> Path:
    """Verify bytes before a local media or array file reaches a renderer."""
    path = _local_asset(directory, filename, suffix)
    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_sha256
    ):
        raise MotionAssetError("The motion asset has no valid SHA-256 checksum.")
    try:
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
    except OSError as error:
        raise MotionAssetError(f"Local asset {filename} is unavailable.") from error
    if digest != expected_sha256.lower():
        raise MotionAssetError(f"Checksum mismatch for {filename}; it will not be displayed.")
    return path


def load_motion_manifest(project_root: Path) -> tuple[Path, dict[str, Any]]:
    """Read the pinned, versioned local manifest without initiating a download."""
    root = Path(project_root).resolve()
    directory = (root / "assets" / "motion").resolve()
    if not directory.is_relative_to(root):
        raise MotionAssetError("The motion directory resolves outside the project.")
    manifest_path = _local_asset(directory, "manifest.json", ".json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MotionAssetError(
            "Prepared OBP marker animations are not available locally."
        ) from error
    if not isinstance(manifest, dict):
        raise MotionAssetError("The motion manifest must contain an object.")
    if manifest.get("schema_version", manifest.get("schema")) != 1:
        raise MotionAssetError("The motion manifest has an unsupported schema version.")
    if manifest.get("source_commit") != SOURCE_COMMIT:
        raise MotionAssetError("The motion manifest does not match the pinned OBP revision.")
    entries = manifest.get("examples")
    if not isinstance(entries, list) or not entries:
        raise MotionAssetError("The motion manifest does not list any prepared examples.")
    identifiers = set()
    for entry in entries:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(name), str) or not entry[name]
            for name in ("session_pitch", "user", "filename_new")
        ):
            raise MotionAssetError("A motion example is missing its source identifiers.")
        if entry["session_pitch"] in identifiers:
            raise MotionAssetError("The motion manifest contains duplicate pitch identifiers.")
        identifiers.add(entry["session_pitch"])
        for name in ("point_rate_hz", "playback_rate"):
            value = entry.get(name)
            if not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
                raise MotionAssetError(f"A motion example has an invalid {name}.")
        for name in ("n_source_frames", "n_frames"):
            if type(entry.get(name)) is not int or entry[name] < 1:
                raise MotionAssetError(f"A motion example has an invalid {name}.")
        if not isinstance(entry.get("poi"), dict):
            raise MotionAssetError("A motion example is missing its source POI metadata.")
    return directory, manifest


def matching_examples(frame: pd.DataFrame, examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match *both* pitch and athlete; never substitute another athlete's motion."""
    if not {"session_pitch", "user"}.issubset(frame.columns):
        return []
    pairs = {
        (str(pitch), str(user))
        for pitch, user in frame[["session_pitch", "user"]].itertuples(index=False, name=None)
        if pd.notna(pitch) and pd.notna(user)
    }
    return [entry for entry in examples if (entry["session_pitch"], entry["user"]) in pairs]


def load_marker_frames(path: Path, expected_n_frames: int | None = None) -> dict[str, np.ndarray]:
    """Load only numeric arrays and Unicode labels; never interpolate missing markers."""
    try:
        with np.load(path, allow_pickle=False) as source:
            arrays = {
                name: source[name].copy() for name in ("positions_m", "times_s", "labels", "links")
            }
    except (OSError, ValueError, KeyError) as error:
        raise MotionAssetError("The marker frame archive is unreadable or unsafe.") from error
    positions, times = arrays["positions_m"], arrays["times_s"]
    labels, links = arrays["labels"], arrays["links"]
    if positions.ndim != 3 or positions.shape[2] != 3 or not positions.shape[0]:
        raise MotionAssetError("Marker positions must have shape [frames, markers, 3].")
    if not np.issubdtype(positions.dtype, np.number) or np.isinf(positions).any():
        raise MotionAssetError(
            "Marker coordinates must be numeric, with missing values kept as NaN."
        )
    if expected_n_frames is not None and positions.shape[0] != expected_n_frames:
        raise MotionAssetError("The marker frame count does not match the manifest.")
    if (
        times.ndim != 1
        or times.shape[0] != positions.shape[0]
        or not np.issubdtype(times.dtype, np.number)
        or not np.isfinite(times).all()
        or np.any(np.diff(times) <= 0)
    ):
        raise MotionAssetError("Marker times must be finite and strictly increasing.")
    if labels.ndim != 1 or len(labels) != positions.shape[1] or labels.dtype.kind != "U":
        raise MotionAssetError("Marker labels must be a matching Unicode array.")
    if (
        links.ndim != 2
        or links.shape[1] != 2
        or not np.issubdtype(links.dtype, np.integer)
        or (links < 0).any()
        or (links >= positions.shape[1]).any()
    ):
        raise MotionAssetError("Marker links contain invalid marker indices.")
    return arrays


def marker_frame_plot(arrays: dict[str, np.ndarray], index: int):
    """Plot measured markers and guide links, omitting endpoints absent in this frame."""
    import matplotlib.pyplot as plt

    positions = arrays["positions_m"][index]
    valid = np.isfinite(positions).all(axis=1)
    fig = plt.figure(figsize=(7, 6), layout="constrained")
    axis = fig.add_subplot(projection="3d")
    if valid.any():
        axis.scatter(*positions[valid].T, s=14, color="#168AAD", label="Measured skin markers")
        for first, second in arrays["links"]:
            if valid[first] and valid[second]:
                segment = positions[[first, second]]
                axis.plot(*segment.T, color="#46647D", linewidth=1)
        low, high = positions[valid].min(axis=0), positions[valid].max(axis=0)
        middle = (low + high) / 2
        radius = max(float((high - low).max()) / 2, 0.25)
        axis.set_xlim(middle[0] - radius, middle[0] + radius)
        axis.set_ylim(middle[1] - radius, middle[1] + radius)
        axis.set_zlim(middle[2] - radius, middle[2] + radius)
    else:
        axis.text2D(0.1, 0.5, "No complete markers in this frame", transform=axis.transAxes)
    axis.set(xlabel="Source X (m)", ylabel="Source Y (m)", zlabel="Source Z (m)")
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=15, azim=-60)
    axis.set_title(
        f"{arrays['times_s'][index]:.3f} s from C3D start; {valid.sum()} visible markers"
    )
    return fig


def _example_label(entry: dict[str, Any]) -> str:
    speed = entry.get("poi", {}).get("pitch_speed_mph")
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        speed = float("nan")
    suffix = f" · {speed:.1f} mph" if np.isfinite(speed) else " · speed unavailable"
    return f"Pitch {entry['session_pitch']} · athlete {entry['user']}{suffix}"


def _render_motion(frame: pd.DataFrame, project_root: Path) -> str | None:
    st.subheader("See a recorded study pitch in 3D")
    st.caption(
        "These animations show measured OBP skin markers from a source C3D trial. "
        "They contain no camera footage or estimated video pose. Guide links connect markers; "
        "they are not a validated joint-center or skeletal model."
    )
    try:
        directory, manifest = load_motion_manifest(project_root)
    except MotionAssetError as error:
        st.info(str(error))
        st.caption(
            "The other dashboard analyses remain available. No asset is downloaded on rerun."
        )
        return None
    entries = matching_examples(frame, manifest["examples"])
    if not entries:
        identifiers = ", ".join(entry["session_pitch"] for entry in manifest["examples"])
        st.info(
            f"Motion is prepared for only {len(manifest['examples'])} study pitches "
            f"({identifiers}). None matches both pitch and athlete in the current sidebar filters. "
            "Clear or change the sidebar athlete/playing-level filters to view a prepared example."
        )
        return None
    chosen = st.selectbox(
        "Recorded study pitch",
        entries,
        format_func=_example_label,
        key="motion_study_pitch",
    )
    try:
        movie = verified_asset(
            directory,
            chosen.get("animation_file"),
            chosen.get("animation_sha256"),
            ".mp4",
        )
        archive = verified_asset(
            directory, chosen.get("frames_file"), chosen.get("frames_sha256"), ".npz"
        )
        arrays = load_marker_frames(archive, chosen["n_frames"])
    except MotionAssetError as error:
        st.warning(f"This motion example cannot be displayed: {error}")
        return None
    st.video(str(movie), format="video/mp4")
    st.caption(
        f"Source marker sampling: {chosen['point_rate_hz']:g} Hz · "
        f"{chosen['n_source_frames']} source frames · "
        f"{chosen['n_frames']} rendered frames · "
        f"playback at {chosen['playback_rate']:g}× recorded speed."
    )
    st.caption(
        f"Pitch {chosen['session_pitch']} · pseudonymous athlete {chosen['user']} · "
        f"source file {chosen['filename_new']}. "
        "Frame time is relative to the C3D start. Its alignment with processed signal/event "
        "times has not been verified, so this viewer does not synchronize those traces or events."
    )
    with st.expander("Inspect a paused marker frame"):
        if st.checkbox("Show frame inspector", key="motion_inspect"):
            index = (
                st.slider(
                    "Rendered frame index",
                    0,
                    len(arrays["times_s"]) - 1,
                    0,
                    key=f"motion_frame_{chosen['session_pitch']}",
                )
                if len(arrays["times_s"]) > 1
                else 0
            )
            fig = marker_frame_plot(arrays, index)
            st.pyplot(fig, width="stretch")
            import matplotlib.pyplot as plt

            plt.close(fig)
            st.caption(
                "Coordinates remain in the source global frame. Missing markers and links with "
                "missing endpoints are omitted; no missing positions are filled in."
            )
    st.markdown(
        f"[Pinned OBP pitching methods and conventions]({SOURCE_BASE}/baseball_pitching/README.md)"
    )
    return chosen["session_pitch"]


def _render_camera_example() -> None:
    st.subheader("Watch a separate official camera example")
    st.write(
        "OBP-CV includes a 62.7 mph pitching demonstration. This is a separate source example: "
        "there is no verified mapping to the 411 POI study pitches, so no study metrics or "
        "model errors are paired with this clip. No video-analysis accuracy is claimed."
    )
    st.markdown(f"[Open the official OBP-CV camera example]({CAMERA_VIEW})")
    st.caption(
        f"Official provenance: [OBP-CV source collection documentation]({SOURCE_BASE}/computer_vision/calibration/README.md) "
        f"and [source video IDs in the upstream fetcher]({SOURCE_BASE}/computer_vision/4d_reconstruction/obp4d/fetch.py)."
    )
    if st.checkbox("Load official camera example", value=False, key="motion_load_camera"):
        import streamlit.components.v1 as components

        components.iframe(CAMERA_PREVIEW, height=430, scrolling=False)
        st.caption(
            "Playback is hosted by the source on Google Drive and depends on its sharing "
            "permissions and your connection. If the embed is unavailable, use the source link."
        )


def _render_measurement_lessons(project_root: Path) -> None:
    st.subheader("How the five measurements are computed")
    st.caption(
        "A visible movement can explain a measurement concept, but its quantitative estimate "
        "depends on calibration, coordinate conventions, instruments, and processing."
    )
    lesson_dir = Path(project_root) / "assets/lessons"
    try:
        video_manifest = json.loads((lesson_dir / "measurement_explainer.json").read_text())
        if video_manifest.get("source_commit") != SOURCE_COMMIT:
            raise MotionAssetError("The instructional video cites a different source revision.")
        movie = verified_asset(
            lesson_dir, video_manifest["artifact"], video_manifest["sha256"], ".mp4"
        )
        st.video(str(movie), format="video/mp4")
        st.caption(
            "15-second instructional animation: relative orientation → angle/time slope → "
            "rigid-segment moment balance. The diagrams contain no measured athlete data or camera footage."
        )
    except (OSError, ValueError, KeyError):
        st.caption(
            "The optional instructional video is unavailable; the source-cited lessons remain below."
        )
    try:
        from pitching.measurement_lessons import LESSONS
    except ImportError:
        st.info("Measurement teaching notes are not available in this project copy.")
        return
    variable = st.selectbox(
        "Measurement to explain",
        list(LESSONS),
        format_func=lambda name: LESSONS[name]["title"],
        key="motion_lesson",
    )
    lesson = LESSONS[variable]
    st.markdown(f"**{lesson['title']} ({lesson['unit']})**")
    st.caption(f"Source POI column: {variable}")
    for index, step in enumerate(lesson["steps"], start=1):
        st.write(f"{index}. {step}")
    st.latex(lesson["formula"])
    st.markdown(f"**What you can see:** {lesson['can_see']}")
    st.markdown(f"**What measurement requires:** {lesson['instrument_requirements']}")
    st.markdown(f"**Interpretation limits:** {lesson['limits']}")
    st.caption(
        "Elbow varus moment is an internal net joint moment, not an injury probability or a "
        "direct measurement of ligament loading. Individual peak summaries do not establish "
        "the timing of a kinetic sequence."
    )


def render_video_lab(frame: pd.DataFrame, project_root: Path) -> str | None:
    """Render the OBP-only teaching tab; return the successfully displayed study pitch ID."""
    selected = _render_motion(frame, project_root)
    _render_camera_example()
    _render_measurement_lessons(project_root)
    return selected
