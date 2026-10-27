# Source-linked recorded-marker catalog

Phase 5 includes prepared numerical marker replays for **all 411 pitches from
100 athletes** in the released analysis cohort. These are observations from the
source C3D motion-capture files, not camera videos, estimated video poses, or
newly validated joint-center models. The original three prepared MP4 clips and
three processed-trace examples are retained separately.

## Source and exact matching

Preparation uses the existing upstream release archive:

- Release: `dataset-v1`.
- File: `pitching_c3d.zip` (184,602,895 bytes).
- SHA-256: `2f5277dc63c7f7535fa4b15310d6f38b3f3b761e572896eec529854c8c920d29`.
- [Original source archive](https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/pitching_c3d.zip).

The archive contains 511 C3D members. The released analysis has 411 unique
metadata filenames, and each resolves to exactly one archive member. The other
100 members are not added to the analysis. Filename encoding is not used as a
predictor or as a substitute for source pitch/athlete identity.

The catalog manifest binds every entry to its exact `session_pitch`, `user`,
`filename_new`, archive member, source C3D SHA-256, five released POI values,
prepared array filename, byte count, and SHA-256. The manifest also records the
analysis-table and pinned-source-manifest hashes, source release, transformation
code hashes, units, sample counts, stride, marker labels, and quality totals.

The loader checks source identity, one-to-one coverage, and POI agreement before
returning entries. The workspace matches both pitch and athlete and never
substitutes a nearby-speed pitch. A missing/corrupt selected asset remains
unavailable. Integrity hashes detect changed files; they do not certify physical
measurement accuracy or independently authenticate the study.

## What is prepared

The source files use meters and a 360 Hz marker sampling rate. Preparation
retains every sixth source sample, producing a 60 Hz display grid while keeping
the original sample count and rate in the metadata. There are 247,709 source
frames and 41,462 retained display frames across the 411 recordings. Numerical
coordinates remain float64; there is no rounding, filtering, interpolation, or
new reconstruction. The prepared arrays occupy 25,057,779 bytes in total
(approximately 23.9 MiB), plus their manifest and attribution.

Each NPZ contains only `positions_m`, `times_s`, Unicode `labels`, and integer
display `links`. Loading uses `allow_pickle=False`. Hashes, array byte counts,
shapes, labels, sample timing, finite coordinates, links, and missing-point counts
are checked before display. Links connect observed skin markers for viewing;
they are not independently validated anatomical joint centers.

Only documented body-marker labels are displayed; other source labels remain
listed as excluded. The recordings contain either 45 or 48 included markers.
The full original source-label list is retained in each entry.

## Three explicit source-label aliases

Pitches `1759_1`, `1759_2`, and `1759_3`, athlete `1017`, use labels such as
`Skeleton_001_LSHO` instead of `LSHO`. These source files contain one consistent
trajectory namespace. For these three recordings only, preparation removes the
`Skeleton_001_` prefix from known body-marker display labels and retains the
complete reversible `marker_label_aliases` map and `source_marker_labels` list.

This is a string-label operation: coordinates, coordinate signs, units, sample
times, and missingness do not change. The word `Skeleton` in an export namespace
does not establish a validated skeletal reconstruction. Unknown prefixes are
not guessed, aliases must be one to one, and multiple subject namespaces or
namespace/bare-marker mixtures are rejected rather than merged.

## Missing observations remain missing

The source residual policy is the existing preparation rule: negative or
nonfinite residuals, or any nonfinite coordinate, invalidate the complete XYZ
sample for that marker. The prepared sample remains NaN rather than being filled,
zeroed, or interpolated. The renderer omits absent points and their guide links.

Pitch `1668_3`, athlete `986`, contains 63 invalid source marker-samples; 11 are
retained on the display grid. These remain missing. Other prepared recordings
contain no missing included-marker samples under this policy. A marker-sample
means one marker in one frame; these counts do not denote 63 missing athletes or
63 missing marker trajectories.

All 411 source candidates produced usable recordings. The manifest has an empty
`unavailable` list. The preparation workflow nevertheless records failures
explicitly if a future source candidate cannot be safely prepared, instead of
inventing a recording or silently dropping its pitch from the coverage audit.

## Time and interpretation

Display times are seconds relative to each C3D capture's first sample. They are
not event-aligned across pitches, camera recordings, or released processed
signals. Side-by-side playback permits visual inspection, not a synchronized
kinematic-sequence analysis. No marker frame is relabeled foot plant or ball
release without a verified source-time mapping.

The broader marker catalog does not expand the scalar-verification sample.
The [measurement reproduction audit](MEASUREMENT_VERIFICATION.md) still compares
four released signal maxima in the original three prepared trace examples. That
audit is not independent inverse-dynamics validation. More marker replays do not
add injury outcomes, causal mechanics effects, or external-cohort validation.

## Reproduce the catalog offline

Viewing prepared assets requires no C3D parser or source archive. To reproduce
them, obtain the exact licensed source archive separately and install the
optional motion dependency:

```powershell
uv sync --frozen --extra motion
uv run --frozen python scripts/prepare_pitch_catalog.py --archive PATH_TO/pitching_c3d.zip --output-dir PATH_TO/new-catalog
```

The command performs no network requests. It verifies the archive's complete
byte count and SHA-256 before reading C3D members, verifies the released analysis
snapshot, and prepares exact metadata-linked members in temporary storage. The
output directory must not exist. A staging directory is renamed only after every
candidate has been examined, and existing operator files are preserved.

Use a new output directory to compare a reproduction; the public default is
`assets/pitch_catalog`. Compare every NPZ, the manifest quality totals, source
identities, and transformation hashes before deliberately replacing a release.
Source C3Ds remain temporary and are not included in the public derivative
catalog. The archive itself is excluded from Git.

The loader APIs are `load_pitch_catalog(project_root)`,
`catalog_examples(frame, manifest)`, and `load_catalog_frames(directory, entry)`
in `pitching.pitch_catalog`. They are read-only and never download, fit a model,
or fill missing observations. The original `assets/motion` and `assets/traces`
manifests are not modified by this workflow.

## Data terms

Source: Driveline Baseball Research & Development, OpenBiomechanics Project.
The arrays, label adaptations, replays, and related source-derived material
retain CC BY-NC-SA 4.0 plus the upstream professional-sports/financial-analysis
affiliation exclusion. Software's MIT license does not grant those data rights.
Preserve `assets/pitch_catalog/ATTRIBUTION.md` and the full
[pinned upstream data terms](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md).
