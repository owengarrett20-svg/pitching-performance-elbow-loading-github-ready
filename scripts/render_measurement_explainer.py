"""Render an original 15-second instructional schematic, not measured motion.

Run from the project root:
    uv run python scripts/render_measurement_explainer.py

Requires ffmpeg on PATH; all other dependencies are in the project environment.
No motion-capture trajectories, human footage, or external images are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Arc, Circle, FancyArrowPatch

from pitching.measurement_lessons import COMMIT, SOURCE_LINKS

BACKGROUND = "#0b1426"
PANEL = "#16253e"
TEXT = "#f4f7ff"
MUTED = "#b8c8e0"
TEAL = "#56dcc4"
ORANGE = "#ffb86b"
LABEL = "Instructional schematic — not measured pitch data"


def point(angle, radius=0.24, center=(0.27, 0.48)):
    return np.asarray(center) + radius * np.array([np.cos(angle), np.sin(angle)])


def ray(ax, angle, *, radius=0.24, color=TEAL, center=(0.27, 0.48), double=False):
    endpoint = point(angle, radius, center)
    start = point(angle + np.pi, radius, center) if double else np.asarray(center)
    ax.plot(
        [start[0], endpoint[0]], [start[1], endpoint[1]], color=color, lw=7, solid_capstyle="round"
    )


def text_block(ax, x, y, lines, size=18, color=TEXT, step=0.065):
    for index, line in enumerate(lines):
        ax.text(x, y - index * step, line, color=color, fontsize=size, va="top")


def draw_frame(fig, time):
    fig.clear()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(0.045, 0.955, LABEL, color=ORANGE, fontsize=15, weight="bold", va="top")
    chapter = min(int(time // 5), 2)
    progress = (time - chapter * 5) / 5
    titles = [
        "1. Separation is a relative orientation",
        "2. Rotation speed is change over time",
        "3. Joint loading needs a dynamics model",
    ]
    ax.text(0.045, 0.87, titles[chapter], fontsize=25, color=TEXT, weight="bold", va="top")
    ax.axvline(0.49, ymin=0.24, ymax=0.78, color=PANEL, lw=2)

    if chapter == 0:
        pelvis = np.deg2rad(8 + 14 * np.sin(np.pi * progress))
        thorax = pelvis + np.deg2rad(12 + 38 * np.sin(np.pi * progress) ** 2)
        ray(ax, pelvis, color=TEAL, double=True)
        ray(ax, thorax, color=ORANGE, double=True)
        ax.add_patch(
            Arc(
                (0.27, 0.48),
                0.25,
                0.25,
                theta1=np.rad2deg(pelvis),
                theta2=np.rad2deg(thorax),
                color=TEXT,
                lw=2,
            )
        )
        ax.add_patch(Circle((0.27, 0.48), 0.015, color=TEXT))
        text_block(ax, 0.07, 0.73, ["Top-down planar illustration"], size=15, color=MUTED)
        ax.text(0.06, 0.28, "Pelvis", color=TEAL, fontsize=18)
        ax.text(0.28, 0.28, "Thorax", color=ORANGE, fontsize=18)
        text_block(
            ax,
            0.54,
            0.71,
            [
                "Compare thorax and pelvis frames.",
                "In 3D, use a relative rotation",
                "and the defined axial component.",
            ],
            size=18,
        )
        ax.text(
            0.54,
            0.44,
            r"$R_{\mathrm{relative}} = R_{\mathrm{pelvis}}^{T} R_{\mathrm{thorax}}$",
            color=TEAL,
            fontsize=21,
        )
        text_block(
            ax,
            0.54,
            0.34,
            ["Peak separation and separation", "at foot plant are different measures."],
            size=17,
            color=MUTED,
        )
        footer = "A projected camera angle is not automatically the source's 3D separation."
    elif chapter == 1:
        theta = np.deg2rad(20 + 125 * progress)
        ax.add_patch(Circle((0.27, 0.48), 0.21, fill=False, ec=PANEL, lw=3))
        ray(ax, theta, radius=0.20)
        ax.add_patch(
            Arc((0.27, 0.48), 0.31, 0.31, theta1=20, theta2=np.rad2deg(theta), color=ORANGE, lw=3)
        )
        ax.add_patch(Circle((0.27, 0.48), 0.015, color=TEXT))
        ax.text(0.07, 0.73, "One planar rotation only", fontsize=16, color=MUTED)
        ax.text(
            0.08,
            0.25,
            r"$\omega_{\mathrm{planar}}\approx\Delta\theta/\Delta t$",
            color=TEAL,
            fontsize=23,
        )
        plot = fig.add_axes([0.59, 0.45, 0.32, 0.24], facecolor=BACKGROUND)
        demo_times = np.linspace(0, 1, 80)
        plot.plot(demo_times, 20 + 125 * demo_times, color=TEAL, lw=3)
        plot.scatter([progress], [20 + 125 * progress], s=70, color=ORANGE, zorder=3)
        plot.set(xlim=(0, 1), ylim=(0, 160), xlabel="Illustration time", ylabel="Angle")
        plot.tick_params(colors=MUTED, labelsize=11)
        plot.xaxis.label.set_color(MUTED)
        plot.yaxis.label.set_color(MUTED)
        for spine in plot.spines.values():
            spine.set_color(PANEL)
        text_block(
            ax,
            0.54,
            0.36,
            [
                "Slope connects angle and time.",
                "3D shoulder/torso rates require",
                "the full coordinate conventions.",
            ],
            size=17,
            color=MUTED,
        )
        footer = (
            "Euler-coordinate derivatives do not generally equal 3D angular-velocity components."
        )
    else:
        angle = np.deg2rad(12 + 12 * np.sin(2 * np.pi * progress))
        origin = (0.11, 0.42)
        endpoint = point(angle, 0.30, origin)
        center = (np.asarray(origin) + endpoint) / 2
        ax.plot(
            [origin[0], endpoint[0]],
            [origin[1], endpoint[1]],
            lw=13,
            color=TEAL,
            solid_capstyle="round",
        )
        ax.add_patch(Circle(origin, 0.025, color=ORANGE))
        ax.add_patch(Circle(center, 0.012, color=TEXT, zorder=4))
        ax.add_patch(
            FancyArrowPatch(
                (endpoint[0], endpoint[1] + 0.15),
                endpoint,
                arrowstyle="-|>",
                mutation_scale=25,
                lw=2,
                color=ORANGE,
            )
        )
        ax.add_patch(
            FancyArrowPatch(
                (0.07, 0.51),
                (0.16, 0.56),
                connectionstyle="arc3,rad=-0.65",
                arrowstyle="-|>",
                mutation_scale=25,
                lw=2,
                color=ORANGE,
            )
        )
        ax.text(0.065, 0.71, "Generic rigid segment", color=MUTED, fontsize=17)
        ax.text(0.075, 0.32, "Joint reaction", color=ORANGE, fontsize=16)
        ax.text(0.29, 0.68, "External force", color=ORANGE, fontsize=15)
        text_block(
            ax,
            0.54,
            0.71,
            [
                "Combine motion + external forces",
                "with segment mass and inertia.",
                "Solve net force/moment balances.",
            ],
            size=18,
        )
        ax.text(
            0.52,
            0.43,
            r"$\sum M_{\mathrm{COM}}=I\alpha+\omega\times(I\omega)$",
            fontsize=20,
            color=TEAL,
        )
        text_block(
            ax,
            0.54,
            0.33,
            ["Net elbow moment is not UCL force", "and does not predict injury."],
            size=17,
            color=MUTED,
        )
        footer = "Conceptual balance about the center of mass; not the complete OBP inverse-dynamics model."

    ax.text(0.045, 0.13, footer, color=MUTED, fontsize=14, va="top")
    ax.text(
        0.045,
        0.062,
        "Original diagrams · Definitions adapted from Driveline's OpenBiomechanics Project",
        color=MUTED,
        fontsize=12,
        va="top",
    )
    ax.plot([0.045, 0.955], [0.022, 0.022], color=PANEL, lw=4)
    ax.plot([0.045, 0.045 + 0.91 * time / 15], [0.022, 0.022], color=TEAL, lw=4)
    return fig


def render(output: Path, fps: int = 24):
    if fps < 1:
        raise ValueError("FPS must be positive.")
    if not FFMpegWriter.isAvailable():
        raise RuntimeError("ffmpeg is required on PATH to render the instructional video.")
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": BACKGROUND})
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BACKGROUND)
    metadata = {
        "title": "How pitching measures are computed: an instructional schematic",
        "artist": "Pitching Performance and Elbow Loading project",
        "comment": LABEL + ". No measured pitch data or human footage used.",
    }
    writer = FFMpegWriter(
        fps=fps,
        codec="libx264",
        metadata=metadata,
        extra_args=["-pix_fmt", "yuv420p", "-crf", "22", "-movflags", "+faststart"],
    )
    with writer.saving(fig, str(output), dpi=100):
        for frame in range(15 * fps):
            draw_frame(fig, frame / fps)
            writer.grab_frame(facecolor=BACKGROUND)
    draw_frame(fig, 2.5)
    poster = output.with_suffix(".jpg")
    fig.savefig(poster, dpi=100, facecolor=BACKGROUND)
    plt.close(fig)
    manifest = {
        "artifact": output.name,
        "poster": poster.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "bytes": output.stat().st_size,
        "duration_seconds": 15,
        "fps": fps,
        "resolution": [1280, 720],
        "type": "original_instructional_schematic",
        "contains_measured_pitch_data": False,
        "contains_athlete_footage": False,
        "on_every_frame": LABEL,
        "chapters": [
            {"start_seconds": 0, "end_seconds": 5, "title": "Relative orientation"},
            {"start_seconds": 5, "end_seconds": 10, "title": "Planar angle-time derivative"},
            {"start_seconds": 10, "end_seconds": 15, "title": "Rigid-segment dynamics concept"},
        ],
        "attribution": "Definitions adapted from Driveline Baseball Research & Development's "
        "OpenBiomechanics Project. Diagrams and pedagogical text are original project adaptations.",
        "source_commit": COMMIT,
        "sources": SOURCE_LINKS,
        "documentation_license": "CC BY-NC-SA 4.0 with upstream additional professional-sports / "
        "financial-analysis affiliation restriction; see the pinned data/documentation license.",
        "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "render_command": "uv run python scripts/render_measurement_explainer.py",
    }
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Rendered {output} ({output.stat().st_size:,} bytes), poster, and manifest.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("assets/lessons/measurement_explainer.mp4")
    )
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    render(args.output, args.fps)
