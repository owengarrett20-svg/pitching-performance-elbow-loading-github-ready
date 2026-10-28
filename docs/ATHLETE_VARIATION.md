# Pitcher-to-pitcher versus pitch-to-pitch variation

Version 0.8.0 adds an exploratory analysis to **Study results → Pitcher vs. pitch
variation**. It asks how much of the variation in pitch speed and elbow loading is a
stable difference between pitchers, and whether the speed–elbow-moment relationship
looks the same **within** one pitcher's session as it does **between** pitchers.

This is a follow-on to the [Phase 2 prediction study](PHASE2_RESULTS.md). It was
specified after the dataset had been explored, so it is exploratory: it is not
preregistered, not externally replicated, and not a causal analysis.

## Data and scaling

The verified study table contains 411 fastballs from 100 athletes, one
recorded session per athlete (2–5 pitches each), from the pinned OpenBiomechanics
release. All pitches have speed, peak internal elbow varus moment, mass, and height.

Elbow moment is reported both in N·m and scaled to body size:

`moment_%BW·H = 100 × moment / (mass × 9.80665 m/s² × height)`

The mean scaled moment is 6.79 %BW·H (SD 0.93); the mean raw moment is
111.3 N·m. Mass and height are the released session values.

## Statistics

- **ICC(1)** — one-way random-effects intraclass correlation with the unbalanced
  n₀ adjustment: the share of total variance associated with which pitcher threw.
- **Within-pitcher slope** — each pitch's speed and moment are centered on that
  pitcher's own means; the pooled least-squares slope uses only those deviations.
- **Between-pitcher slope** — least squares on pitcher means, one point per pitcher.
- **Uncertainty** — 5,000 athlete-cluster bootstrap resamples (seed 20261028) with
  95% percentile intervals. Every pitch stays with its pitcher. Intervals describe
  resampling of this cohort only; they exclude measurement and external-population
  uncertainty.

The code is [`src/pitching/athlete_variation.py`](../src/pitching/athlete_variation.py)
and the checks are in [`tests/test_athlete_variation.py`](../tests/test_athlete_variation.py).

## Results

Estimates with 95% athlete-resampled intervals:

| Statistic | All pitchers (100) | College only (75) |
| --- | ---: | ---: |
| Speed variance between pitchers (ICC) | 98% [98%, 99%] | 98% [97%, 99%] |
| Raw elbow-moment variance between pitchers (ICC) | 95% [92%, 97%] | 94% [89%, 97%] |
| Scaled elbow-moment variance between pitchers (ICC) | 92% [88%, 95%] | 92% [87%, 96%] |
| Within-session speed SD, mph | 0.62 [0.54, 0.70] | 0.61 [0.51, 0.71] |
| Within-pitcher slope, %BW·H per mph | 0.072 [0.027, 0.116] | 0.072 [0.018, 0.129] |
| Between-pitcher slope, %BW·H per mph | 0.061 [0.030, 0.092] | 0.069 [0.030, 0.108] |
| Within − between, %BW·H per mph | 0.012 [-0.037, 0.057] | 0.003 [-0.054, 0.058] |
| Within-pitcher slope, N·m per mph | 1.25 [0.45, 2.04] | 1.23 [0.30, 2.24] |
| Between-pitcher slope, N·m per mph | 1.90 [1.26, 2.63] | 1.61 [0.78, 2.47] |
| Within − between, N·m per mph | -0.65 [-1.66, 0.28] | -0.38 [-1.62, 0.82] |

![Scaled elbow moment against pitch speed. Grey points are pitches, orange lines are each pitcher's own fit, and the dashed line fits pitcher means.](images/athlete_variation.png)

## What this shows

1. **Most variation is between pitchers.** Roughly nine-tenths or more of the
   variance in speed and in elbow moment, raw or scaled, is associated with which
   pitcher threw. Within one session, speed varies by only about
   0.6 mph.
2. **Faster pitches carry more scaled elbow moment, within and between pitchers.**
   Within a pitcher's session, each additional mph is associated with about
   0.072 %BW·H more moment, about 1.1% of the cohort mean. Both
   intervals exclude zero.
3. **The two slopes were not distinguishable.** The within − between difference
   interval includes zero on both the scaled and raw scales. Equal slopes are not
   established; the intervals are wide.
4. **The college-only sensitivity subset agrees** in direction and approximate size.

## Limits

- The within-pitcher slope covers a narrow, naturally occurring speed range and
  should not be extrapolated to deliberate larger velocity changes.
- These are associations among completed pitches. They do not show that throwing
  harder causes higher loading in a given pitcher.
- Internal net elbow varus moment is a joint-level loading summary. It is not UCL
  force, tissue strain, or injury risk, and there are no injury labels.
- The cohort is mostly collegiate and from one source; it is not MLB-representative.
- Source data and derived results keep the OpenBiomechanics terms, including the
  professional-sports affiliation restriction. See [LICENSING.md](LICENSING.md).
