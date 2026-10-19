# Contributing

Thank you for helping make this a clear, reproducible biomechanics study. Read the
[research plan](docs/RESEARCH_PLAN.md), [variable definitions](docs/VARIABLES.md),
and [licensing notes](docs/LICENSING.md) before proposing a scientific change.

## Local development

Use Python 3.12 and uv. From the checkout root:

```bash
uv sync --frozen --extra dev
uv run --frozen pitching fetch
uv run --frozen pitching run --offline
uv run --frozen pytest -q
uv run --frozen ruff check src tests scripts app.py streamlit_app.py
```

Fetching first enables the cached real-data integration tests. Tests themselves
must not require network access. Clearly label synthetic test fixtures; never mix
them with the reported observations. The dashboard uses prepared visual assets;
FFmpeg, motion extras, and large source archives are only needed to rebuild those
assets, as described in [VIDEO_METHODS.md](docs/VIDEO_METHODS.md).

## Propose a focused change

- Open a bug report for reproducible software failures, or a research-question
  issue for a new hypothesis or analysis. Explain the purpose and expected output.
- Keep changes small enough to review. Include a test for a meaningful behavior
  change and update documentation where behavior or interpretation changes.
- Preserve immutable source revisions, verification checksums, source units, and
  missing observations. Do not replace missing targets or quietly exclude unusual
  athletes to improve model scores.
- Keep all preprocessing within training folds and all of an athlete's pitches in
  one evaluation fold. Treat changes to features, tuning, evaluation, or exclusions
  as a new analysis specification; do not compare repeatedly selected models as
  if the displayed folds were untouched evaluation data.
- Distinguish a measured motion replay, a processed signal, a schematic, and a
  camera recording. Do not infer frame synchronization or pitch identity without
  evidence. Never attach MLB footage scraped from other sites.

## Scientific and licensing review

Report errors in physical units, identify the population and evaluation unit, and
describe limitations. Joint moments are loading measures, not injury labels or
tissue-specific forces. Predictive associations do not establish a causal coaching
intervention. Cite a source when changing a biomechanical definition.

Original software contributions use the project's MIT license. OBP data,
documentation adaptations, and data-derived assets retain the upstream terms,
including its professional-sports/financial-analysis affiliation restriction.
Do not place third-party data or media under the code license. Obtain required
permission before using restricted material in an excluded setting.

Do not post secrets, private license credentials, identifiable athlete information,
or athlete videos without the necessary rights and consent. Share the minimum
non-sensitive example needed to reproduce a bug. Please disclose suspected secret
exposure privately through GitHub's available reporting controls rather than a
public issue.
