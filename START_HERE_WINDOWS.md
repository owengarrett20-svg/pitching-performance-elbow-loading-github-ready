# Open the Phase 5 pitching research workspace on Windows

**Updating your existing GitHub-connected project?** Use
[the Phase 5 upgrade guide](docs/PHASE5_UPGRADE_WINDOWS.md). It verifies
`pitching-phase5-update.bundle` before fetching, then preserves your history,
GitHub remote, and existing Streamlit address. Phase 4 is published at `ad4cd71`;
version 0.7.0 adds source-linked comparison and a research brief while retaining
the existing scientific findings.

## Preview a fresh source copy

1. Stop Streamlit with **Ctrl+C** in its terminal.
2. Extract `pitching-performance-elbow-loading-phase5.zip` into a **new folder**.
3. In VS Code, open the folder containing `app.py`, `streamlit_app.py`, `assets`, and this file.
4. Open a PowerShell terminal. Run each command separately and stop if one fails:

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the **Local URL** printed by Streamlit. Viewing the reference application
requires no raw archive download, MATLAB, FFmpeg, model fitting, or optional
motion-processing dependency. Prepared marker arrays and reference reports are
included. The source ZIP has no Git history or configured remote; the bundle is
the update route for your existing connected project.

## Start with one recorded comparison

1. Select **Explore pitches → Find & compare pitches**.
2. Search `pitch 1623_3` or `athlete 970`, or enter literal free-text/numeric terms.
3. Select a table row to make it **Pitch A**. The Pitch A selector also works with a keyboard or touch screen.
4. Choose **Pitch B**. Inspect each pane's source pitch and athlete, play or rotate the marker replays, and read their associated measurements and marker sets.
5. Copy the address to share the selected IDs. A paired link looks like `?page=explore&pitch=1623_3&compare=2916_4`.

The catalog contains source-linked marker replays for all 411 study pitches.
These are measured skin-marker animations, not camera footage or a validated
joint-center skeleton. Starting both from their own first samples does not align
foot plant, ball release, or processed signals. Missing coordinates stay missing.
Unavailable or corrupt evidence is identified rather than replaced by another
pitch's motion. A search with no matches clears the comparison panes.

## Eight focused views

- **Start here:** the question, source example, and main finding.
- **Research brief:** source-derived methods/results, evidence limits, contribution record, and downloadable documents.
- **Explore pitches:** searchable A/B workspace or the existing **Charts & associations** view.
- **Watch motion:** source marker inspection; detailed traces and MP4 clips remain available for the original three examples.
- **Athlete reports:** printable HTML, observations, and provenance for the selected athlete's recorded pitches.
- **Study results:** fixed full-cohort errors, conditional intervals, and detailed audit.
- **New-data lab:** blank templates and local audit/freeze/evaluate instructions for an authorized new study.
- **Methods & collaboration:** definitions, data quality, limitations, and a non-sensitive public introduction route.

Sidebar filters change observations, not the full-cohort model contrasts or
intervals. Athlete reports describe a few pitches from one released assessment;
they do not establish long-term consistency or development.

## Use the project in an application

Read the [PhD application guide](docs/PHD_APPLICATION_GUIDE.md),
[contribution/AI-assistance record](docs/CONTRIBUTIONS_AND_AI.md), and
[research-brief guide](docs/RESEARCH_BRIEF.md). The brief can be opened or printed
to PDF; attach it only where the program permits that format. This is an
independent AI-assisted research software project, not a publication or a
completed external/independent biomechanical validation study. Private CV and
application drafts remain outside the public repository.

## Reproduce the research or evaluate new data

The original [study summary](docs/STUDY_SUMMARY.md),
[Phase 2 results](docs/PHASE2_RESULTS.md), and
[analysis plan](docs/PHASE2_ANALYSIS_PLAN.md) remain unchanged. Use
[REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for the pipeline and source hashes.
The [catalog guide](docs/PITCH_CATALOG.md) describes optional archive-based
repreparation; it is unnecessary for viewing the included arrays.

The [new-data audit](docs/NEW_DATA_GUIDE.md) and
[external-evaluation workflow](docs/EXTERNAL_VALIDATION.md) run locally with
approved inputs. They are implemented tools; no external cohort has been scored
in this release. Keep private data and identity mappings in the agreed
environment, separate from the public snapshot.

## Publish to the same website

Keep the existing repository
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)
and deployment: `main`, `streamlit_app.py`, Python 3.12. Follow
[PHASE5_UPGRADE_WINDOWS.md](docs/PHASE5_UPGRADE_WINDOWS.md), push after previewing,
and check Actions plus Streamlit rebuild logs. Local files do not update the
public site automatically.

OBP-derived arrays, reports, and documents retain the source terms, including
the professional-sports/financial-analysis affiliation restriction. The original
software's MIT license does not grant those data rights. Read
[LICENSING.md](docs/LICENSING.md) before reuse.
