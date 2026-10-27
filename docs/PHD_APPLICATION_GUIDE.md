# Presenting the project in PhD applications

This project can support an application as an **independent, AI-assisted research
software project**. Its value is a traceable question, inspectable evidence, and
careful evaluation. It should complement substantive research experience and
should not be listed as a peer-reviewed publication or a completed independent
biomechanical validation study.

## Give a reviewer a short path through the work

Offer a brief description and two stable links:

- [Live application](https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/)
- [Source and reproducibility documentation](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)

After the Phase 5 release is pushed and rebuilt, the application's **Research
brief** view provides a short route through the question, methods, results,
verification, and limitations. A downloaded brief can accompany an application
only where the program permits that format. A local release is not automatically
the version displayed by the live site; check the published revision before
submission.

The [research-brief guide](RESEARCH_BRIEF.md) explains its generation and evidence
sources. The brief and repository do not establish that the applicant personally
implemented or replicated every method. Use the
[contribution record](CONTRIBUTIONS_AND_AI.md) to distinguish those claims.

## Where the project belongs

| Application location | Appropriate use |
| --- | --- |
| CV: Selected Research Software or Independent Projects | A title, year, one or two accurate contribution bullets, and source/application links. |
| Statement of purpose | A short example of a research question, methodological judgment, or next question that connects to the applicant's wider research interests. |
| Website or portfolio field | The repository and live application, with a concise research description. |
| Permitted supplemental material | The concise research brief, if the program accepts that type and length of material. |
| Interview | A reproducible example the applicant can explain, including assistance, assumptions, errors, and uncompleted validation. |

Keep formal research appointments, manuscripts, presentations, and independent
software projects in their appropriate sections. Preserve publication status
exactly: an in-preparation manuscript, submitted abstract, presented poster, and
accepted publication are different records.

Do not bypass word limits, upload unsolicited supplements, or assume every
program accepts portfolios. Verify each program's current instructions, research
fit, and authorship/AI-use requirements before submitting.

## A concise project description

> An AI-assisted Python/Streamlit research software portfolio examining recorded
> pitch speed, rotational kinematics, and internal net elbow varus moment in
> Driveline's OpenBiomechanics Project. It combines source auditing,
> athlete-grouped baseline evaluation, inspectable measured-marker examples,
> and explicit limits on measurement interpretation and generalization.

This describes the project. Pair it with an accurate account of the applicant's
own contribution; do not turn it into a claim of unaided implementation or
independent data collection.

## Claims to preserve accurately

- **Measurements:** elbow varus moment is a released internal net joint moment,
  not an injury probability, isolated ligament force, or safe-loading threshold.
- **Source reproduction:** checking a released trace maximum against a released
  scalar does not independently validate inverse dynamics or tissue loading.
- **Prediction:** athlete-grouped held-out errors concern the released cohort.
  The project has not evaluated an independent external cohort.
- **Uncertainty:** the paired athlete-cluster intervals condition on saved
  out-of-fold predictions; they exclude uncertainty from retraining the complete
  pipeline. Repeated partitions are descriptive sensitivity checks.
- **Planning:** the Phase 2 plan was frozen after Phase 1 had been viewed. It is
  an exploratory follow-on, not a preregistered confirmatory study.
- **Motion:** marker replay, processed trace, and camera availability must be
  checked separately for the selected source pitch in the current verified
  catalog. Marker and processed-signal controls have no verified shared time
  origin. A separate official camera example is not a matched recording of the
  analyzed pitches.
- **Authorship:** project ownership, AI-assisted implementation, agent-executed
  checks, and personal method review must remain distinguishable.
- **Rights:** professional-team interest does not remove OBP's affiliation
  restriction. Future work needs appropriate independent data permissions.

## Prepare to discuss one defensible example

Choose one recorded pitch and trace its identifier through the source table,
measurement definition, prepared replay availability, and saved model error.
Then explain one cohort-level contrast and why it does not establish an effect
of changing mechanics. Be able to identify a useful failure, such as uncertain
incremental prediction of elbow moment, as well as a favorable result.

Before claiming a personally completed analysis, keep a short dated record of
the commands run, code inspected, assumptions checked, and any changes made.
Record unresolved questions rather than replacing them with a claim of complete
validation. The [new-data workflow](EXTERNAL_VALIDATION.md) is a proposal-ready
tool for a separately authorized study, not evidence that that study has occurred.

## Public and private materials

This public guide intentionally contains no CV, contact details, institution-
specific application narrative, or private application drafts. Tailored materials
should remain outside the public repository unless their owner explicitly
chooses to publish them. Submission wording should reflect the current verified
record and the applicant's own understanding at the time of submission.
