"""Readable methods and a source-independent research collaboration introduction.

This page describes a proposed collaboration process. It does not accept data,
contact anybody, fit models, or imply that an external cohort has been evaluated.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

PROFILE_URL = "https://github.com/owengarrett20-svg"
REPOSITORY_URL = f"{PROFILE_URL}/pitching-performance-elbow-loading-github-ready"
SOURCE_COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
DATA_LICENSE_URL = (
    f"https://github.com/drivelineresearch/openbiomechanics/blob/{SOURCE_COMMIT}/LICENSE-DATA.md"
)


def collaboration_links() -> dict[str, str]:
    """Return public introduction and documentation links, without data payloads."""
    return {
        "introduction": f"{REPOSITORY_URL}/issues/new?{urlencode({'template': 'collaboration.yml'})}",
        "profile": PROFILE_URL,
        "project": REPOSITORY_URL,
        "study": f"{REPOSITORY_URL}/blob/main/docs/PHASE2_RESULTS.md",
        "guide": f"{REPOSITORY_URL}/blob/main/docs/COLLABORATION.md",
        "data_license": DATA_LICENSE_URL,
    }


def render_collaboration_methods(report_dir: Path, project_root: Path) -> None:
    """Render the introduction without consuming or changing athlete reports.

    ``report_dir`` follows the common page-router interface. This introductory
    page deliberately works before a study run and reads no athlete records.
    """
    links = collaboration_links()
    st.subheader("A research question worth testing")
    st.write(
        "I’m Owen Garrett, a mechanical engineer and biomechanics researcher "
        "building reproducible work in human movement and baseball. "
        "My goal is to make the measurements, evaluation, and uncertainty easy to inspect."
    )
    about, process = st.columns(2, gap="large")
    with about, st.container(border=True):
        st.markdown("#### What this project demonstrates")
        st.write(
            "A documented path from source measurements to a checked analysis table, "
            "predictions for withheld athletes, and a report that retains uncertain results."
        )
        st.markdown(
            f"[Read the study]({links['study']}) · "
            f"[Inspect the code]({links['project']}) · "
            f"[View my GitHub profile]({links['profile']})"
        )
    with process, st.container(border=True):
        st.markdown("#### A useful next research question")
        st.write(
            "Do the same definitions and fixed models work in a genuinely new cohort "
            "or a later assessment session? That requires appropriately authorized data "
            "and a new evaluation plan. External validation remains future work."
        )

    st.subheader("How a collaboration could start")
    st.markdown(
        "1. **Define the decision.** Describe the performance or measurement question "
        "and the result that would help your research.\n"
        "2. **Describe the measurements.** Begin with a variable dictionary, units, "
        "collection protocol, and approximate athlete/session counts.\n"
        "3. **Agree the evaluation.** Set athlete, session, and time boundaries before "
        "scoring; compare against simple baselines.\n"
        "4. **Inspect the evidence.** Review data quality, held-out errors, uncertainty, "
        "and limitations together, including unfavorable findings."
    )
    st.caption(
        "This is a proposed process for a separately authorized study. "
        "The current project does not provide a team-data upload service or a completed external benchmark."
    )

    st.info(
        "OBP data and derivatives retain CC BY-NC-SA 4.0 plus an additional "
        "professional-sports / financial-analysis affiliation exclusion. "
        "Those uses require a specific written paid license from the licensor. "
        f"[Read the pinned terms]({links['data_license']}). "
        "The original software’s MIT license covers the software only. "
        "Future team work needs independently authorized data and agreed permissions."
    )

    st.link_button(
        "Introduce a research question",
        links["introduction"],
        type="primary",
        width="stretch",
    )
    st.caption(
        "This opens a public GitHub issue. Share a non-sensitive introduction only. "
        "Keep player identities, individual measurements, videos, medical information, "
        "files, and credentials out of public issues. Agree a private communication "
        "channel and an approved analysis environment before any data transfer."
    )

    with st.expander("How to read the evaluation"):
        st.markdown(
            "**Withheld athletes:** every pitch from an athlete stays outside the model’s "
            "training set when that athlete is evaluated.\n\n"
            "**Average error per athlete:** calculate each athlete’s average absolute error, "
            "then average those values equally. This is the primary comparison.\n\n"
            "**Conditional intervals:** resample whole athletes from the saved held-out "
            "errors while keeping model pairs together. These intervals exclude full "
            "model-training and external-population uncertainty.\n\n"
            "**Joint loading:** internal net elbow moment is a mechanical summary. "
            "The study has no injury outcomes and establishes no causal coaching intervention."
        )
    with st.expander("Reproduce the study or plan a new dataset"):
        st.code(
            "uv sync --frozen --extra dev\n"
            "uv run --frozen pitching fetch\n"
            "uv run --frozen pitching phase2 --offline\n"
            "uv run --frozen pytest -q",
            language="bash",
        )
        st.write(
            "The current command reproduces the pinned OBP study. A new dataset needs "
            "a reviewed adapter, compatible variable definitions, and its own frozen "
            "evaluation plan before results are interpreted."
        )
        st.markdown(f"[Read the collaboration guide]({links['guide']})")
        guide = Path(project_root) / "docs/COLLABORATION.md"
        if guide.is_file():
            st.download_button(
                "Download the collaboration guide",
                data=guide.read_bytes(),
                file_name="COLLABORATION.md",
                mime="text/markdown",
                key="collaboration_guide_download",
            )
