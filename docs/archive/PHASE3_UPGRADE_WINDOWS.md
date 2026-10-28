# Upgrade your existing project to Phase 3 on Windows

Phase 2 is already published in your repository at `a2f339e`. This update adds
the guided research experience, interactive recorded-pitch explorer, and
collaboration documentation. It preserves the models, dataset, and study
findings. It does not add external validation or a confidential upload service.

Use the Git bundle with your existing GitHub-connected folder. The separate
`pitching-performance-elbow-loading-phase3.zip` is a complete source archive
for a fresh copy; it contains no Git history or configured remote.

## 1. Bring the update into your existing folder

Download `pitching-phase3-update.bundle` to your normal **Downloads** folder.
In VS Code, open your existing project and its PowerShell terminal. Stop any
running Streamlit server with **Ctrl+C**. Run these commands one at a time:

```powershell
git status
```

Continue when the working tree is clean. If you have edits, commit or preserve
them first; do not discard them or force a merge to get around a conflict.
The bundle supports a fast-forward from the published Phase 2 commit. If a
later change makes that impossible, stop and inspect the history.

```powershell
git fetch "$env:USERPROFILE\Downloads\pitching-phase3-update.bundle" main
```

```powershell
git merge --ff-only FETCH_HEAD
```

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the **Local URL** printed in the terminal. No raw source download, model
fitting, FFmpeg installation, or motion-capture software is required to view
the included reference demonstration.

## 2. Preview the five views

- **Start here:** question, measured-marker replay, and plain-language findings.
- **Explore pitches:** hover/select chart points, change axes, inspect athlete
  averages, and compare two recorded pitches. Copy the address to share a
  selection. Athlete averages combine released per-pitch peak summaries.
- **Watch motion:** the three prepared marker replays and existing processed
  traces. Most pitches have no prepared replay. Motion and trace clocks have
  no verified alignment; the separate camera example is not a matched pitch.
- **Study results:** outcome comparisons, observed prediction errors, and the
  detailed audit. Full-cohort findings remain unchanged by sidebar filters.
- **Methods & collaboration:** definitions, provenance, limitations, and a
  non-sensitive introduction route for independently authorized future work.

The comparison is descriptive. A difference between recorded pitches does not
estimate what would happen if an athlete changed their mechanics. Elbow varus
moment is a net joint-level moment, not an injury prediction.

## 3. Publish the update to the same website

When the local preview looks right, return to the terminal, press **Ctrl+C**,
and run:

```powershell
git push origin main
```

Keep the existing remote and repository:
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready).
There is no need to create a second GitHub repository or a second Streamlit app.
The existing deployment uses `main`, `streamlit_app.py`, and Python 3.12. Check
GitHub **Actions** and Streamlit deployment logs after pushing; Phase 3 is not
public until the branch has been pushed and the deployment has rebuilt.

The current public address remains:
<https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/>.

## Reproduce or extend the research separately

The verified reference reports are included. To run the developer checks:

```powershell
uv sync --frozen --extra dev
uv run --frozen pitching fetch
uv run --frozen pytest -q
```

For a full analysis rebuild, follow [REPRODUCIBILITY.md](../REPRODUCIBILITY.md).
Do not regenerate or relabel research results just to change the presentation.
OBP's professional-sports affiliation exclusion still applies to these data;
the original software's MIT license does not grant restricted data rights.
See [COLLABORATION.md](../COLLABORATION.md) for the next scientific milestone:
an appropriately authorized external or longitudinal validation study with a
frozen evaluation protocol.
