# A source-bound research brief for reviewers

The **Research brief** view presents the existing exploratory study in a concise
case-study format. It offers a self-contained HTML document designed for two A4
print pages, a plain-text Markdown version, machine-readable provenance, and the
released-scalar audit CSV. Use a browser's **Print → Save as PDF** to create a PDF.
The public view performs no downloads, model fitting, or resampling.

The brief is an independent research-software portfolio artifact. It is not a
peer-reviewed publication, a preregistered study, or a completed external
validation. Follow each program's application instructions when deciding
where a link or attachment is permitted.

## What the brief establishes

- The pinned OBP source, one-to-one pitch join, repeated-measure structure,
  missingness, and current eligible sample are identified.
- Both outcomes, four fixed models, equal-athlete errors, and the declared
  primary contrasts come from checksum-bound saved study reports.
- The elbow-moment increment remains uncertain when its conditional interval
  includes zero. The text does not select only a favorable result.
- Conditional athlete resampling uses fixed out-of-fold errors. The interval
  does not include full model-refitting uncertainty. The overlapping alternative
  partitions are descriptive sensitivity checks.
- The plan was recorded before Phase 2 comparisons after Phase 1 results had
  been viewed. It is an exploratory follow-on, not preregistration.
- The released-scalar audit reproduces supplied trace maxima against supplied
  POIs. It is not independent inverse dynamics, new biomechanical ground truth,
  or marker–signal synchronization. Missing trace samples remain missing.

The evidence table also makes unperformed work visible: independent dynamics
reconstruction, an external cohort study, and verified clock alignment. Injury
and causal coaching effects remain outside the study. These distinctions are
useful in a research interview because validation can refer to different
questions with different evidence requirements.

## Build the brief locally

From the project directory, install the locked runtime and choose a new output
directory:

```bash
uv sync --frozen
uv run --frozen python scripts/export_research_brief.py --output-dir reports/research-brief
```

The default reads the committed, verified reference snapshot. No raw source-data
fetch is needed. To use a completed local OBP reproduction explicitly:

```bash
uv run --frozen python scripts/export_research_brief.py --reports-dir reports --output-dir local_studies/public-brief
```

The output must remain separate from input reports. Existing output directories
are refused, including empty ones, to preserve user files. The exporter writes:

| File | Purpose |
| --- | --- |
| `research-brief.html` | Responsive case study with two designed print pages |
| `research-brief.md` | The same study facts in plain text |
| `research-brief-provenance.json` | Cohort, comparisons, source/plan/code/lock hashes, evidence scope |
| `measurement-reproduction.csv` | Individual source-summary checks and source identities |
| `evidence-summary.csv` | Available and unperformed evidence |
| `export-manifest.json` | SHA-256 hashes for the five exported documents/tables |

The exporter does not bundle private local studies or read an external cohort.
Its supported scientific source is the pinned OBP study. A different dataset
requires a separate study and appropriate reporting rather than relabeling the
public brief.

## Integrity and failure behavior

The default path verifies the complete hosted snapshot. An explicit local path
must contain a completed, bound Phase 2 study plus matching audit and missingness
artifacts from the pinned OBP revision. Counts, focal missingness, and eligible
model cohorts are checked before presenting results. A stale or inconsistent
study suppresses the brief.

If prepared trace assets are missing or corrupted, the source-summary audit is
shown as unresolved or unavailable. The brief does not claim a successful audit
from incomplete checks. The separately verified statistical study may still be
described with that narrower evidence boundary. Hashes establish file
consistency, not independently authenticated provenance or physical validity.

## Contribution, AI assistance, and applications

The heading identifies this as an **AI-assisted research-software portfolio**.
The user set the project framing and requirements; implementation and
documentation were developed with AI assistance. Describe personal execution,
review, explanation, and modifications accurately. Do not claim sole coding or
independent verification that has not happened. Use the
[contribution and assistance record](CONTRIBUTIONS_AND_AI.md) before adapting the
case study into an application or interview answer.

The strongest next scientific question is external transfer with compatible
measurement definitions and independently authorized data. The existing local
freeze/evaluate tooling supports that workflow; no such cohort or score is
claimed here. An external study also needs owner review of athlete independence,
permissions, and an appropriately frozen evaluation protocol.

Original software is MIT. The source-derived brief, figures, tables, and evidence
retain OBP's CC BY-NC-SA 4.0 terms and additional professional-sports /
financial-analysis affiliation exclusion. Preserve the full attribution and
review [LICENSING.md](LICENSING.md) before reuse.

See [MEASUREMENT_VERIFICATION.md](MEASUREMENT_VERIFICATION.md),
[PHASE2_RESULTS.md](PHASE2_RESULTS.md), and
[REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the underlying methods and evidence.
