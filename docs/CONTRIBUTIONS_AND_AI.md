# Contributions and AI assistance

Pitching Performance and Elbow Loading is an independent research software
portfolio organized by Owen Garrett. Its purpose is to make a biomechanics
question, source measurements, model evaluation, and limitations inspectable.
It is not a publication, a completed independent external-validation study, or
a claim that its owner personally wrote every line of code.

## Contribution record

The record below reflects the work confirmed for this project. Update it when
additional personal review, implementation, or independent replication has
actually been completed.

| Contribution | Current record |
| --- | --- |
| Research purpose and scope | The owner specified the sports-biomechanics question, OBP source, reproducibility goals, grouped evaluation requirement, and intended research/portfolio audience. |
| Product and research requirements | The owner guided successive requirements for exploratory analysis, motion inspection, reporting, and a local new-data workflow, and requested searchable records linked to replay, markers, and measurements. |
| Deployment and interface review | The owner deployed the site using the documented workflow and confirmed reviewing the complete Streamlit interface. |
| Implementation and draft documentation | AI assistance contributed substantially to the Python implementation, tests, interface code, methods drafts, and release materials. These contributions should not be represented as unaided personal coding. |
| Executed software checks | Development agents ran automated checks and local browser checks. Those executions are recorded in the release evidence; they are distinct from a personally executed replication by the owner. |
| Personal code-level and methodological review | Complete personal review of every calculation, test, coordinate convention, and statistical assumption has not been confirmed. Record the specific items reviewed and commands rerun before making stronger claims. |
| Original data collection and source processing | Driveline Baseball Research & Development produced the released OBP data and source processing. The portfolio owner did not collect these athletes' measurements. |

The independent-project label describes the project setting and ownership. It
does not establish sole implementation, faculty supervision, organizational
endorsement, or independent validation of the underlying biomechanical model.

## What the evidence supports

The source and saved artifacts support inspection of pitch-level measurements,
one-to-one data preparation, repeated-athlete structure, fixed baseline models,
and held-out errors within the released cohort. Tests can establish software
behavior such as correct grouping, frozen preprocessing, missing-value handling,
and agreement with specified calculations.

Comparing maxima of released processed traces with released scalar summaries is
a source-reproduction check. It does not independently reconstruct inverse
dynamics, establish marker–signal clock alignment, or validate a physiological
mechanism. Athlete-grouped cross-validation assesses prediction within the
source setting; it is not a new independent external cohort.

Read the [research brief](RESEARCH_BRIEF.md),
[measurement-verification scope](MEASUREMENT_VERIFICATION.md),
[Phase 2 analysis plan](PHASE2_ANALYSIS_PLAN.md), and
[results](PHASE2_RESULTS.md) for the corresponding evidence and limitations.

## Using the project in an application or interview

Describe what you personally did, what the software does, what assistance was
used, and what evidence remains unavailable. Those are four different statements.
A capability of the project is not automatically a personally demonstrated skill.

A concise contribution statement consistent with the current record is:

> I defined the project goals and requirements, guided AI-assisted implementation,
> deployed the application, and reviewed its interface. The implementation and
> draft documentation were substantially AI-assisted. I distinguish the checks
> executed during development from the code and methods I have personally
> reviewed or replicated.

Use that statement only where it accurately represents the work at the time of
submission. If personal contributions expand, document concrete changes,
experiments, review notes, and commands before revising the statement.

Useful evidence of personal understanding includes being able to explain the
source variables and signs, demonstrate why a random pitch split can leak athlete
information, calculate the two MAE weightings on a small example, trace a saved
prediction to its held-out athlete, and identify the uncertainty excluded by the
conditional bootstrap. A test count alone does not demonstrate that understanding.

Follow each application's published authorship and AI-use rules. Application
drafts and interview notes should support an accurate explanation in the
applicant's own voice. Do not imply personal completion of a task solely because
the repository contains code for it.

## Source credit and reuse

Credit Driveline's OpenBiomechanics Project separately from the original
software. OBP data and derived materials retain CC BY-NC-SA 4.0 with the
additional professional-sports/financial-analysis affiliation exclusion. The
software's MIT license does not grant restricted data or model-use rights.
See [LICENSING.md](LICENSING.md).

No institution, research group, professional team, or source-data provider is
claimed to endorse this independent portfolio. Keep any unrelated appointment,
publication, or presentation distinct from this project.
