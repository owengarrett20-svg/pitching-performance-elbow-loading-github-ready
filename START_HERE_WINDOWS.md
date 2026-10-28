# Run the pitching research dashboard on Windows

The hosted dashboard needs no installation:
<https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/>.
Use these steps to run the same reference app on your own computer.

## 1. Get the code and run it

Install [Git](https://git-scm.com/download/win) and
[uv](https://docs.astral.sh/uv/getting-started/installation/). Then, in PowerShell,
run each command separately and stop if one fails:

```powershell
git clone https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready.git
```

```powershell
cd pitching-performance-elbow-loading-github-ready
```

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the **Local URL** that Streamlit prints. Prepared marker arrays and verified
reference reports are included, so viewing needs no raw-data download, MATLAB,
FFmpeg, or model fitting. Stop the app with **Ctrl+C**.

To update an existing clone later, run `git pull` from its folder, then
`uv sync --frozen`.

## 2. Try one comparison

1. Open **Explore pitches → Find & compare pitches**.
2. Search `athlete 970` or `pitch 1623_3`, or open **Chart · pick a point**.
3. With **Pitch A** selected under *A row or chart click opens*, click a row or a point.
   Switch to **Pitch B** and click another.
4. Play or rotate the two measured-marker replays, then read the measurements and
   cohort percentiles below them. **Swap A and B** and
   **B: next pitch by athlete …** change the pair in one click.
5. Copy the browser address to share the pair, for example
   `?page=explore&pitch=1623_3&compare=2916_4`.

Replays show measured skin markers, not camera footage. Each keeps its own clock,
so starting both together does not align foot plant or ball release.

## 3. Read the research

- [Two-page research brief (PDF)](docs/research_brief/research-brief.pdf)
- [Study summary](docs/STUDY_SUMMARY.md) and [Phase 2 results](docs/PHASE2_RESULTS.md)
- [Pitcher vs. pitch variation](docs/ATHLETE_VARIATION.md) — also under
  **Study results → Pitcher vs. pitch variation** in the app
- [Contribution and AI-assistance record](docs/CONTRIBUTIONS_AND_AI.md)

To regenerate every result from the pinned source files, follow
[REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md). The
[new-data audit](docs/NEW_DATA_GUIDE.md) and
[external-evaluation workflow](docs/EXTERNAL_VALIDATION.md) run locally on
independently authorized data; no external cohort has been scored.

## Data terms

The software is MIT-licensed. OpenBiomechanics data and everything derived from
it, including arrays, reports, figures, and documents, keep CC BY-NC-SA 4.0 plus
the professional-sports/financial-analysis affiliation restriction. Read
[LICENSING.md](docs/LICENSING.md) before reuse.
