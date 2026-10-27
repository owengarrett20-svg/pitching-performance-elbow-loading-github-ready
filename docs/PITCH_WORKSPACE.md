# Search a pitch, then inspect the exact recording

The **Explore pitches → Find & compare pitches** view links a searchable table
to two observed source rows, their prepared marker replays, the recorded marker
set, and their measured point-of-interest values. The existing association
charts remain available separately. No model fitting or source download runs
when a visitor searches, selects, plays, or exports a recording.

## Select observations

Search is case-insensitive. A leading `pitch`, `athlete`, or `session` label
followed by a value matches that identifier exactly; colon notation such as
`athlete:970` is also supported. Remaining free-text tokens are literal and must
all match. Examples:

- `1623_3` or `pitch 1623_3` identifies a source pitch.
- `athlete 970` finds the supplied athlete identifier.
- `college` finds source playing-level text.
- `85.3` searches released and displayed numeric values across the five focal
  measurements; it is not a pitch-speed-only filter.

The replay toggle limits results to source pitches declared available by the
local catalog. Search does not interpret regular expressions, alter values,
impute missing observations, or rank technique. Identifier strings and playing
levels are retained from the selected source table. Several rows may belong to
one athlete and are not independent athlete observations.

Click a table row to open **Pitch A**. Keyboard and touch users can use the Pitch
A selector instead. **Pitch B** can be any pitch in the sidebar-filtered source
table, including one outside the current free-text search. Selecting the same
pitch twice is allowed and explicitly labeled. A search with no matching rows
removes the replay panes; it does not silently retain the previous recording.

The table's input order is stable, with prepared replays first. Streamlit reports
selected row positions relative to that input even after a browser-side sort.
The selection handler maps exactly one valid integer position to its source ID.
Malformed, stale, multiple, or out-of-range selections are ignored. Search and
Pitch A changes create a new table-selection generation so an old table
highlight cannot override a later dropdown choice.

The route returns both actual selected IDs to its parent. Ordinary URL/state
round trips do not undo user changes. Copying the page address shares source
identifiers only; URL text is never treated as a path, recording, or observation.

## Compare recorded motion

The main panes contain interactive **measured skin-marker replays**, not camera
footage or estimated video poses. Each is identified by its exact source pitch
and athlete. Drag to rotate, use the frame slider or previous/next controls,
select a body region, or choose a source marker to inspect its X/Y/Z coordinates
in meters. The two panes remain independently controllable.

**Start available replays from their own starts** resets each available recording
to its own first displayed sample and starts it. It does **not** align ball
release, foot plant, an anatomical phase, or a processed-signal cursor. Different
trial lengths and unverified time origins prevent that interpretation. A joint
start is only a playback convenience. Missing markers stay missing, and guide
links are not validated anatomical joint centers.

Coverage comes from the verified local marker catalog. The expanded catalog is
matched against released metadata and analysis identities. A selected array is
checked for its source identity, byte count, SHA-256, labels, time grid, and
missingness before rendering. Corrupt or unavailable recordings show an
explicit placeholder for the selected ID. They are never replaced with another
athlete's or a nearby-speed pitch's motion.

The original three MP4 examples are available under **Prepared video clips for
the original examples**. They also show measured marker animations. Absence of
an MP4 does not mean absence of an interactive replay, and neither establishes
camera coverage. The separate official camera example remains in the existing
video lessons without an asserted identity link to study pitches.

## Inspect the associated measurements and markers

The comparison table uses the two selected source rows for pitch speed, peak
internal net elbow varus moment, peak shoulder rotational velocity, peak
thorax–pelvis separation, and peak torso rotational velocity. Units accompany
every row. Differences are **B minus A**, and a missing source value leaves its
difference missing. These observations do not estimate an intervention effect.
Peaks need not occur at the same instant. Peak separation is not specifically
separation at foot plant, and internal net moment is not ligament force or
injury probability.

The marker panel lists the recorded labels, display groups, and observed/missing
prepared-sample counts. Original source labels appear beside display labels;
explicit `Skeleton_001_` namespace aliases are documented for the three source
recordings that use them. The label-only normalization leaves coordinates
unchanged. These are the source markers displayed in the recording,
not an independently verified list of marker contributions to each anatomical
calculation. Released joint signals and moments come from the source processing.
This viewer does not reconstruct source filtering, segment coordinate systems,
joint centers, inertial parameters, or inverse dynamics from the displayed points.

## Export and reproduce

The replay HTML is self-contained, includes local playback code and source terms,
and loads no network assets. Selected-observation JSON retains the exact pitch
and athlete IDs, five observed values, units, source revision, and data license.
Missing values are JSON `null`, never zero or nonstandard `NaN`.
The expandable full-record table and JSON `source_records` also retain the
remaining released fields for each selected observation. Their definitions and
units follow the pinned source dictionaries; they are not new model predictions.

All replays and source-derived exports retain OBP's data terms, including the
professional-sports/financial-analysis affiliation restriction. See
[LICENSING.md](LICENSING.md), [VIDEO_METHODS.md](VIDEO_METHODS.md), and
[MOTION_LAB.md](MOTION_LAB.md). Original software licensing does not grant data
rights. Tests cover searches, source identity, row mapping, stale events, missing
measurements, corrupted assets, escaped output, and repeated selection changes;
actual browser interaction is part of release verification.
