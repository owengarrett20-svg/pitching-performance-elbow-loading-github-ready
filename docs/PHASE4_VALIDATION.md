# Phase 4 release verification

Version 0.6.0 adds motion inspection, athlete reporting, and local new-data
workflows to the published Phase 3 history at `edf5c05`. Checks below describe
local software behavior on 2026-10-20. They do not establish external validity,
peer review, data permission, or a newly deployed public version.

## Automated checks

- Complete suite: **305 passed**, with the nine small pinned source files
  present so the real-data integration checks execute.
- Ruff lint and formatting: passed for all 59 checked Python files.
- Locked runtime dependency export: matches `uv.lock`.
- Python 3.12.14 and uv 0.12.23; numerical dependencies retain their Phase 3
  versions. Only the local package version changes to 0.6.0.
- The local audit → freeze → audit → evaluate CLI is exercised end to end on
  explicitly synthetic test fixtures. Network access and fitting are forbidden
  during evaluation; frozen bundle files remain unchanged. These fixtures never
  enter the public reference dataset or research findings.

Tests cover identity and leading-zero preservation, units, semantic/sign/rights
declarations, missing outcomes, source-column reuse, malformed input, output
preservation, corruption, exact frozen/sklearn prediction agreement, training-only
preprocessing, shared-namespace overlap, and cross-namespace limitations.
Report tests check missing-versus-zero values, safe HTML and CSV identifiers,
source matching, saved errors, and scope. Motion tests cover missing coordinates,
checksums, source identity, clocks, and selection persistence.

## Actual browser interaction

Chromium at 1440×1000 and 390×844 passed 41 integrated checks and ten further
checks after the final athlete-report layout update. These include real chart
clicks, chart-to-athlete handoff, repeated selection changes, URL agreement, all
seven routes, legacy video playback, and actual HTML/ZIP downloads.

The measured-marker canvas rotates, zooms, highlights regions, scrubs, and plays.
Trace peak jumps leave its marker frame unchanged. The replay component fits
both viewport widths without nested vertical scrolling. Downloaded marker HTML
also supports keyboard frame changes and loads no network assets.

The athlete report opens at desktop and phone widths without horizontal document
overflow or JavaScript errors, loads no network assets, and prints successfully
to PDF. The builder exposes download controls before its measurement cards;
full-precision tables remain available separately. Opening navigation and report
links preserve source identities. The planning ZIP contains only the fixed blank
mapping, dictionary, protocol, and instructions.

Source-derived screenshots are retained under `docs/images/`. Preview servers
started for these checks were stopped. Browser checks are not a substitute for
future usability research with coaches or researchers.

## Reproducibility and packaging acceptance

The release process requires a clean-source reproduction of Phase 1/2, a verified
43-file reference snapshot, and comparison of scientific artifacts with Phase 3.
Producing source revision, code hashes, input hashes, dependency lock hash, and
dirty status are retained in the snapshot metadata.

The Git bundle must fast-forward a disposable clone from `edf5c05` with
`core.autocrlf=true`, preserving its GitHub remote and asset bytes. A runtime-only
installation must render every reference view with network/model fitting
disabled and without raw-data or working-report directories. The source ZIP
contains tracked project files and prepared public assets, excluding Git state,
environments, caches, private studies, and working source downloads.

## Evidence limits

Marker and processed-signal time origins remain unverified. Reports summarize a
few pitches from one released assessment per athlete. There is no new independent
evaluation cohort, external score, injury endpoint, tissue-specific force,
causal coaching effect, or confidential public upload service. Owner declarations
and hashes support an audit trail; they do not authenticate study independence
or permissions. OBP and source-derived material retain their full data terms.
