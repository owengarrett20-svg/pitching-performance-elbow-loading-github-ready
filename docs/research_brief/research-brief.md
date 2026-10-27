# Pitching Performance and Elbow Loading

Owen Garrett · AI-assisted research-software portfolio

Independent exploratory software artifact; not a peer-reviewed publication.

**Research question.** Do completed-pitch rotational summaries add predictive information beyond age, body mass, and height for pitch speed and peak internal elbow varus moment in held-out athletes?

**Source cohort.** 411 pitches, 100 athletes, 100 sessions; 2–5 recorded pitches per athlete. These are repeated observations, not independent pitches.

**Data audit.** One-to-one pitch join. Focal missing values: 0. Other source POI columns with missing observations: 25. Missing outcomes are never imputed.

**Design.** 5 shared athlete-grouped folds, primary seed 42; fixed ridge alpha 10. Training-only median imputation, missingness indicators, and standardization. Predictor groups contain age/mass/height, three rotational peaks, or all six; both outcomes, IDs, and filenames are excluded from predictors. The plan followed viewed Phase 1 results; this is exploratory, not preregistered or independently confirmatory.

## Saved results

Equal-athlete MAE averages within athlete, then across athletes equally. Lower is closer to observed measurements.

| Model | Pitch speed (mph) | Peak internal elbow varus moment (N·m) |
| --- | ---: | ---: |
| Training-fold mean | 3.807 | 15.662 |
| Age + body size | 3.542 | 12.404 |
| Rotation summaries | 3.530 | 15.557 |
| Combined | 3.153 | 12.104 |

Pitch speed: combined − age/body-size equal-athlete MAE -0.389 mph; conditional 95% interval [-0.749, -0.029] mph. This within-source contrast does not establish an intervention effect or external performance.

Elbow loading: combined − age/body-size equal-athlete MAE -0.299 N·m; conditional 95% interval [-1.218, +0.628] N·m. The interval includes zero; the incremental predictive value remains uncertain.

Intervals use 5,000 paired athlete resamples of fixed out-of-fold errors; they exclude full model-refitting uncertainty. The 10 overlapping refitted partitions are descriptive sensitivity checks, not independent replications or confidence intervals.

## Evidence and limitations

- **Source provenance / join: Passed source audit.** Pinned files; one-to-one pitch join; recorded missingness.
- **Released scalar reproduction: 12/12 source checks passed.** Finite maxima of supplied traces compared with supplied POIs; not new ground truth.
- **Within-source prediction: Athlete-held-out assessment.** 5 shared athlete-grouped folds; learned preprocessing stays in training folds.
- **Software behavior: See release verification.** Automated and browser checks exercise integrity, missingness, grouping, and frozen evaluation.
- **Independent inverse dynamics: Not performed.** Joint moments are released source outputs; no independent dynamics reconstruction.
- **External cohort validation: Not performed.** Local freeze/evaluate tooling is implemented; no independent cohort has been supplied.
- **Marker–signal synchronization: Unverified.** A matching sample grid does not establish a shared time origin or camera alignment.
- **Injury / causal intervention: Outside scope.** No injury outcomes, tissue-specific forces, or causal mechanics intervention.

The source cohort is primarily collegiate. Each athlete has one released assessment; the data do not establish longitudinal development. Peak separation is not the foot-plant angle. Net elbow moment does not isolate UCL force or predict injury.

## Next research question

Do frozen definitions and models generalize to an independently authorized cohort with compatible measurements? Freeze development choices before viewing evaluation outcomes, establish athlete independence with the owner, and report declines as well as improvements.

## Contribution and assistance

Project framing and requirements by Owen Garrett; code and documentation developed with AI assistance. Personal review, execution, and modifications should be described accurately in the contribution record. This brief makes no claim of sole implementation.

[Contribution record](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready/blob/main/docs/CONTRIBUTIONS_AND_AI.md). Use application links or attachments only where the program permits them.

## Reproduce and inspect

[Source code](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready) · [Dashboard](https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/) · [Pinned source](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084)

```bash
uv sync --frozen --extra dev
uv run --frozen pitching fetch
uv run --frozen pitching phase2 --offline
uv run --frozen pytest -q
```

Analysis SHA-256: `83c751ae903ce5f62a12e0678159c275e456c004f88c1f164caa191cf63b0b14`. Producing project revision: `77dea84e6d03985fb145172f1f721e7168909480`.

Source: Driveline Baseball Research & Development, OpenBiomechanics Project. Source data, definitions, and this source-derived brief retain CC BY-NC-SA 4.0 plus the additional professional-sports / financial-analysis affiliation exclusion. Those uses require the licensor's specific written paid license. Original software is MIT; that license does not grant restricted data or model-use rights. [Full source terms](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md).

Generated (UTC) 2026-10-27T12:41:07.282861+00:00; application version 0.7.0.
