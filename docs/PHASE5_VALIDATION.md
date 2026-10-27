# Phase 5 release verification

Version **0.7.0** · checked 27 October 2026. These are development-agent
executions. They are not a claim of personal replication by the project owner,
independent biomechanical validation, external-cohort performance, or peer review.

## Automated checks

- `uv run --frozen pytest -q`: **399 passed**, no skipped tests, in 198.67 seconds.
- Ruff lint passed; all 70 checked Python files passed formatting checks.
- Requirements export matches the lockfile, and `git diff --check` passed.
- Checks include exact search/selection identity, stale selection and empty
  results, paired URL state, corrupt/unavailable assets, source matching,
  grouped evaluation, frozen preprocessing, and offline hosted views.

## Source-linked recordings

All **411 pitches from 100 athletes** have exactly matched C3D-derived marker
replays. All 411 prepared numerical assets were loaded with their byte counts,
SHA-256 digests, array dimensions, label identities, sample times, and missing
observations checked. The archive checksum and each selected source member's
checksum were verified. Catalog-specific tests: **26 passed**.

A full independent rerun of the preparation command from the cached source
archive reproduced every NPZ byte for byte. Only a stale generator-code hash in
the manifest required correction; the regenerated manifest now records the
current generator. No coordinates or study values changed. The original three
prepared recordings remain numerically unchanged.

- 247,709 source frames; 41,462 retained display frames.
- 360 Hz source grid, every sixth sample displayed; coordinates remain meters.
- Pitch `1668_3`: 63 invalid source marker-samples and 11 retained display
  marker-samples remain missing.
- Pitches `1759_1`, `1759_2`, and `1759_3`: explicit reversible single-subject
  display-label aliases preserve their original source labels and coordinates.

These are measured-marker animations. They do not establish camera-video
availability, validated anatomical joint centers, or event/processed-signal
synchronization between recordings.

## Scientific reproduction

`uv run --frozen pitching phase2 --offline` completed from clean producing
revision `77dea84e6d03985fb145172f1f721e7168909480`. Both run records report
`project_git_dirty: false`. The refreshed hosted snapshot contains **43 verified
files**. Relative to the published Phase 4 snapshot, **41 scientific artifacts
are byte-identical**; only the two run metadata files changed. The enclosing
manifest was updated to bind those metadata changes.

Source joins, the analysis table, figures, predictions, fold assignments,
fixed-model comparisons, resampling results, and uncertainty findings are
unchanged. No new model or external cohort was introduced.

The measurement audit reproduces **12 of 12** released scalar maxima, with zero
numeric differences, using four released traces in each of three original
examples. It checks the supplied signal summaries against supplied POIs. It does
not independently validate inverse dynamics or extend processed-signal coverage
to all 411 marker recordings.

## Research brief and privacy

The static brief is exported from the refreshed, checksum-bound reference
snapshot. Its self-contained HTML was printed with Chromium as **two A4 pages**.
Desktop width 1100 and phone width 390 showed no horizontal overflow. The
document preserves the uncertain elbow-moment comparison, conditional
resampling scope, source attribution, and assistance/contribution boundaries.

CV-specific application drafts and the uploaded CV remain outside the public
repository. Public documentation was checked for CV-specific institutional,
contact, and application details. The source ZIP and Git bundle must contain
only the committed public project; private applications and local study outputs
are excluded.

## Browser interactions and release artifacts

Real Chromium interaction checks confirmed exact athlete search, a rendered
table-row click updating Pitch A and its URL, a dropdown overriding an earlier
row selection, reselection of that same row, independent Pitch B changes,
correct source identity after client-side sorting, both marker canvases, and
paired start/pause controls operating each recording's own clock. Browser
screenshots of the opening, workspace, and research brief are included in
`docs/images`. Desktop and phone previews showed no document-level horizontal
overflow or application exceptions.

The separate release record supplies bundle/source-ZIP checksums and fresh-copy
installation evidence. It is kept beside the downloadable artifacts so its
commit and archive hashes do not create a self-referential source file.

All 194 checked relative documentation links resolve. The unchanged upstream
licenses retain their original text; small reference pages keep their mutual
relative links usable in this repository.

GitHub Actions and the existing Streamlit deployment require verification
after the owner pushes this release. Local checks cannot establish the result
of a later remote rebuild.
