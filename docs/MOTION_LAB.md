# Motion and measurement lab

The **Watch motion → Interactive lab** view uses the verified measured-marker
catalog, prepared for all 411 released study pitches in Phase 5. The original
three prepared examples remain a fallback when that catalog is absent, and are
the only pitches with the bundled detailed processed traces and MP4 clips.
No source archive is downloaded and no reconstruction, filtering, model fitting,
or inverse dynamics runs when the page opens. The
[source catalog guide](PITCH_CATALOG.md) records coverage, missingness, and the
three explicitly documented source-label namespace aliases.

## What can be inspected

| Source pitch | Source athlete | Recorded speed | Source marker samples | Display samples |
| --- | --- | ---: | ---: | ---: |
| `1393_3` | `919` | 69.5 mph | 540 | 90 |
| `1623_3` | `970` | 85.3 mph | 806 | 135 |
| `2916_4` | `1596` | 94.4 mph | 406 | 68 |

The table lists the three original detailed trace/MP4 examples, illustrating
low, near-median, and high recorded speeds in the released cohort. They are
selected illustrations, not a representative sample or an experiment comparing
three pitching techniques. The expanded catalog provides playable marker
animations for all 411 pitches, while camera footage and detailed trace coverage
remain separate questions.

The viewer checks the exact pitch **and** athlete against the selected analysis
rows. It returns the actual displayed pitch ID to the dashboard so the page
address identifies the visible recording. An unavailable selection produces an
explanation; a filter excluding all prepared examples produces an empty state.
An asset failing its recorded checksum is hidden rather than substituted.

## Inspect measured motion

The local canvas displays measured skin-marker coordinates in meters using an
orthographic 3D projection. Drag to rotate, use the camera/zoom buttons, or choose
the X–Z and Y–Z views. Highlight the head, trunk, upper limbs, or lower limbs.
Selecting a marker displays its measured coordinates at the current replay
sample. Unknown marker labels remain available in the all-marker view.

The marker slider and previous/next controls are keyboard accessible. Playback
offers 0.25×, 0.5×, and 1× recorded speed, using the prepared sample timestamps.
The source marker sampling rate is 360 Hz; the prepared arrays retain every
sixth source sample. This is a downsampled display, so it does not expose every
original marker frame. The prepared MP4 clips remain available through
**Video & measurement lessons**.

Missing markers stay missing. Display links between markers are visual guides;
they are not independently validated anatomical joint centers or a skeletal
model. Rotating the view changes only the projection, not the source coordinates
or a measurement. A marker's apparent projected angle is not automatically the
source's anatomical joint angle.

The **Download this interactive marker replay (HTML)** file is self-contained
and works offline. It contains the displayed source coordinates, local JavaScript,
attribution, and data-use terms. It loads no external scripts or fonts. It can be
shared only under the applicable source terms.

The expandable native coordinate inspector provides a table fallback. Its
sample control is independent of the replay's client-side slider; both controls
use the marker clock, but moving one does not move the other. The selected marker
inside the replay is the direct way to inspect the replay's current coordinates.

## Follow a released signal to its scalar summary

The independent signal inspector offers four released quantities:

| Published POI | Released column | Displayed units |
| --- | --- | --- |
| Peak hip–shoulder separation | `torso_pelvis_angle_z` | deg |
| Named peak shoulder internal rotation velocity | `shoulder_velo_z` | deg/s |
| Peak torso rotation velocity | `torso_velo_z` | deg/s |
| Peak internal net elbow varus moment | `elbow_moment_y` | N·m |

Choose an analysis window, inspect the trace cursor, or jump it to the largest
finite value within that window. The calculation retains the largest **signed**
value, not the largest absolute magnitude. Gaps stay missing; lines do not bridge
missing runs. An empty or entirely missing window has no maximum and disables
the peak-jump control.

The published POI appears beside the selected-window maximum. The whole-trace
maximum matches the released scalar in these prepared examples. That agreement
does not independently reproduce or validate source filtering, coordinate
conventions, POI windowing, or inverse dynamics. Narrowing the window illustrates
why phase-specific and whole-trial peaks can differ.

Hip–shoulder separation is a released torso–pelvis rotational signal. Its peak
is not necessarily the separation at foot plant. The processed shoulder-velocity
sign is retained: the positive maximum of `shoulder_velo_z` matches the named
internal-rotation POI in these examples, while the broad upstream angle-convention
table alone does not settle that velocity convention. The source ambiguity is
displayed. A 3D angular-velocity vector is generally not a vector of componentwise
Euler-angle derivatives.

Internal net elbow moment requires an appropriate dynamics model with motion,
external forces, inertial parameters, and timing. It cannot be computed from a
visible elbow angle alone. The released joint-level moment is not an isolated
ligament force, an injury probability, or an established safe threshold. Peak
magnitudes alone do not establish energy transfer or a causal coaching effect.

Recorded pitch speed remains the source POI: no full-signal ball trajectory is
provided to reconstruct it in this lab.

## Timing audit and the boundary between the controls

Marker replay times are seconds relative to the C3D start. Processed trace times
are the original CSV time values. All three prepared traces have the same sample
counts as their corresponding C3D sources and are numerically compatible with a
zero-based 360 Hz grid, within the released CSV rounding precision.

Those checks establish compatible sampling evidence. They do not establish a
shared origin, processing delay, or an event-to-marker mapping. The lab therefore
records timing status as **unverified**, even when counts and grids match.
The original source material reviewed for this project has not established the
mapping needed to synchronize the controls.

The replay and signal cursor remain independent. Trace peak-jump controls do not
move a marker frame. Source event times appear only in the processed-trace
provenance panel; no animation frame is labeled foot plant or ball release.
Foot contact and foot plant retain the source 10% and 100% body-weight threshold
definitions. ER/IR event names denote shoulder external/internal rotation.

A future synchronized view requires a documented source-clock mapping, checks
against the original source frame/time conventions, independently justified
handling of processing delays, and verified event definitions. Similar lengths,
numerical correlation, or matching peaks alone are insufficient. Camera-to-motion
alignment would additionally require verified recording identity and calibration.

## Reproducibility and validation

The motion and trace manifests retain exact source IDs, original filenames,
source hashes, asset hashes, units, rates, sample counts, and transformations.
The numerical arrays are loaded with `allow_pickle=False`; coordinates, times,
labels, and guide-link indices are checked before display. HTML escapes source
strings and JSON script boundaries; the local viewer uses text-only updates for
dynamic labels. No missing coordinate is interpolated.

Tests cover source-bound published peaks, missing-coordinate preservation,
marker-region membership, invalid/compatible clocks, script escaping, unavailable
or mismatched identities, corrupted assets, consecutive recorded-pitch changes,
and trace jumps that preserve the independent marker control. Actual browser
interaction is part of the release checks because unit tests cannot demonstrate
canvas usability or phone layout.

See [VIDEO_METHODS.md](VIDEO_METHODS.md) for source preparation, archive checksums,
the separate official camera example, and teaching-animation provenance.

## Attribution and data rights

Source: **Driveline Baseball Research & Development, OpenBiomechanics Project**,
revision `44b98dae05cceb016f080ab39d105c85b8639084`, release `dataset-v1`.
Transformations include selecting metadata-linked examples, downsampling observed
markers, projecting them for display, extracting released signals, and computing
user-selected finite-sample maxima. There is no new camera reconstruction or
independent dynamics replication.

Data-derived material retains CC BY-NC-SA 4.0 plus the additional
professional-sports/financial-analysis affiliation exclusion. The original
software's MIT license does not grant those data rights. Preserve attribution,
manifests, and the full source terms with redistributed reports or replays.
See [LICENSING.md](LICENSING.md) and the
[pinned source terms](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md).
