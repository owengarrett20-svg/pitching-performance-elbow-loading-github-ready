# Recorded athlete research reports

The **Athlete reports** view creates a self-contained HTML report of one
pseudonymous athlete's recorded observations. Open the HTML in a browser; use
**Print → Save as PDF** when a PDF is useful. It requires no internet connection,
runs no scripts, and embeds its figures and styles. There is no PDF server or
new report-generation dependency.

The companion observation CSV and provenance JSON should travel together.
Missing measurements remain empty CSV cells and are marked as missing in HTML.
Neither rendering nor exporting a report downloads data, fits a model, or runs a
bootstrap calculation.

The dashboard puts the three report downloads near the athlete/session counts.
Five cards show observed means with units, ranges, and missing counts. Card
rounding affects display only; the detailed measurement table and observation
CSV retain their original numerical precision. A fully missing measure is
shown as **Unavailable**. The full table remains under **Detailed measurement
table**, and the recorded-pitch chart and saved-error inspection remain
available below the summaries.

Identifier strings that could be interpreted as spreadsheet formulas receive a
protective apostrophe prefix in the CSV. Their original strings and affected
row/column locations are retained in `csv_identifier_escapes` in the companion
metadata. This applies to identifiers only; numeric measurements, including
negative values, remain unchanged. Released OBP identifiers require no such
escape. The observation-file checksum describes the actual exported bytes.

## Scope of the observations

The main dashboard supplies its full verified analysis table to the report
builder. For each selected athlete, the report includes that supplied table's
recorded pitch rows, rather than an arbitrary current scatterplot selection.
If a caller supplies a subset, the report states both its included pitch count
and the available athlete count in the verified study table when matching is
possible. The supplied-table cohort counts are retained in provenance.

The released sample has only two to five pitches and one assessment session per
athlete. These reports describe observations; they do not establish a reliable
long-term consistency trait, development trend, clinical assessment, or causal
mechanics intervention. Identifier ordering is not a time axis.

For each of the five focal measures, the report gives observed count, missing
count, mean, and minimum/maximum in its native units. Means use observed values
for that variable only. Rotation means average the released per-pitch peak
summaries; they are not time-averaged signal traces. Different peaks may occur
at different instants. Hip–shoulder separation is the released peak angle,
not specifically the angle at foot contact.

Internal net elbow varus moment is a joint-level moment, not UCL force, injury
probability, or a safe/unsafe threshold. No unified technique, talent, or injury
score is generated. Individual metrics retain their own units.

## Saved model errors

Errors are optional. `load_phase2_reports` first verifies the complete
hash-bound parent/child Phase 2 artifact set. The reporting layer then requires
agreement of the selected pitch ID, athlete ID, session when supplied, and all
five displayed observed measurements with the verified source table.

The report reads only the **primary partition's combined ridge** prediction
rows. Every included observed outcome must have one row, without duplicate
pitch/outcome pairs. Observed values, saved residuals, absolute errors, athlete
identity, and saved fold assignments must agree. A mismatch withholds the
saved errors with an explanation. Source identity is marked unverified when
the observations do not match the verified study table.

The per-athlete, per-outcome mean absolute error averages that athlete's
recorded pitch errors. The complete study's primary metric averages athlete
MAEs equally. A report's individual errors are diagnostic details of already
computed athlete-held-out predictions, not an independent external validation
study, a newly trained model, an individualized uncertainty interval, or an
injury assessment. This is separate from the new-data freezing/evaluation
workflow.

## Provenance and safe output

Provenance retains report/software versions, UTC creation time, supplied and
selected counts, verification status, pinned source revision, producing study
revision, observed-row CSV SHA-256, verified study-analysis checksum, and saved
primary prediction-file checksum. Checksums identify exact artifacts; they are
not independent scientific validation or a cryptographic author signature.

HTML values are escaped, and graphs are inline SVG with no active code. The
report is responsive on screen and has print styles. Wide observation tables
remain inside their own horizontal scroll container. Downloads use fixed safe
filenames rather than treating athlete identifiers as paths.

OBP-derived report material retains the source attribution and data terms:
**CC BY-NC-SA 4.0 with the additional professional-sports/financial-analysis
affiliation restriction**. The software's MIT license does not grant those data
rights. Preserve the notices in HTML and companion metadata, and consult
[LICENSING.md](LICENSING.md) before reuse or organizational work.

## Developer API

- `prepare_athlete_report(frame, athlete_id, verified_reports=None)` creates the
  scoped report without I/O or model fitting.
- `render_report_html(report)`, `report_csv(report)`, and
  `report_metadata_json(report)` return standalone export contents.
- `render_report_builder(frame, report_dir, project_root)` renders the view.
  A navigation callback can set `st.session_state["report_requested_athlete"]`
  to request an athlete once. The builder consumes that request before creating
  its `report_athlete` widget, allowing subsequent user selections to persist.
