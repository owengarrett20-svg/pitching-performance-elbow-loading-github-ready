"""Hosted, read-only demo entry point for Streamlit Community Cloud.

Use app.py for locally regenerated research reports. This entry point verifies
the bundled reference snapshot and performs no network requests or model fitting.
"""

import sys
from pathlib import Path

# Explicit source path also supports deployment hosts that install locked third-
# party dependencies without installing this repository's editable package.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import streamlit as st

from pitching.deployment import verified_demo_reports


def main() -> None:
    try:
        reports = verified_demo_reports(PROJECT_ROOT)
    except (OSError, ValueError) as exc:
        st.set_page_config(page_title="Pitching research demo", layout="wide")
        st.error(f"The reference snapshot failed verification: {exc}")
        st.info(
            "Restore the committed assets/demo files or rebuild the snapshot before deployment."
        )
        return
    from app import main as research_dashboard

    research_dashboard(report_dir_override=reports, bundled_demo=True)


if __name__ == "__main__":
    main()
