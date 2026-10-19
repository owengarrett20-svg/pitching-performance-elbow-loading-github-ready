# Research and portfolio roadmap

The goal is a reviewable research project with defensible claims. Each stage has
an explicit question and a completion criterion. Later stages are proposals, not
completed analyses or promised improvements to the current scores.

## 1. Make the existing study publication-ready

Here, publication means a clearly labeled software/research release, not a claim
of peer review.

- Connect the local project to a GitHub repository, run CI on a fresh checkout,
  and reproduce the pinned-data analysis and dashboard smoke checks.
- Review the [study summary](STUDY_SUMMARY.md), license notices, variable units,
  manifests, and source citations. Keep restricted derived material separate from
  the original code's MIT license.
- Publish a tagged software release only after checks pass. Add an archive DOI
  only if a real archival service issues one; update citation metadata with the
  actual repository/release URLs.
- Present the data audit, held-out error plots, and a short walkthrough. Explain
  which visuals are observed motion, processed traces, and teaching schematics.

**Done when:** another researcher can reproduce the reported metrics from the
README, identify the sample and evaluation unit, and understand the license and
measurement limits without reading application code.

## 2. Prespecify a small scientific extension

**Question:** How much predictive information do the released rotational summaries
add beyond anthropometrics in this cohort?

Before running comparisons, commit an analysis addendum defining anthropometrics
only (age, mass, height), kinematics only (the three current rotational summaries),
and the combined six-feature model. Use the same athlete partitions and target
definitions for a paired comparison. Keep preprocessing within training folds.
If regularization is tuned, use inner athlete-grouped folds and reserve outer
folds for evaluation. The already-viewed Phase 1 results remain exploratory;
document any choices they informed.

**Done when:** all planned models, exclusions, pooled and equal-athlete errors,
and negative/null findings are reported. Do not choose a winning explanation
from a set of unreported feature searches.

## 3. Quantify uncertainty at the athlete level

**Question:** How sensitive are the descriptive error differences to the sampled
athletes and partition choices?

Specify an athlete-cluster resampling procedure, interval target, seed, and number
of replicates before calculation. Resampling fixed out-of-fold athlete errors
describes uncertainty conditional on the fitted folds; it does not include all
training/model-selection uncertainty. If the goal is full-pipeline uncertainty,
use a design that refits the complete grouped procedure and explain its limits.
Keep paired model comparisons together within athletes. Fold-to-fold variation
alone is not a confidence interval.

**Done when:** code reproduces the stated intervals and the report explains their
estimand and limitations. No uncertainty interval is claimed in current results.

## 4. Establish external or temporal validation

**Question:** Do the fixed definitions and model generalize to a genuinely new
cohort or later assessment sessions?

First obtain an appropriately licensed dataset and document compatibility of
instrumentation, units, populations, and signal conventions. Freeze the model
specification before evaluating the new data. Keep athlete identities separated
across development and evaluation; distinguish new sessions from new athletes.
Revisit permissions before any professional-team or commercial use.

**Done when:** provenance, permission, cohort shift, missingness, and external
errors are reported even if performance declines. The existing 100-session
dataset cannot supply a future-session holdout by itself.

## 5. Study time-resolved mechanics with verified alignment

**Question:** What temporal relationships can the released marker and processed
signals support beyond isolated peaks?

Start with the three verified examples and specify event definitions, anatomical
frames, signal signs, filtering, sampling, and the analysis window. Resolve the
documented shoulder-velocity convention and establish marker/signal clock mapping
before synchronized overlays or event-frame labels. Independent replication of
inverse dynamics would require its model inputs and assumptions; matching a
published trace maximum is not that validation.

Only add camera analysis when the recording's rights, calibration, pitch identity,
and synchronization are established. There is no assumption that video exists
for all study pitches, and no MLB footage acquisition is planned.

**Done when:** the measured quantities and alignment are validated and uncertainty
is stated. Camera angles alone must not be relabeled as joint moments or injury
scores.
