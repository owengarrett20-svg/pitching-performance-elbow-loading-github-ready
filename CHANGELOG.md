# Changelog

These entries describe local project development. They do not establish that a
version has been published as a GitHub release or archived with a DOI.

## 0.8.0 — Pitcher-versus-pitch variation and a reviewer-first repository

- Add **Study results → Pitcher vs. pitch variation**: elbow moment scaled by body weight × height, ICC(1) variance shares, and pooled within-athlete versus between-athlete-mean speed slopes with 5,000 seeded athlete-cluster bootstrap resamples.
- Document the exploratory status, methods, results, college-only sensitivity subset, and limits in `docs/ATHLETE_VARIATION.md`, with tests that recover exact synthetic slopes, match one-way ANOVA ICC, exclude incomplete pitches, and check the documented numbers against the computation.
- Lead the README with the research questions, key findings, and figure; add markerless/wearable measurement validation as a future extension.
- Replace the bundle-based Windows guide with a clone-and-run guide; move earlier phase scopes, upgrade guides, and Phase 4 validation into `docs/archive/`.
- Remove the PhD application guide from the public repository; it is kept with private application materials.
- State recurring workspace caveats once instead of repeating them in several captions.
- Preserve the Phase 1/2 sample, models, findings, research brief outputs, and source data restrictions.

## 0.7.1 — Phase 5.1 direct pitch picking

- Add a clickable chart to Find & compare pitches: choose any two of the five focal measurements, click a point to open that exact recorded pitch, and see Pitch A and Pitch B labeled among the searched rows.
- Let a table-row or chart-point click fill either Pitch A or Pitch B, so both comparison pitches can be chosen without dropdowns.
- Show all five focal measurements, playing level, and an A/B marker in the searchable table.
- Add Swap A and B, and a within-athlete control that cycles Pitch B through Pitch A's athlete's other recorded pitches.
- Add mid-rank cohort percentiles for both pitches; missing values receive no percentile and the wording keeps percentiles descriptive.
- Correct the Charts & associations caption that still described three prepared marker replays.
- Preserve the Phase 1/2 sample, models, numerical findings, research brief outputs, and source data restrictions.

## 0.7.0 — Phase 5 source-linked workspace and research brief; publication pending

- Add a searchable, selectable recorded-pitch table with side-by-side marker replays, marker-set inspection, associated values, and checked A/B share links.
- Retain the existing association charts and athlete-average view separately from the default comparison workspace.
- Prepare source-linked measured-marker arrays for all 411 study pitches from the verified official archive; retain raw label aliases, source identity, and missing observations.
- Keep the original three MP4/processed-trace examples distinct from catalog coverage and camera footage; simultaneous playback does not establish event alignment.
- Add a source-derived research brief with HTML, Markdown, provenance, and an explicit twelve-check selected source-scalar reproduction audit.
- Distinguish software/source reproduction, internal held-out prediction, independent biomechanical validation, and an unperformed external study.
- Document contributions, substantial AI implementation assistance, application wording boundaries, and private handling of CV-specific drafts.
- Preserve the Phase 1/2 sample, models, numerical findings, uncertainty scope, and source data restrictions.

## 0.6.0 — Phase 4 code published to the connected branch

- Add an interactive measured-marker lab with independent marker and processed-signal inspection; retain unverified timing and source-convention limits.
- Add source-attributed athlete reports as self-contained printable HTML, with missingness-aware summaries and strictly matched saved held-out errors.
- Add local new-data mapping, explicit unit conversion, source/definition/permission declarations, grouping checks, and checksum-bound prepared artifacts.
- Add a two-stage development freeze and new-athlete external-evaluation workflow using numerical JSON models and fixed preprocessing.
- Report local external errors and covariate differences only when authorized new data are actually supplied; no external dataset or result is included in this release.
- Add Athlete reports and New-data lab views without introducing a public athlete-file uploader.
- Preserve the existing Phase 1/2 findings, retrospective estimand, conditional intervals, uncertain elbow finding, and source data-use restrictions.
- Document the existing-history bundle upgrade and missing-download checks before fetching.
- Publish the Phase 4 update at commit `ad4cd71`; this does not establish a tagged release, DOI, or independently verified deployment.

## 0.5.0 — Phase 3 code published to the connected branch

- Add five focused views with a short research opening and active-view rendering.
- Present verified outcome comparisons in plain language while retaining the detailed audit.
- Add interactive recorded-pitch charts, accessible selection, athlete averages, and observed A/B comparisons.
- Add checked, shareable page/pitch links and source-attributed CSV downloads.
- Keep the existing measured-marker examples and place additional motion explanations behind expandable controls.
- Add a non-sensitive collaboration introduction and guidance for future independently authorized data.
- Declare Altair as a direct dependency without changing the fixed scientific models or source data.
- Preserve conditional interval scope, uncertain elbow findings, source identities, and data-use restrictions.
- Publish the Phase 3 update at commit `edf5c05`; a tagged archival release remains a separate step.

## 0.4.0 — Phase 2 code published to the connected branch

- Freeze an exploratory follow-on analysis plan before computing new model comparisons.
- Compare age/body-size, rotational kinematics, and combined ridge predictors on shared athlete folds.
- Add paired athlete-cluster bootstrap intervals conditional on fixed held-out errors.
- Refit the study across ten declared athlete partitions and retain all planned contrasts.
- Add Phase 2 dashboard views, a generated research report, three figures, and auditable outputs.
- Bind the producing analysis plan and every study artifact to verified hosted snapshots.
- Preserve the existing Phase 1, motion examples, upstream attribution, and data-use restrictions.
- Publish the Phase 2 update at commit `a2f339e`; a tagged archival release remains a separate step.

## 0.3.0 — GitHub and hosted demonstration

- Prepare the project for GitHub review and a reproducible hosted dashboard.
- Add contribution guidance, software citation metadata, issue/PR templates,
  a short study summary, and a staged research roadmap.
- Keep software licensing distinct from OBP data and derived-material terms.
- Publish the project repository and the reference dashboard; public URLs appear in the README.

## 0.2.0 — local development milestone

- Add three metadata-linked marker-motion examples and released signal traces.
- Add an educational measurement animation, source-cited lessons, and a paused
  marker-frame inspector.
- Link an official camera example separately from study-pitch measurements.
- Document marker/signal clock boundaries, source conventions, and media rights.

Local history: commit `421e519`.

## 0.1.0 — local development milestone

- Pin OBP source files and validate their hashes, schema, and one-to-one joins.
- Produce missingness reports and five-variable exploratory plots.
- Compare training-mean and fixed ridge baselines with athlete-grouped validation.
- Add the Streamlit explorer, tests, analysis plan, and reproducibility notes.

Local history: commit `bcd6502`.
