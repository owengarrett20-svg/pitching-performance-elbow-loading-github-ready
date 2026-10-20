"""The public collaboration introduction accepts no athlete data or messages."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from streamlit.testing.v1 import AppTest

from pitching.collaboration_view import collaboration_links


def make_app(tmp_path):
    return AppTest.from_string(
        "from pathlib import Path\n"
        "from pitching.collaboration_view import render_collaboration_methods\n"
        f"render_collaboration_methods(Path({str(tmp_path / 'reports')!r}), "
        f"Path({str(tmp_path)!r}))\n",
        default_timeout=20,
    ).run()


def text_blocks(app):
    return "\n".join(
        item.value
        for group in (app.markdown, app.caption, app.info)
        for item in group
        if isinstance(item.value, str)
    )


def test_introduction_link_opens_public_template_without_a_data_payload():
    links = collaboration_links()
    parsed = urlparse(links["introduction"])
    assert parsed.scheme == "https" and parsed.hostname == "github.com"
    assert parsed.path == (
        "/owengarrett20-svg/pitching-performance-elbow-loading-github-ready/issues/new"
    )
    assert parse_qs(parsed.query) == {"template": ["collaboration.yml"]}
    assert links["profile"] == "https://github.com/owengarrett20-svg"
    assert "44b98dae05cceb016f080ab39d105c85b8639084" in links["data_license"]
    assert all("mailto:" not in value for value in links.values())


def test_page_is_readable_without_reports_and_does_not_fetch_fit_or_write(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The public introduction must not fetch, fit, bootstrap, or send")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("pitching.models.evaluate_baselines", forbidden)
    monkeypatch.setattr("pitching.phase2.evaluate_phase2", forbidden)
    monkeypatch.setattr("pitching.phase2.compare_fixed_predictions", forbidden)
    app = make_app(tmp_path)
    assert not app.exception, [item.value for item in app.exception]
    assert not app.error
    assert not list(tmp_path.iterdir())
    copy = text_blocks(app)
    assert "Owen Garrett" in copy and "mechanical engineer" in copy
    assert "External validation remains future work" in copy
    assert "public GitHub issue" in copy
    assert "approved analysis environment before any data transfer" in copy
    assert "specific written paid license" in copy
    assert "professional-sports / financial-analysis affiliation exclusion" in copy
    assert "independently authorized data" in copy
    assert not app.get("file_uploader")
    assert not app.text_input and not app.text_area


def test_download_is_only_the_written_collaboration_guide(tmp_path):
    guide = tmp_path / "docs/COLLABORATION.md"
    guide.parent.mkdir()
    guide.write_text("Synthetic documentation fixture, no athlete observations.\n")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    app = make_app(tmp_path)
    assert not app.exception
    buttons = app.get("download_button")
    assert len(buttons) == 1
    assert buttons[0].label == "Download the collaboration guide"
    assert before == {path: path.read_bytes() for path in before}


def test_linked_issue_template_and_guide_exist_in_the_project():
    root = Path(__file__).resolve().parents[1]
    template = root / ".github/ISSUE_TEMPLATE/collaboration.yml"
    guide = root / "docs/COLLABORATION.md"
    assert template.is_file() and guide.is_file()
    template_text = template.read_text()
    assert "Do not attach data or footage" in template_text
    assert "This issue is public" in template_text
    assert "no team-data upload service" in template_text
    assert "separately reviewed adapter and analysis plan" in guide.read_text()
