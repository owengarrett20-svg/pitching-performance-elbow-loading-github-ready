# How the measures are computed — instructional schematic

`measurement_explainer.mp4` is an original 15-second silent teaching animation.
It explains three concepts: relative segment orientation, a planar angle–time
derivative, and a rigid-segment moment balance. **Every frame says
“Instructional schematic — not measured pitch data.”** It is not a simulated
pitch, a measured OBP trajectory, a validated motion-reconstruction system, or
athlete footage. The schematic uses hand-drawn generic segments and analytic
teaching motions; no pose-estimation or video-analysis results are claimed.

The real OBP motion-capture examples in this project's viewer are separate
assets with their own provenance. A rendered marker trajectory is a
visualization of measurements, not a synchronized camera recording. No MLB
footage or other human footage is used in this animation.

## Reproduce

From the project root, with the frozen environment installed and ffmpeg on PATH:

```sh
uv run python scripts/render_measurement_explainer.py
```

Only existing Python dependencies (`numpy`, `matplotlib`) and ffmpeg are used.
The command creates the MP4, a JPEG poster, and a JSON provenance manifest.
The default render is 1,280 × 720, 24 frames/s, 15 seconds, H.264/yuv420p for
browser compatibility. Encoding may vary with ffmpeg/platform versions; the
manifest records the actual output hash rather than promising identical bytes.

## Interpretation

- The top-down two-line orientation illustrates a planar special case. The
  source hip–shoulder separation is a component of a defined 3D thorax–pelvis
  orientation; camera-plane shoulder and hip lines are not automatically that
  quantity. Peak separation and separation at foot plant are different POIs.
- The derivative is for one unwrapped planar angle. Euler-coordinate derivatives
  do not generally equal components of 3D angular velocity. This script does not
  reproduce OBP shoulder or torso rotational velocities.
- The moment equation is a general rigid-segment balance about its center of
  mass. External forces and their moment arms and joint reaction terms belong
  in the summed moments. It does not specify every term, coordinate transform,
  transport operation, or algorithm in OBP's inverse-dynamics pipeline.
- An internal net elbow varus moment is not a direct UCL force, ligament stress,
  or injury-probability measurement. Visible posture alone cannot supply it.
- Pitch speed is a recorded POI. Complete instrument and speed-protocol details
  are not established here; we do not claim a particular radar procedure.

## Attribution and terms

Definitions and conventions are adapted from **Driveline Baseball Research &
Development, The OpenBiomechanics Project**, pinned to commit
`44b98dae05cceb016f080ab39d105c85b8639084`:

- [Pitching definitions and conventions](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/README.md)
- [CSV data dictionary](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/data/data_dictionary.csv)
- [Pinned data and documentation license](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md)

Changes: original explanatory text, hand-drawn diagrams, conceptual equations,
and animation; no measured motion data appear in this schematic. These adapted
teaching/documentation assets are shared under the upstream data/documentation
terms: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) with
the upstream additional restriction on use by employees, contractors,
associates, or significant shareholders of professional sports organizations
or financial-analysis firms without a specific written paid license. Review
the full pinned terms before reuse; this attribution does not imply endorsement.
The renderer's software is covered by the project's software license.
