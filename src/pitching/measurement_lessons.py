"""Teaching notes for the five OBP POI measures, plus a planar illustration.

The illustration helper is not a reconstruction of OBP's three-dimensional
biomechanical model. Read processed POI values from the verified source tables.
"""

from __future__ import annotations

import numpy as np

COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
SOURCE_BASE = f"https://github.com/drivelineresearch/openbiomechanics/blob/{COMMIT}"
SOURCE_LINKS = {
    "Pitching definitions and conventions": f"{SOURCE_BASE}/baseball_pitching/README.md",
    "Data dictionary": f"{SOURCE_BASE}/baseball_pitching/data/data_dictionary.csv",
    "Data and documentation license": f"{SOURCE_BASE}/LICENSE-DATA.md",
}

LESSONS = {
    "pitch_speed_mph": {
        "title": "Pitch speed",
        "unit": "mph",
        "source_column": "pitch_speed_mph",
        "steps": [
            "OBP supplies a recorded speed for each pitching trial in its POI and metadata CSVs.",
            "This app reads that recorded value; it does not estimate ball speed from the animation.",
            (
                "A separate calibrated ball-tracking study would estimate displacement over elapsed "
                "time, define the measurement location, and report uncertainty."
            ),
        ],
        "formula": r"\lVert\overline{\mathbf{v}}\rVert = \frac{\lVert\Delta\mathbf{x}_{\mathrm{ball}}\rVert}"
        r"{\Delta t}\quad\mathrm{(calibrated\ tracking\ example)}",
        "can_see": "A real clip can show the throwing action and ball flight if the ball is visible. "
        "The marker animation does not provide a calibrated ball trajectory.",
        "instrument_requirements": "To compute speed from video: calibrated spatial coordinates, "
        "accurate frame times, and resolvable ball positions. Radar or another validated tracking "
        "system is a different possible measurement route; the pinned POI documentation does not "
        "give enough instrument and protocol detail to identify the exact speed measurement setup.",
        "limits": "Arm rotation speed is not ball speed. A camera-plane displacement can underestimate "
        "three-dimensional travel. An interval-average speed need not equal a reported release "
        "speed. The formula is the magnitude of interval-average velocity; average speed uses "
        "path length instead of displacement unless flight is straight. Do not treat it as a "
        "reproduction of OBP's speed protocol.",
        "sources": list(SOURCE_LINKS.values()),
    },
    "elbow_varus_moment": {
        "title": "Peak internal elbow varus moment",
        "unit": "N·m",
        "source_column": "elbow_varus_moment",
        "steps": [
            (
                "Track three-dimensional segment motion and combine it with measured external forces "
                "and a model of segment mass, center of mass, and inertia."
            ),
            (
                "An inverse-dynamics model solves the segment force and moment balances for net joint "
                "reactions. The equation shown is a rigid-segment balance about its center of mass, "
                "not OBP's complete implementation."
            ),
            (
                "Resolve the elbow moment in the model's specified frame and sign convention, then "
                "summarize its varus peak. OBP describes varus as positive and valgus as negative."
            ),
        ],
        "formula": r"\sum\mathbf{M}_{\mathrm{COM}} = \mathbf{I}_{\mathrm{COM}}"
        r"\boldsymbol{\alpha} + \boldsymbol{\omega}\times"
        r"(\mathbf{I}_{\mathrm{COM}}\boldsymbol{\omega})",
        "can_see": "You can inspect posture and timing. The size of an internal net elbow moment "
        "cannot be read directly from a visible elbow angle or from one camera view.",
        "instrument_requirements": "Three-dimensional kinematics, external forces, segment inertial "
        "parameters, model definitions, and force/marker time alignment. Force moment arms and "
        "joint reaction terms belong in the balance. OBP reports marker data at 360 Hz and force "
        "data at 1,080 Hz; their grids must not be joined as though they were identical.",
        "limits": "This is a net joint moment, not a direct measurement of UCL force, ligament "
        "stress, injury probability, or a safe threshold. The present viewer reads source POI "
        "values and does not rerun inverse dynamics. Marker motion alone is insufficient.",
        "sources": list(SOURCE_LINKS.values()),
    },
    "max_shoulder_internal_rotational_velo": {
        "title": "Peak shoulder internal rotation velocity",
        "unit": "deg/s",
        "source_column": "max_shoulder_internal_rotational_velo",
        "steps": [
            "Define the upper-arm and thorax frames using the source's anatomical model.",
            (
                "Compute their relative three-dimensional rotation and the model's shoulder "
                "rotational velocity, with its axis and sign conventions."
            ),
            (
                "Read the source's named peak without changing its sign. OBP's angle-convention "
                "table labels external rotation positive and internal rotation negative; that alone "
                "does not justify negating its exported rotational-velocity values."
            ),
        ],
        "formula": r"\boldsymbol{\omega}_{\mathrm{arm/thorax}}\ne"
        r"\begin{bmatrix}\dot\alpha&\dot\beta&\dot\gamma\end{bmatrix}^{T}"
        r"\quad\mathrm{in\ general}",
        "can_see": "The arm changes orientation relative to the torso. A single projected forearm "
        "angle does not isolate shoulder internal rotation, particularly during a fast pitch.",
        "instrument_requirements": "Time-resolved three-dimensional upper-arm and thorax "
        "orientations, a defined rotation sequence, frame conventions, and appropriate sampling "
        "and filtering. The source reports fourth-order, 20 Hz Butterworth filtering for processed "
        "marker-derived signals.",
        "limits": "A derivative of one Euler-angle coordinate is not generally a component of "
        "three-dimensional angular velocity. Camera perspective, soft-tissue artifact, and "
        "filtering affect estimates. The source's angle sign table and named internal-rotation "
        "velocity do not fully establish the velocity-processing convention. The planar teaching "
        "animation is not this measurement.",
        "sources": list(SOURCE_LINKS.values()),
    },
    "max_rotation_hip_shoulder_separation": {
        "title": "Peak hip–shoulder separation",
        "unit": "deg",
        "source_column": "max_rotation_hip_shoulder_separation",
        "steps": [
            (
                "Define three-dimensional pelvis and thorax frames, then obtain their relative "
                "orientation using the source's rotation conventions."
            ),
            (
                "Use the axial component of the torso–pelvis orientation; OBP calls separation "
                "positive and closing negative."
            ),
            (
                "Read the source's peak separation POI. Separation at foot plant is a different "
                "column, rotation_hip_shoulder_separation_fp. The source distinguishes foot contact "
                "(10% body weight) from foot plant (100% body weight)."
            ),
        ],
        "formula": r"\mathbf{R}_{\mathrm{thorax/pelvis}} = "
        r"\mathbf{R}_{\mathrm{pelvis}}^{T}\mathbf{R}_{\mathrm{thorax}}",
        "can_see": "A top-down schematic illustrates how pelvis and thorax orientations differ. "
        "The colored lines illustrate two segment headings; they are not marker measurements.",
        "instrument_requirements": "Three-dimensional segment orientation, an explicit rotation "
        "decomposition, and consistent anatomical frames. Rotation matrices in the formula map "
        "segment coordinates into the same global frame. A top-down two-dimensional difference "
        "illustrates the idea only when motion is planar.",
        "limits": "A camera projection of shoulder and hip lines is not necessarily the source's "
        "three-dimensional separation angle. A peak summary does not tell when it occurred or "
        "establish a sequence, causal mechanism, or optimal value.",
        "sources": list(SOURCE_LINKS.values()),
    },
    "max_torso_rotational_velo": {
        "title": "Peak torso axial rotation velocity",
        "unit": "deg/s",
        "source_column": "max_torso_rotational_velo",
        "steps": [
            (
                "Use time-resolved three-dimensional torso orientation with the source's segment "
                "coordinate definition."
            ),
            (
                "Use the processed torso axial rotational-velocity component. OBP labels the torso "
                "Z component as rotation toward home plate positive, away negative."
            ),
            (
                "Read the peak torso rotational-velocity POI. This app does not reconstruct that "
                "trace by differentiating a camera-plane angle."
            ),
        ],
        "formula": r"\omega_{\mathrm{planar}} \approx \frac{\Delta\theta_{\mathrm{unwrapped}}}"
        r"{\Delta t}\quad\mathrm{(teaching\ example\ only)}",
        "can_see": "The planar lesson connects a changing angle to an angle–time slope. Actual "
        "torso motion also contains tilt and lateral flexion; one projected angle omits them.",
        "instrument_requirements": "Three-dimensional orientation, reliable timestamps, an "
        "explicit segment/frame convention, and sampling/filtering suitable for rapid rotation. "
        "Differentiation amplifies noise; filtering changes the resulting peak.",
        "limits": "A derivative of an Euler-angle component is not generally the corresponding "
        "angular-velocity component. Separate peak torso, pelvis, and shoulder values need not "
        "occur together and cannot establish proximal-to-distal timing.",
        "sources": list(SOURCE_LINKS.values()),
    },
}


def angular_speed_from_planar_demo(theta_deg, time_s) -> np.ndarray:
    """Differentiate a continuous, adequately sampled *planar* teaching angle.

    Degrees/s, retaining sign; angles crossing +/-180 degrees are unwrapped.
    This assumes successive true rotations are less than 180 degrees apart.
    It is neither a three-dimensional Euler-rate conversion nor an OBP POI
    calculator. Nonuniform sample times are supported; no smoothing is hidden.
    """
    angles = np.asarray(theta_deg, dtype=float)
    times = np.asarray(time_s, dtype=float)
    if angles.ndim != 1 or times.ndim != 1 or angles.shape != times.shape or len(times) < 3:
        raise ValueError(
            "Supply matching one-dimensional angle/time arrays with at least 3 samples."
        )
    if not np.isfinite(angles).all() or not np.isfinite(times).all():
        raise ValueError("Angle and time samples must all be finite; missing values stay missing.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Time samples must be strictly increasing, with no duplicates.")
    unwrapped = np.rad2deg(np.unwrap(np.deg2rad(angles)))
    return np.gradient(unwrapped, times, edge_order=2)
