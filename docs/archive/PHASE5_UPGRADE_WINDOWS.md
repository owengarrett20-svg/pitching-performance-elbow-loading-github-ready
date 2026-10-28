# Upgrade your existing project to Phase 5 on Windows

The public Phase 4 base is `ad4cd71`. Version 0.7.0 adds a searchable source table,
paired measured-marker replays, marker/measurement inspection, and a concise
research brief. It preserves the original analysis sample, models, results, and
source terms. It does not add a completed external study or independently
validated inverse-dynamics calculation.

Use **`pitching-phase5-update.bundle`** with your existing GitHub-connected
project. The separate `pitching-performance-elbow-loading-phase5.zip` is a full
source copy for a fresh folder and contains no Git history or configured remote.
There is no need to create another repository or Streamlit app.

## 1. Download and verify before fetching

Save `pitching-phase5-update.bundle` in your normal **Downloads** folder. Check
its exact filename; browsers can add `(1)` or save in another location.

In VS Code, open your existing project terminal. Stop Streamlit with **Ctrl+C**.
Run commands **one at a time** and stop if any fails.

```powershell
Test-Path "$env:USERPROFILE\Downloads\pitching-phase5-update.bundle"
```

This must print **True**. If it prints False, find the file in your browser's
download list and use its actual path or move it to Downloads. The source ZIP
cannot be used in place of a Git bundle.

```powershell
git bundle verify "$env:USERPROFILE\Downloads\pitching-phase5-update.bundle"
```

Continue only when it says the bundle **“is okay.”** A local bundle error does
not establish a GitHub login problem. If verification fails, stop and redownload
before trying to merge.

## 2. Preserve your working copy and update its history

```powershell
git status
```

Continue with a clean working tree. Commit or preserve your own edits first;
do not discard work or force a merge around unexpected history. The supplied
bundle supports a fast-forward from the published Phase 4 history.

```powershell
git fetch "$env:USERPROFILE\Downloads\pitching-phase5-update.bundle" main
```

If fetch fails, stop. A later “Already up to date” can refer to an old
`FETCH_HEAD` and does not prove this update was installed. After a successful
fetch, run:

```powershell
git merge --ff-only FETCH_HEAD
```

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the **Local URL**. Included reference reports and marker arrays require no
raw C3D archive download, MATLAB license, optional motion-processing dependency,
or model fitting for viewing. The catalog adds approximately 25 MB of prepared
numerical arrays; the large original archive remains excluded from Git.

## 3. Check the interaction you will share

- Open **Explore pitches → Find & compare pitches**.
- Search `pitch 1623_3` or `athlete 970`, select a source table row, and choose Pitch B.
- Confirm the two pitch/athlete headings, marker replays, marker sets, and associated measurements agree.
- Play each independently or start both from their own origins. That convenience does not align foot plant, ball release, or a processed trace.
- Change A/B repeatedly, clear the search, and copy a paired link such as `?page=explore&pitch=1623_3&compare=2916_4`.
- Open **Charts & associations** for the existing exploratory plots and athlete averages.
- Open **Research brief** for methods/results, evidence limits, and downloads. Test the HTML and, if useful, **Print → Save as PDF**.
- Confirm that **Watch motion**, **Athlete reports**, **Study results**, **New-data lab**, and **Methods & collaboration** still work.

The 411 source-linked replays show measured skin markers, not camera footage or
validated anatomical joint centers. The original three MP4/processed-trace
examples remain separately available. Marker and processed-signal clocks are
unverified; missing values stay missing. A corrupt or unavailable recording is
identified instead of replaced with a nearby-speed or different-athlete example.

The brief's twelve source-summary checks compare four released trace maxima in
three examples with released POIs. They do not independently validate dynamics,
all measurements in all pitches, an injury model, or a causal mechanics change.

## 4. Publish to the same repository and address

After previewing, return to the terminal, press **Ctrl+C**, then run:

```powershell
git push origin main
```

Keep the existing repository:
<https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready>.
The deployment continues to use `main`, `streamlit_app.py`, and Python 3.12.
Check the new GitHub **Actions** run and Streamlit rebuild logs. A successful
local test or Git push does not independently verify those services.

The public address remains:
<https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/>.
After rebuilding, verify the **Research brief** view before sharing a link such
as `?page=research`. Phase 5 is not public until the branch is pushed and the
application rebuild succeeds.

## 5. Use the project accurately in applications

Read PHD_APPLICATION_GUIDE.md (kept with private application materials),
[CONTRIBUTIONS_AND_AI.md](../CONTRIBUTIONS_AND_AI.md), and
[RESEARCH_BRIEF.md](../RESEARCH_BRIEF.md). Describe an independent AI-assisted
research software project and your actual contributions, rather than a
publication or personally completed validation that has not happened. Keep
CV-specific drafts and the uploaded CV outside the public repository. Follow
each program's rules for links, supplemental material, and AI assistance.

The software is MIT; source-derived arrays, reports, and documents retain OBP's
CC BY-NC-SA 4.0 terms plus its professional-sports/financial-analysis affiliation
restriction. Review [LICENSING.md](../LICENSING.md) before reuse.
