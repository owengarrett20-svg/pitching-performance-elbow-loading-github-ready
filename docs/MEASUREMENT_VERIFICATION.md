# What the measurement-reproduction audit establishes

The Phase 5 audit checks whether a transparent calculation on released processed
signals reproduces the associated published scalar point-of-interest (POI)
values. It is **source-scalar reproduction**, not independent biomechanical
validation. It does not compute a joint moment from video or skin markers.

## Data and calculation

The audit uses three existing prepared examples from Driveline Baseball Research
& Development's OpenBiomechanics Project, pinned to source revision
`44b98dae05cceb016f080ab39d105c85b8639084`:

| Recorded pitch | Pseudonymous athlete | Released processed samples |
| --- | --- | ---: |
| `1393_3` | `919` | 540 |
| `1623_3` | `970` | 806 |
| `2916_4` | `1596` | 406 |

For each example, it evaluates four released quantities:

| Published summary | Native processed column | Units |
| --- | --- | --- |
| Peak hip–shoulder separation | `torso_pelvis_angle_z` | deg |
| Named peak shoulder internal rotation velocity | `shoulder_velo_z` | deg/s |
| Peak torso axial rotation velocity | `torso_velo_z` | deg/s |
| Peak internal net elbow varus moment | `elbow_moment_y` | N·m |

The operation is the **largest finite signed sample over the whole released
trace**. It is not the largest absolute magnitude. Missing values remain missing;
an entirely missing trace yields no peak. An infinite signal sample is a failed
source check. The calculation does not reproduce the upstream filtering or
recover the original POI event window merely from the field's name.

The absolute numerical acceptance tolerance is `1e-4` in each quantity's displayed
unit. This checks consistency with the four-decimal released scalar values; it
does not represent instrument accuracy, uncertainty in joint mechanics, a
physiological threshold, or an injury-risk boundary. The full unrounded difference
is retained alongside the computed and published values.

On the actual bundled examples, all **12 checks** reproduce their published
scalars, with absolute differences of zero in the stored numerical values.
These are selected illustrations from three athletes, not independent validation
of every source pitch or a representative experiment comparing techniques.

The time-series data are not complete merely because their scalar POIs are
observed. Each prepared trace contains two missing shoulder-velocity samples,
two missing torso-velocity samples, and four missing elbow-moment samples. These
are counted explicitly and remain missing when taking the finite-sample maximum.
The prepared separation traces have no missing samples.

Recorded pitch speed is not one of the reproduced quantities: this lab does not
include the ball trajectory or instrument signal needed to reconstruct that
measurement. It remains the released source POI.

## Identity and integrity checks

Before a comparison can pass, the audit checks:

1. Nonmissing, nonempty analysis identifiers and one input row per pitch.
2. The pinned source revision and reviewed trace signal names, units, and signs.
3. Each of the three reviewed pitch IDs appears once in the trace manifest.
4. The same pitch and athlete link the analysis table, trace, and motion metadata.
5. Prepared trace bytes match their manifest checksum; the sample count and
   finite, unique, monotonic time coordinates agree with the declared coverage.
6. The matching prepared marker-array asset has its declared checksum. This
   checks the linked example asset, not a marker-to-signal clock mapping.
7. The published POI agrees between the actual analysis row, trace comparison,
   and motion metadata. Missing analysis values are never supplied from those
   duplicate metadata fields.
8. The displayed signal alias retains the reviewed native-column sign before
   its maximum is computed. A cached previous `trace_max` is not used as evidence.

Rows retain source/trace/motion manifest SHA-256 digests, the prepared trace and
marker-array digests, and the pinned source commit. `analysis_input_sha256`
identifies a deterministic CSV representation of the supplied pitch/athlete and
four measured columns, sorted by pitch with 17-digit floating-point formatting.
It is explicitly not the byte hash of the original `analysis.csv`; the parent
verified report snapshot separately binds that original file.

These hashes detect stale or corrupted files relative to the recorded manifest.
They are not signatures, independent authentication of the provider, or a legal
permission certificate. The original release-archive hashes remain in the trace
manifest, but this lightweight audit does not download or reread those archives.

## Result states and missing evidence

- **Passed:** identities and declarations agree, a finite peak is available,
  and its absolute difference is within the numerical tolerance.
- **Failed:** an identity, POI, sign, unit, signal, or numerical comparison is
  inconsistent. The audit retains the reason instead of substituting a pitch.
- **Unavailable:** an input observation, finite peak, or integrity-checked asset
  is unavailable. The check remains in the result table and cannot count as a pass.

Missing or corrupt per-pitch assets produce four explicit unavailable rows.
Structurally invalid manifests or analysis tables stop the audit. A summary's
`all_passed` requires the complete expected set of twelve distinct pitch/metric
checks; an empty, partial, duplicated, or unknown-status table cannot establish
that result.

## What remains unestablished

Agreement checks the released signal and scalar against one another. Both depend
on the provider's processing and biomechanical model, so agreement is not an
independent ground-truth comparison. This audit does not establish:

- Anatomical coordinate or joint-center validity, filtering accuracy, or the
  correctness of the provider's inverse-dynamics model.
- Exact event-specific POI windows, causal energy transfer, or the benefit of
  changing a pitcher's mechanics. A peak separation angle is not necessarily
  separation at foot plant.
- Marker/processed-signal time-origin alignment, camera synchronization, or
  video coverage for every pitch.
- Tissue-specific ligament force, injury probability, or a safe joint moment.

The source shoulder-velocity sign is retained. Its positive `shoulder_velo_z`
maximum matches the named internal-rotation POI in these examples. The generic
upstream angular-convention table does not settle the full velocity export
pipeline, and a 3D angular velocity is generally not a componentwise Euler-angle
derivative. See [MOTION_LAB.md](MOTION_LAB.md) and
[VIDEO_METHODS.md](VIDEO_METHODS.md) for these boundaries.

## Reproduce the audit

The `audit_measurement_summaries(project_root, analysis)` function reads local
public assets only and returns a per-check DataFrame. `audit_summary(rows)`
counts passed, failed, and unavailable evidence with explicit scope. It never
downloads data, fits a model, interpolates a gap, or writes a report on import.
Use a verified full-cohort report table when calling it from research materials.

```bash
uv run --frozen pytest -q tests/test_measurement_audit.py
```

Tests exercise the real twelve source comparisons and clearly labeled fault
fixtures: missing/corrupt assets, identity mismatches, partial evidence,
missing/nonfinite values, native negative magnitudes, alias sign changes,
changed numerical peaks, and unit/declaration conflicts. Test-only modifications
never enter public research observations or the prepared reference snapshot.

Source definitions, traces, and derived checks retain OBP's full data terms,
including CC BY-NC-SA 4.0 and the professional-sports/financial-analysis affiliation
exclusion. Original independently authored software is MIT. Preserve attribution
and review [LICENSING.md](LICENSING.md) and the
[pinned upstream license](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md)
before reuse.
