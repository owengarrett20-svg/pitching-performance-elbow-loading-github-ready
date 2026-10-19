# Watch pitches and understand the measurements

The **Watch pitches** dashboard tab adds three different visual resources. They are deliberately labeled by what they actually contain.

## 1. Recorded study motion from measured markers

Three sample pitches come from the canonical `dataset-v1/pitching_c3d.zip` release. The complete archive is checked against the SHA-256 in the pinned upstream `scripts/release_checksums.sha256` before extracting any selected file. The filename is matched exactly to `metadata.filename_new`; pitch identity is not guessed from a filename suffix.

| Study pitch ID | Athlete ID | Recorded speed | Source frames | Displayed frames |
| --- | --- | ---: | ---: | ---: |
| `1393_3` | `919` | 69.5 mph | 540 | 90 |
| `1623_3` | `970` | 85.3 mph | 806 | 135 |
| `2916_4` | `1596` | 94.4 mph | 406 | 68 |

These are deterministic examples near the source minimum, median, and maximum speed, with distinct athletes. They are useful illustrations, not a representative sample or a comparison study of three pitching techniques.

The actual C3D files report marker coordinates in **meters at 360 Hz**. Display samples take every sixth source frame and are encoded at 30 fps, producing **0.5× playback speed**. A paused-frame inspector shows the measured coordinates. Connecting lines are visual guides between skin markers, not anatomical joint centers or an independently validated skeleton.

The original capture contains skin markers and may contain non-body channels. The renderer explicitly selects known body-marker names and records excluded labels. Missing coordinates and negative/nonfinite residuals remain missing; nothing is interpolated. Importantly, ezc3d's fourth `points` row is homogeneous coordinates here; residual validity is read from `data.meta_points.residuals`. The bundled NPZ arrays load with `allow_pickle=False`.

Manifest: `assets/motion/manifest.json`. Each entry records exact source filename/member, source/derived hashes, unit/rate/frame counts, selection rule, marker labels, and published POI values. The viewer requires both athlete and pitch to match the sidebar selection. If none of the three prepared pitches matches a filter, it says so instead of substituting another athlete's motion.

## 2. Real processed signals and scalar summaries

`assets/traces/` contains thin extracts from the same selected pitch IDs in the canonical joint-angle, joint-velocity, and force/moment archives. Every archive is SHA-256 checked against the pinned release manifest. Tables must have one-to-one `session_pitch` + `time` coverage and agreeing event metadata; mismatches raise an error rather than silently dropping frames.

| Published POI | Released signal shown | Display operation |
| --- | --- | --- |
| Peak hip–shoulder separation | `torso_pelvis_angle_z` | Retain original degrees |
| Peak shoulder internal rotation velocity | `shoulder_velo_z` | Retain original deg/s and sign; see note below |
| Peak torso rotation velocity | `torso_velo_z` | Retain original deg/s |
| Peak internal elbow varus moment | `elbow_moment_y` | Retain original N·m, varus-positive |

The viewer reports the published POI alongside a simple maximum over the finite samples in the user-selected interval. All four whole-trace maxima agree with the published values in the three prepared examples. This is a numerical source comparison, **not independent validation of the complete original processing or inverse-dynamics model**. Changing the interval demonstrates why a phase-specific peak need not equal a full-trial maximum. No full-signal ball trajectory is supplied, so recorded pitch speed remains a source POI rather than a video-derived estimate.

**Shoulder convention ambiguity:** The generic upstream kinematic table labels shoulder external rotation positive/internal negative, but the positive maximum of the released `shoulder_velo_z` matches the named internal-rotation POI for all three examples. Negating that trace on the basis of the angle label would give different values. This project keeps the released trace unchanged and states the ambiguity. It does not claim that a differentiated Euler-angle coordinate, or an undocumented sign adjustment, reproduces the upstream rotational-velocity calculation.

Foot-contact and foot-plant markers retain the source definitions: 10% and 100% body weight, respectively. The plot also marks maximum external rotation, ball release, and maximum internal rotation. Velocity/moment edge gaps remain missing.

**Clock boundary:** Marker animations use time relative to their C3D start. Signal plots use original processed CSV times. Both are linked to the same pitch by metadata, but their frame-to-event alignment has not been independently established here. The app does not synchronize them or identify an animation frame as ball release. Camera recordings below are separate again.

## 3. A separate official camera recording

The pinned OBP-CV sources link a real **62.7 mph** `OBP_movement_BaseballThrow_001` demonstration from several cameras. Camera 19 is available through the [official source link](https://drive.google.com/file/d/1sa2wrKhEHXsEvM59PQdixIDVa_e5QEDI/view).

References establishing that link:

- [OBP-CV calibration documentation](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/computer_vision/calibration/README.md)
- [Official reconstruction fetcher listing source IDs](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/computer_vision/4d_reconstruction/obp4d/fetch.py)
- [Reconstruction scope and limitations](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/computer_vision/4d_reconstruction/README.md)

There is **no verified crosswalk from this recording to the 411 POI study pitches**. Their source speeds range from 69.5 to 94.4 mph, and none has 62.7 mph in metadata. The dashboard never overlays a selected study pitch's metrics or model errors on this camera recording.

The optional embed requests Google Drive only when the user enables **Load official camera example**. Availability depends on the source's sharing settings and the user's connection. In the cloud development environment, Google Drive downloads were blocked; the official references were checked, but camera playback itself was not inspected or validated. Use the direct source link if an embed does not load. No camera recording is downloaded into the project or repackaged, and no MLB footage is scraped.

## 4. A short teaching animation and source-cited lessons

The 15-second `assets/lessons/measurement_explainer.mp4` is an **original instructional schematic**, labeled on every frame as not measured pitch data. It illustrates relative segment orientation, an angle–time slope, and a rigid-segment moment balance. It contains no athlete footage and no synthesized observations inserted into the dataset.

The five selectable lessons explain what each POI means, what can be seen visually, what instrumentation/modeling is needed, and what cannot be inferred. In particular:

- Ball speed is not shoulder angular velocity, and an uncalibrated camera does not provide a valid 3D ball-speed measurement.
- Peak hip–shoulder separation differs from separation at foot plant; a projected shoulder/hip line angle is not automatically the source's 3D angle.
- Three-dimensional angular velocity is generally not a vector of Euler-angle derivatives. Sampling, filtering, frame choice, and sign conventions affect peak values.
- Elbow varus moment requires a dynamics model with appropriate motion, external forces, segment inertias, and time alignment. A visible elbow angle alone does not measure it.
- Internal net moment is not tissue-specific UCL force, injury probability, or a demonstrated safe threshold.

The planar derivative helper exists solely for the labeled schematic. It unwraps angles, checks strictly increasing time, and refuses missing values rather than silently repairing them. It is not a new OBP biomechanics pipeline.

## Rebuild and validate

Prebuilt visual assets are included in the normal project download. **Windows dashboard users do not need FFmpeg, ezc3d, or the large source archives to watch them.** The standard `uv sync --frozen --extra dev` is sufficient.

To regenerate motion examples, separately obtain and retain the official archives in ignored `data/visual-source/`. Their URLs, sizes, and expected hashes are recorded in the visual manifests; do not alter expected hashes to accept an unknown file. First run the normal `pitching fetch` so the pinned POI/metadata source cache is available. Then:

```bash
# Rebuilding only: requires a native FFmpeg executable on PATH.
uv sync --frozen --extra dev --extra motion
uv run --frozen --extra motion python scripts/prepare_motion_examples.py
uv run --frozen python scripts/prepare_trace_examples.py
uv run --frozen python scripts/render_measurement_explainer.py
```

The three trace archives plus C3D archive total about 345 MB compressed. They are not committed or included in the small update ZIP. Rebuilding does not fetch camera footage, run pose estimation, or rerun inverse dynamics.

Tests verify unit conversion, residual-based missingness, exact metadata links, asset integrity, safe NPZ structure, filtered-athlete behavior, planar teaching derivatives, trace-key cardinality and sign preservation, interval-dependent peaks, and the three examples' published-value comparisons. Original Phase 1 modeling tests remain in place.

## Attribution and terms

The observed C3D trajectories, released processed traces, biomechanics definitions, and their derivatives are credited to **Driveline Baseball Research & Development, OpenBiomechanics Project**, source commit `44b98dae05cceb016f080ab39d105c85b8639084`, canonical release `dataset-v1`. Transformations comprise selecting three metadata-linked examples, downsampling observed markers, rendering marker links/videos, extracting source signals, and adding original pedagogical diagrams/text. These do not imply Driveline endorsement.

Data-derived material and documentation retain **CC BY-NC-SA 4.0 plus OBP's additional professional-sports/financial-analysis affiliation exclusion**. Original software remains MIT. Keep the source/asset manifests, this attribution, and the full upstream data terms with redistributed media. See [LICENSING.md](LICENSING.md) and `docs/licenses/UPSTREAM-LICENSE-DATA.md`.
