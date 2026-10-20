"""Public planning tools for an independently authorized, local-only study."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import streamlit as st

PUBLIC_REPOSITORY = (
    "https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready"
)
TEMPLATE_PATHS = (
    "schemas/new_data_mapping.example.json",
    "schemas/new_data_dictionary.csv",
    "analysis/external_validation_protocol.template.json",
)
WORKFLOW = (
    "uv run --frozen pitching new-data audit --csv local_studies/development.csv "
    "--mapping local_studies/development_mapping.json --output local_studies/development\n\n"
    "uv run --frozen pitching external freeze --prepared local_studies/development "
    "--protocol local_studies/protocol.json --output local_studies/frozen\n\n"
    "uv run --frozen pitching new-data audit --csv local_studies/external.csv "
    "--mapping local_studies/external_mapping.json --output local_studies/external\n\n"
    "uv run --frozen pitching external evaluate --prepared local_studies/external "
    "--bundle local_studies/frozen --output local_studies/evaluation"
)


def planning_files(project_root: Path) -> dict[str, bytes]:
    """Read only the fixed, public templates; never enumerate local study inputs."""
    files: dict[str, bytes] = {}
    for relative in TEMPLATE_PATHS:
        content = (project_root / relative).read_bytes()
        if relative.endswith(".json") and not isinstance(json.loads(content), dict):
            raise ValueError("A planning template must be a JSON object")
        files[Path(relative).name] = content
    files["START_HERE.txt"] = (
        "New-data study planning kit\n\n"
        "These are blank planning templates, not athlete observations or completed results.\n"
        "Complete the mapping and protocol for the actual authorized study before running.\n"
        "Development and external data require separate reviewed mappings and identity checks.\n"
        "Use an approved local/private environment. Public GitHub issues are for non-sensitive introductions.\n"
        "OBP data and derived model bundles retain its professional-affiliation restrictions.\n"
        f"Instructions: {PUBLIC_REPOSITORY}/blob/main/docs/NEW_DATA_GUIDE.md\n"
        f"Evaluation: {PUBLIC_REPOSITORY}/blob/main/docs/EXTERNAL_VALIDATION.md\n"
    ).encode()
    return files


def planning_zip(project_root: Path) -> bytes:
    """Build a reproducible template archive, containing no study records."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in planning_files(project_root).items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return buffer.getvalue()


def render_new_data_lab(project_root: Path) -> None:
    """Describe the runnable local workflow without opening or accepting private data."""
    st.subheader("How would a new dataset be evaluated?")
    st.write(
        "Start with a measurement dictionary and a focused question. Then audit the data, "
        "freeze development models, and evaluate an independently authorized new cohort."
    )
    st.info(
        "Workflow ready · external study pending. No independent evaluation cohort has "
        "been supplied or scored in this demonstration."
    )
    question, workflow = st.columns(2, gap="large")
    with question, st.container(border=True):
        st.markdown("#### Start with the measurements")
        st.write(
            "Agree what one row represents, which athlete and session it belongs to, "
            "the units and sign conventions, and when each measurement becomes available."
        )
        st.write(
            "A peak internal net elbow moment and an external moment, or a peak separation "
            "angle and a foot-plant angle, require a semantic review. Changing a column "
            "name or converting units cannot make those definitions equivalent."
        )
        st.caption(
            "Private measurements stay in an approved local environment. The public "
            "site supplies planning templates and documentation."
        )
    with workflow, st.container(border=True):
        st.markdown("#### A fixed evaluation path")
        st.markdown(
            "1. **Audit development data.** Check identity, units, missingness, and provenance.\n"
            "2. **Freeze the protocol and models.** Learn preprocessing on development data.\n"
            "3. **Audit the external cohort.** Establish permissions, compatible measurements, "
            "and independent athletes.\n"
            "4. **Evaluate without fitting.** Report physical-unit errors, cohort shift, "
            "and unfavorable results."
        )
        st.caption(
            "The implemented workflow concerns new athletes and completed-pitch measurements. "
            "Future-session forecasting requires a different protocol."
        )
    st.download_button(
        "Download the blank study planning kit",
        data=planning_zip(project_root),
        file_name="pitching-new-data-planning-kit.zip",
        mime="application/zip",
        type="primary",
        key="new_data_planning_kit",
    )
    st.caption(
        "The kit contains templates, definitions, and instructions. Complete the actual "
        "permissions, collection protocol, identity namespace, and measurement declarations."
    )
    with st.expander("Run the workflow locally"):
        st.write(
            "Use your project terminal after preparing the real CSVs and completed mapping "
            "and protocol files. The paths below are placeholders for your approved local "
            "study. Use a new output directory for each command."
        )
        st.code(WORKFLOW, language="bash")
        st.caption(
            "local_studies/ is excluded from Git. Review allowed storage and outputs with "
            "the data owner; a Git ignore rule does not establish a private analysis environment."
        )
    with st.expander("What the outputs establish"):
        st.write(
            "The audit records source hashes, a canonical table, missingness, and declared "
            "definitions. Frozen model bundles contain numerical parameters. External "
            "evaluation produces predictions, per-athlete and pooled errors, and descriptive "
            "covariate-shift summaries. Missing targets remain missing."
        )
        st.write(
            "Hashes check file integrity; they cannot authenticate data rights or athlete "
            "independence. Different ID namespaces still require owner confirmation that "
            "development and evaluation athletes are distinct."
        )
    st.markdown(
        f"[Data mapping guide]({PUBLIC_REPOSITORY}/blob/main/docs/NEW_DATA_GUIDE.md) · "
        f"[External evaluation protocol]({PUBLIC_REPOSITORY}/blob/main/docs/EXTERNAL_VALIDATION.md)"
    )
    st.caption(
        "OBP data and derivatives retain their source terms, including professional-sports "
        "and financial-analysis affiliation restrictions. Independently authorized team "
        "work needs appropriate development and evaluation data rights."
    )
