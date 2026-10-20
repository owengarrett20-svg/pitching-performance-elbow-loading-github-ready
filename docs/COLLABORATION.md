# Research collaborations and a new-data study

Owen Garrett is a mechanical engineer and biomechanics researcher developing
reproducible work in human movement and baseball. This portfolio demonstrates
source validation, athlete-grouped evaluation, interpretable baselines, and
transparent reporting. It does not claim a professional-team affiliation or an
existing team-data partnership.

The next scientific question is whether fixed definitions and models generalize
to an appropriately licensed independent cohort or later assessment sessions.
External validation remains proposed work. New data can reveal limitations as
well as opportunities; an improvement in performance is not guaranteed.

## Start with a non-sensitive introduction

Use the [research collaboration issue template](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready/issues/new?template=collaboration.yml)
to describe the question and arrange the next conversation. GitHub issues are
public. Share only information that is approved for public discussion:

- The research or measurement question and the decision it would inform.
- Broad measurement types and a non-sensitive description of the collection setting.
- Approximate athlete/session counts, if those aggregates are public-safe.
- Whether permissions and a private contact route can be arranged.

Keep player names, individual measurements, persistent player identifiers, videos,
medical information, raw files, credentials, and confidential organizational
details out of public issues. GitHub's issue editor supports attachments; that
capability is not an invitation to upload athlete data here.

The current application offers no team-data upload service, private storage
portal, or established confidential analysis infrastructure. Agree a private
communication channel and an approved analysis environment before discussing any
data transfer. The [GitHub profile](https://github.com/owengarrett20-svg) and
[project repository](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)
identify the author and work; this document does not publish a private email
address or promise a response time.

## Keep the demonstration and data permissions distinct

The present demonstration uses Driveline's OpenBiomechanics Project (OBP).
Its data, source definitions, and derived material retain CC BY-NC-SA 4.0 plus the
additional professional-sports/financial-analysis affiliation exclusion.
Employees, contractors, associates, and significant shareholders of the excluded
organizations require the licensor's specific written paid license for such use.
Public availability does not remove that condition. Read [LICENSING.md](LICENSING.md)
and the full [pinned upstream terms](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md).

Independently authored software is MIT-licensed. That software license does not
grant rights to OBP measurements, documentation, reports, or visual derivatives.
A prospective team collaboration would form a separate study with independently
authorized data and agreed permissions. Establish rights for every input,
including measurements, footage, derived signals, and any publication of outputs.
Do not transfer restricted OBP material into a new setting under the assumption
that the code license authorizes it.

## Proposed collaboration workflow

### 1. Define a useful, testable question

Agree the target, units, intended population, and timing of the intended use.
Distinguish predicting an already recorded measurement from forecasting a future
session or delivery. Define what a useful baseline and an informative failure
would look like before choosing a model.

The existing study concerns pitch speed and internal net elbow varus moment.
It contains no injury outcomes, tissue-specific force measurements, or causal
mechanics intervention. New research questions require their own evidential
scope rather than inheriting unsupported claims from this demonstration.

### 2. Review a measurement inventory privately

Before data transfer, agree permission, access, retention, allowed outputs, and
the environment in which analysis would take place. A dictionary and collection
protocol can establish much of the technical scope before sharing athlete rows.

| Topic | Information to establish |
| --- | --- |
| Observation unit | What one row represents: pitch, session, athlete, or another unit |
| Grouping | Stable pseudonymous athlete/session/pitch keys and repeated-measure structure |
| Targets | Definitions, units, observed timing, instrument or computation method, and missingness |
| Predictors | Units, coordinate frames, sign conventions, sampling, preprocessing, and when each becomes available |
| Cohort | Collection setting, population, pitch types, sessions, and relevant inclusion rules |
| Motion or video | Actual availability, recording rights, calibration, pitch identity, and verified time mapping |
| Permissions | Who may access inputs, where they may be analyzed, and which outputs may be shared |

Pseudonymous identifiers still require care; keep any identity mapping with the
authorized data owner. Filename patterns can encode outcome information and must
be checked as potential leakage. A shared date or filename does not establish
camera-to-signal synchronization.

### 3. Agree an adapter and freeze the evaluation

The original study workflow remains pinned to the released OBP source and its
recorded sample. The separate [new-data adapter](NEW_DATA_GUIDE.md) now supports
an explicit reviewed mapping for authorized local development and external
datasets. It checks units, measurement declarations, identifiers, and missingness
before the [freeze/evaluate workflow](EXTERNAL_VALIDATION.md). This local tooling
does not establish permission or provide confidential hosting. Preserve the
original study's checksums and specification while defining the new study.
Every new study still needs a separately reviewed adapter and analysis plan.

Validate join cardinality, units, grouping, missingness, and inclusion rules before
model fitting. Keep transformations inside training folds. Set athlete, session,
and time holdouts to match the intended generalization question. A future-session
assessment and a new-athlete assessment are different evaluation targets.

For a genuinely external test, freeze the development specification before
viewing evaluation outcomes. Compare useful simple baselines first. Tuning or
feature selection requires an evaluation design that separates those choices
from the final held-out assessment.

### 4. Return an inspectable result

Agree deliverables appropriate to the question, such as:

- A data dictionary, provenance record, and documented quality/exclusion audit.
- A reproducible environment and an auditable preprocessing/model specification.
- Held-out predictions with athlete/session membership and leakage checks.
- Errors in physical units, including athlete-level summaries and difficult cases.
- Uncertainty estimates with their estimand and assumptions stated.
- Cohort-shift analysis, limitations, and unfavorable or null results.
- A readable report and a local or approved hosted exploration interface.

The scope and form of these deliverables would be agreed for the new study.
This list does not represent a completed collaboration or an existing service.
Performance differences alone do not establish causal mechanical changes or
injury-risk reduction.

## Existing evidence to inspect

- [Current study summary](STUDY_SUMMARY.md)
- [Phase 2 results and all planned comparisons](PHASE2_RESULTS.md)
- [Frozen Phase 2 analysis plan](PHASE2_ANALYSIS_PLAN.md)
- [Reproducibility and artifact checks](REPRODUCIBILITY.md)
- [Variable definitions](VARIABLES.md)
- [Motion/video provenance and alignment limits](VIDEO_METHODS.md)
- [Research roadmap](ROADMAP.md)

These materials describe a transparent research demonstration. They establish
neither an external benchmark nor permission for excluded organizational reuse.
