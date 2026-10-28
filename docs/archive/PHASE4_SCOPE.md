# Phase 4: an inspectable research lab and a new-data workflow

This scope was recorded before implementing the new workflows. The release
extends the published Phase 3 at `edf5c05`; it does not replace the Phase 2
analysis plan or its findings. It is a software and methods milestone, not a
completed external-validation study.

## Deliverables

1. An offline, interactive measured-marker lab for the three prepared source
   pitches, with body-region inspection and source-linked signal calculations.
   Marker and processed-signal clocks remain independent unless an original
   source establishes their relationship. Similar lengths or peaks do not
   establish alignment. No synchronized camera footage is assumed.
2. Downloadable, self-contained athlete HTML reports, printable to PDF using
   the browser, with measurements, missingness, observed variation, and verified
   saved held-out errors. The few pitches from one recorded assessment do not
   support a reliable consistency trait, longitudinal improvement, causal
   coaching instruction, tissue-force estimate, or injury prediction.
3. A local-only, auditable new-data adapter. Mapping requires explicit units,
   measurement definitions, sign conventions, identity namespace, population,
   collection protocol, and an operator declaration of authorized use. Missing
   outcomes remain missing. IDs, joins, numeric validity, output integrity, and
   repeated-measure structure are checked before modeling.
4. A separate freeze/evaluate external-validation workflow. A declared protocol
   and authorized development data produce fixed numerical model parameters.
   A new cohort is evaluated without fitting or tuning on its rows. Athlete
   independence and measurement compatibility require owner attestations;
   different identifier namespaces do not verify independent athletes. Report
   descriptive errors and cohort shift, including unfavorable findings.

## Evaluation contract

The four fixed models remain the training mean and anthropometric, kinematic,
and combined ridge baselines with alpha 10. The external workflow fits on the
declared development cohort once and freezes preprocessing and coefficients
before evaluation. These fits are distinct from the existing grouped out-of-fold
Phase 2 evidence. The supported target is a new-athlete cohort using completed
pitch measurements; temporal forecasting and intervention effects are outside
this implementation.

Model bundles use validated numerical JSON, not executable object serialization.
Private inputs and results belong in ignored `local_studies/` or a separately
approved environment, and are never automatically added to the public snapshot.
Integrity hashes detect stale/corrupted files; they do not certify permission,
independence, study registration, or externally authenticated provenance.

## Release checks

Exercise source identities, independent clocks, selection persistence, missing
measurements, escaped report content, unit conversions, duplicate/grouping
failures, frozen preprocessing, exact pipeline prediction agreement, overlap
rejection, corrupted bundles, and evaluation without fitting. Synthetic records
may be used only in explicitly labeled tests; no invented external observations
or scores appear in the public application.

Run locked installation, the appropriate test suite and code checks, actual
desktop/phone browser interactions, and a clean-copy offline hosted smoke test.
Rebuild the unchanged Phase 2 scientific artifacts only to bind them to the
release source. Verify the Windows Git-bundle upgrade from the published base.

## Data rights and publication

OBP and its derived reports, movies, traces, and model outputs retain the upstream
data terms and professional-sports/financial-analysis affiliation exclusion.
The original software is MIT; that license does not grant restricted data rights.
Future team work needs independently authorized development and evaluation data.
There is no confidential data upload service or completed organizational study.

The new release is prepared locally for review and installation. Existing GitHub
and Streamlit addresses remain; publication requires pushing the updated branch
and a successful deployment rebuild.
