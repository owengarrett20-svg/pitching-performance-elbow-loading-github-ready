"""A source-bound research case study for reviewers, without new statistical fits.

The brief distinguishes reproduced source summaries, software checks, internal
held-out prediction, and the independent validation that remains unperformed.
It does not turn a portfolio artifact into a publication or a claim of sole work.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from pitching import __version__
from pitching.data import COMMIT, VARIABLES
from pitching.deployment import verified_demo_reports
from pitching.measurement_audit import audit_measurement_summaries, audit_summary
from pitching.models import FEATURES
from pitching.phase2_dashboard import TARGETS, load_phase2_reports
from pitching.research_story import StorySummary, primary_story_summary

PROJECT_URL = "https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready"
APP_URL = "https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/"
SOURCE_URL = f"https://github.com/drivelineresearch/openbiomechanics/tree/{COMMIT}"
LICENSE_URL = f"https://github.com/drivelineresearch/openbiomechanics/blob/{COMMIT}/LICENSE-DATA.md"
QUESTION = (
    "Do completed-pitch rotational summaries add predictive information beyond age, "
    "body mass, and height for pitch speed and peak internal elbow varus moment in held-out athletes?"
)
MODEL_LABELS = {
    "dummy_mean": "Training-fold mean",
    "ridge_anthropometric": "Age + body size",
    "ridge_kinematic": "Rotation summaries",
    "ridge_combined": "Combined",
}
AI_STATEMENT = (
    "Project framing and requirements by Owen Garrett; code and documentation developed "
    "with AI assistance. Personal review, execution, and modifications should be described "
    "accurately in the contribution record. This brief makes no claim of sole implementation."
)
DATA_TERMS = (
    "Source: Driveline Baseball Research & Development, OpenBiomechanics Project. "
    "Source data, definitions, and this source-derived brief retain CC BY-NC-SA 4.0 plus "
    "the additional professional-sports / financial-analysis affiliation exclusion. "
    "Those uses require the licensor's specific written paid license. Original software "
    "is MIT; that license does not grant restricted data or model-use rights."
)


@dataclass(frozen=True)
class ResearchBrief:
    """Verified study facts plus a separately scoped source-summary audit."""

    cohort: dict
    settings: dict
    metrics: pd.DataFrame
    primary: tuple[StorySummary, ...]
    measurement_rows: pd.DataFrame
    measurement_summary: dict
    evidence: pd.DataFrame
    provenance: dict
    created_utc: str


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _bound_quality(report_dir: Path) -> tuple[dict, pd.DataFrame, dict]:
    parent_bytes = (report_dir / "run_metadata.json").read_bytes()
    parent = json.loads(parent_bytes)
    expected = parent.get("artifacts_sha256", {})
    payloads = {}
    for name in ("audit.json", "missingness.csv"):
        contents = (report_dir / name).read_bytes()
        if _sha(contents) != expected.get(name):
            raise ValueError(f"Research brief quality artifact checksum mismatch: {name}")
        payloads[name] = contents
    audit = json.loads(payloads["audit.json"])
    if (
        audit.get("status") != "passed"
        or audit.get("cardinality") != "one_to_one"
        or audit.get("source_commit") != COMMIT
    ):
        raise ValueError("The brief requires the passed one-to-one audit of the pinned OBP data")
    missingness = pd.read_csv(io.BytesIO(payloads["missingness.csv"]))
    required = {"table", "column", "n_rows", "n_missing"}
    if not required.issubset(missingness):
        raise ValueError("The brief missingness artifact lacks required columns")
    hashes = {name: _sha(content) for name, content in payloads.items()}
    hashes["parent_run_metadata.json"] = _sha(parent_bytes)
    return audit, missingness, hashes


def build_research_brief(
    project_root: Path,
    report_dir: Path | None = None,
    *,
    created_utc: datetime | None = None,
) -> ResearchBrief:
    """Read verified reports, quality records, and prepared traces without fitting.

    The default is the hash-verified public snapshot. An explicit directory may
    hold a locally reproduced OBP run; it must pass the same source and binding
    checks. This is not an importer for a confidential or external cohort.
    """
    root = Path(project_root).resolve()
    reports_path = (
        Path(report_dir).resolve() if report_dir is not None else verified_demo_reports(root)
    )
    reports = load_phase2_reports(reports_path)
    if reports.metadata.get("source_commit") != COMMIT:
        raise ValueError("The public research brief requires the pinned OBP source")
    analysis = reports.analysis
    required = {"session_pitch", "user", "session", *FEATURES, *VARIABLES}
    if not required.issubset(analysis):
        raise ValueError("The brief analysis table lacks required identities or measurements")
    if analysis[["session_pitch", "user", "session"]].isna().any().any():
        raise ValueError("The brief requires complete pitch, athlete, and session identifiers")
    if analysis.groupby("session").user.nunique().gt(1).any():
        raise ValueError("A source session cannot belong to multiple athletes")
    audit, missingness, quality_hashes = _bound_quality(reports_path)
    counts = analysis.groupby("user").size()
    sessions_per_athlete = analysis.groupby("user").session.nunique()
    if not sessions_per_athlete.eq(1).all():
        raise ValueError("The pinned-source brief requires one released assessment per athlete")
    for name in {*FEATURES, *VARIABLES}:
        values = pd.to_numeric(analysis[name], errors="raise").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError("The brief analysis contains nonfinite observed measurements")
    focal_missing = {
        name: int(pd.to_numeric(analysis[name], errors="raise").isna().sum()) for name in VARIABLES
    }
    if (
        audit.get("n_joined_pitches") != len(analysis)
        or audit.get("n_athletes") != len(counts)
        or audit.get("n_sessions") != analysis.session.nunique()
        or audit.get("requested_variables_missing") != focal_missing
    ):
        raise ValueError("The quality audit does not describe the verified analysis cohort")
    source_missing = missingness.loc[missingness.table.eq("poi")]
    if source_missing.column.duplicated().any():
        raise ValueError("The source missingness report has duplicate variable records")
    if not source_missing.n_rows.eq(len(analysis)).all():
        raise ValueError("The source missingness report has inconsistent observation counts")
    for name, missing in focal_missing.items():
        row = source_missing.loc[source_missing.column.eq(name), "n_missing"]
        if len(row) != 1 or float(row.iloc[0]) != missing:
            raise ValueError("Focal missingness differs between source audit and analysis")
    if source_missing.n_missing.lt(0).any() or source_missing.n_missing.gt(len(analysis)).any():
        raise ValueError("The source missingness report has invalid missing counts")
    metrics = reports.metrics.copy()
    for target in TARGETS:
        rows = metrics.loc[metrics.target.eq(target)]
        if rows.n_pitches.nunique() != 1 or rows.n_athletes.nunique() != 1:
            raise ValueError("Model comparisons require a shared eligible cohort per outcome")
    primary = tuple(primary_story_summary(reports, target) for target in TARGETS)
    spec = reports.spec
    n_splits = spec.get("n_splits")
    alpha = spec.get("models", {}).get("ridge_combined", {}).get("alpha")
    if n_splits is None or alpha is None:
        raise ValueError("The brief requires a declared fold count and fixed ridge penalty")
    expected_features = {
        "dummy_mean": [],
        "ridge_anthropometric": list(FEATURES[:3]),
        "ridge_kinematic": list(FEATURES[3:]),
        "ridge_combined": list(FEATURES),
    }
    if (
        spec.get("group") != "user"
        or spec.get("splitter") != "GroupKFold"
        or spec.get("shared_target_and_model_folds") is not True
        or set(spec.get("models", {})) != set(expected_features)
        or set(spec.get("targets", [])) != set(TARGETS)
    ):
        raise ValueError("The brief requires the declared shared athlete-grouped baseline design")
    for model, features in expected_features.items():
        declared_model = spec["models"][model]
        if declared_model.get("features") != features or (
            model != "dummy_mean" and declared_model.get("alpha") != alpha
        ):
            raise ValueError(
                "The brief requires the declared fixed predictor groups and common ridge penalty"
            )
    seeds = sorted(int(seed) for seed in reports.sensitivity.partition_seed.unique())
    declared = spec.get("sensitivity", {}).get("partition_seeds")
    if declared is not None and sorted(declared) != seeds:
        raise ValueError("Saved sensitivity partitions differ from the declared specification")
    try:
        rows = audit_measurement_summaries(root, analysis)
        measurement_summary = audit_summary(rows)
    except (OSError, ValueError, KeyError, TypeError) as error:
        rows = pd.DataFrame()
        measurement_summary = {
            "n_checks": 0,
            "n_passed": 0,
            "n_failed": 0,
            "n_unavailable": 0,
            "all_passed": False,
            "scope": "source_scalar_reproduction_only",
            "interpretation": (
                f"Measurement audit unavailable ({type(error).__name__}); inspect the source "
                "assets and audit records. No successful source reproduction is claimed."
            ),
        }
    source_state = (
        f"{measurement_summary['n_passed']}/{measurement_summary['n_checks']} source checks passed"
        if measurement_summary.get("all_passed") is True
        else "Unresolved or unavailable"
    )
    evidence = pd.DataFrame(
        [
            (
                "Source provenance / join",
                "Passed source audit",
                "Pinned files; one-to-one pitch join; recorded missingness.",
            ),
            (
                "Released scalar reproduction",
                source_state,
                "Finite maxima of supplied traces compared with supplied POIs; not new ground truth.",
            ),
            (
                "Within-source prediction",
                "Athlete-held-out assessment",
                f"{n_splits} shared athlete-grouped folds; learned preprocessing stays in training folds.",
            ),
            (
                "Software behavior",
                "See release verification",
                "Automated and browser checks exercise integrity, missingness, grouping, and frozen evaluation.",
            ),
            (
                "Independent inverse dynamics",
                "Not performed",
                "Joint moments are released source outputs; no independent dynamics reconstruction.",
            ),
            (
                "External cohort validation",
                "Not performed",
                "Local freeze/evaluate tooling is implemented; no independent cohort has been supplied.",
            ),
            (
                "Marker–signal synchronization",
                "Unverified",
                "A matching sample grid does not establish a shared time origin or camera alignment.",
            ),
            (
                "Injury / causal intervention",
                "Outside scope",
                "No injury outcomes, tissue-specific forces, or causal mechanics intervention.",
            ),
        ],
        columns=["evidence", "status", "interpretation"],
    )
    created = created_utc or datetime.now(UTC)
    if created.tzinfo is None:
        raise ValueError("Brief creation time must include a timezone")
    cohort = {
        "n_pitches": len(analysis),
        "n_athletes": len(counts),
        "n_sessions": int(analysis.session.nunique()),
        "pitches_per_athlete_min": int(counts.min()),
        "pitches_per_athlete_max": int(counts.max()),
        "sessions_per_athlete_min": int(sessions_per_athlete.min()),
        "sessions_per_athlete_max": int(sessions_per_athlete.max()),
        "focal_missing": focal_missing,
        "source_columns_with_missing": int(
            (source_missing.n_missing.gt(0) & ~source_missing.column.isin(VARIABLES)).sum()
        ),
        "pitch_types": audit.get("pitch_types", {}),
    }
    settings = {
        "n_splits": int(n_splits),
        "ridge_alpha": float(alpha),
        "primary_seed": spec.get("primary_seed"),
        "n_partitions": len(seeds),
        "partition_seeds": seeds,
        "bootstrap_replicates": int(primary[0].resamples),
        "plan_status": "exploratory follow-on planned after Phase 1 results had been viewed; not preregistered",
        "prediction_scope": "retrospective completed-pitch measurements in held-out athletes from the same source setting",
    }
    provenance = {
        "schema_version": 1,
        "application_version": __version__,
        "source_commit": COMMIT,
        "source_repository": SOURCE_URL,
        "project_repository": PROJECT_URL,
        "dashboard": APP_URL,
        "analysis_sha256": reports.metadata["analysis_sha256"],
        "study_plan_sha256": reports.metadata.get("plan_sha256"),
        "producing_project_commit": reports.metadata.get("project_git_commit"),
        "producing_project_dirty": reports.metadata.get("project_git_dirty"),
        "producing_code_sha256": reports.metadata.get("project_code_sha256"),
        "dependency_lock_sha256": reports.metadata.get("uv_lock_sha256"),
        "phase2_metadata_sha256": _sha((reports_path / "phase2/run_metadata.json").read_bytes()),
        "quality_artifacts_sha256": quality_hashes,
        "measurement_audit_scope": measurement_summary.get("scope"),
        "assistance_statement": AI_STATEMENT,
        "data_terms": DATA_TERMS,
        "license_url": LICENSE_URL,
        "publication_status": "independent research-software portfolio; not a peer-reviewed publication or completed external-validation study",
    }
    return ResearchBrief(
        cohort,
        settings,
        metrics,
        primary,
        rows,
        measurement_summary,
        evidence,
        provenance,
        created.astimezone(UTC).isoformat(),
    )


def _comparison_text(summary: StorySummary) -> str:
    uncertainty = (
        "The interval includes zero; the incremental predictive value remains uncertain."
        if summary.interval_includes_zero
        else "This within-source contrast does not establish an intervention effect or external performance."
    )
    return (
        f"{summary.title}: combined − age/body-size equal-athlete MAE "
        f"{summary.difference:+.3f} {summary.unit}; conditional {summary.level * 100:g}% interval "
        f"[{summary.low:+.3f}, {summary.high:+.3f}] {summary.unit}. {uncertainty}"
    )


def _metrics_table(brief: ResearchBrief) -> pd.DataFrame:
    table = brief.metrics.pivot(index="model", columns="target", values="athlete_mae")
    table = table.reindex(index=list(MODEL_LABELS), columns=list(TARGETS))
    table.index = [MODEL_LABELS[model] for model in table.index]
    return table.rename(
        columns={name: f"{label} ({unit})" for name, (label, unit) in TARGETS.items()}
    )


def brief_markdown(brief: ResearchBrief) -> str:
    """A concise plain-text case study using the same verified numbers as the HTML."""
    c, settings = brief.cohort, brief.settings
    table = _metrics_table(brief)
    model_lines = ["| Model | " + " | ".join(table.columns) + " |", "| --- | ---: | ---: |"]
    model_lines.extend(
        "| " + name + " | " + " | ".join(f"{value:.3f}" for value in row) + " |"
        for name, row in table.iterrows()
    )
    evidence = "\n".join(
        f"- **{row.evidence}: {row.status}.** {row.interpretation}"
        for row in brief.evidence.itertuples(index=False)
    )
    return (
        "# Pitching Performance and Elbow Loading\n\n"
        "Owen Garrett · AI-assisted research-software portfolio\n\n"
        "Independent exploratory software artifact; not a peer-reviewed publication.\n\n"
        f"**Research question.** {QUESTION}\n\n"
        f"**Source cohort.** {c['n_pitches']} pitches, {c['n_athletes']} athletes, "
        f"{c['n_sessions']} sessions; {c['pitches_per_athlete_min']}–{c['pitches_per_athlete_max']} "
        "recorded pitches per athlete. These are repeated observations, not independent pitches.\n\n"
        f"**Data audit.** One-to-one pitch join. Focal missing values: {sum(c['focal_missing'].values())}. "
        f"Other source POI columns with missing observations: {c['source_columns_with_missing']}. "
        "Missing outcomes are never imputed.\n\n"
        f"**Design.** {settings['n_splits']} shared athlete-grouped folds, primary seed "
        f"{settings['primary_seed']}; fixed ridge alpha {settings['ridge_alpha']:g}. "
        "Training-only median imputation, missingness indicators, and standardization. "
        "Predictor groups contain age/mass/height, three rotational peaks, or all six; both outcomes, "
        "IDs, and filenames are excluded from predictors. The plan followed viewed Phase 1 results; "
        "this is exploratory, not preregistered or independently confirmatory.\n\n"
        "## Saved results\n\nEqual-athlete MAE averages within athlete, then across athletes equally. "
        "Lower is closer to observed measurements.\n\n"
        + "\n".join(model_lines)
        + "\n\n"
        + "\n\n".join(_comparison_text(summary) for summary in brief.primary)
        + "\n\n"
        f"Intervals use {settings['bootstrap_replicates']:,} paired athlete resamples of fixed "
        "out-of-fold errors; they exclude full model-refitting uncertainty. "
        f"The {settings['n_partitions']} overlapping refitted partitions are descriptive sensitivity "
        "checks, not independent replications or confidence intervals.\n\n"
        "## Evidence and limitations\n\n" + evidence + "\n\n"
        "The source cohort is primarily collegiate. Each athlete has one released assessment; "
        "the data do not establish longitudinal development. Peak separation is not the foot-plant "
        "angle. Net elbow moment does not isolate UCL force or predict injury.\n\n"
        "## Next research question\n\n"
        "Do frozen definitions and models generalize to an independently authorized cohort with "
        "compatible measurements? Freeze development choices before viewing evaluation outcomes, "
        "establish athlete independence with the owner, and report declines as well as improvements.\n\n"
        f"## Contribution and assistance\n\n{AI_STATEMENT}\n\n"
        f"[Contribution record]({PROJECT_URL}/blob/main/docs/CONTRIBUTIONS_AND_AI.md). "
        "Use application links or attachments only where the program permits them.\n\n"
        f"## Reproduce and inspect\n\n[Source code]({PROJECT_URL}) · [Dashboard]({APP_URL}) · "
        f"[Pinned source]({SOURCE_URL})\n\n"
        "```bash\nuv sync --frozen --extra dev\nuv run --frozen pitching fetch\n"
        "uv run --frozen pitching phase2 --offline\nuv run --frozen pytest -q\n```\n\n"
        f"Analysis SHA-256: `{brief.provenance['analysis_sha256']}`. "
        f"Producing project revision: `{brief.provenance['producing_project_commit']}`.\n\n"
        f"{DATA_TERMS} [Full source terms]({LICENSE_URL}).\n\n"
        f"Generated (UTC) {brief.created_utc}; application version {brief.provenance['application_version']}.\n"
    )


def _score_svg(brief: ResearchBrief, target: str) -> str:
    label, unit = TARGETS[target]
    rows = brief.metrics.loc[brief.metrics.target.eq(target)].set_index("model")
    high = max(float(rows.athlete_mae.max()), 0.001)
    marks = []
    for index, model in enumerate(MODEL_LABELS):
        value = float(rows.loc[model, "athlete_mae"])
        y = 23 + index * 25
        width = value / high * 150
        color = "#007c91" if model == "ridge_combined" else "#708493"
        marks.append(
            f'<text x="3" y="{y + 10}" font-size="10">{_safe(MODEL_LABELS[model])}</text>'
            f'<rect x="130" y="{y}" width="{width:.4f}" height="13" rx="2" fill="{color}"/>'
            f'<text x="{137 + width:.4f}" y="{y + 10}" font-size="10">{value:.2f}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 139" role="img" '
        f'aria-label="{_safe(label)} equal-athlete errors in {_safe(unit)}">'
        f"<title>{_safe(label)}: lower error is closer</title>"
        f'<text x="3" y="12" font-size="11" font-weight="700">{_safe(label)} ({_safe(unit)})</text>'
        + "".join(marks)
        + '<text x="130" y="136" font-size="9">Equal-athlete MAE · lower is closer</text></svg>'
    )


def brief_html(brief: ResearchBrief) -> str:
    """Two print pages, self-contained SVG/HTML, and responsive reading on screen."""
    c, s = brief.cohort, brief.settings
    metrics = _metrics_table(brief)
    header = "".join(f"<th>{_safe(name)}</th>" for name in metrics.columns)
    result_rows = "".join(
        f'<tr><th scope="row">{_safe(name)}</th>'
        + "".join(f"<td>{float(value):.3f}</td>" for value in row)
        + "</tr>"
        for name, row in metrics.iterrows()
    )
    contrasts = "".join(
        f'<div class="contrast"><strong>{_safe(item.title)}</strong>'
        f"<p>Combined − age/body-size MAE: <b>{item.difference:+.3f} {_safe(item.unit)}</b>.</p>"
        f"<p>Conditional {item.level * 100:g}% interval: [{item.low:+.3f}, {item.high:+.3f}] {_safe(item.unit)}.</p>"
        f"<p>{'Increment remains uncertain: interval includes zero.' if item.interval_includes_zero else 'Within-source error contrast; no causal intervention or external-performance claim.'}</p></div>"
        for item in brief.primary
    )
    evidence_rows = "".join(
        f'<tr><th scope="row">{_safe(row.evidence)}</th><td><b>{_safe(row.status)}</b><br>'
        f"{_safe(row.interpretation)}</td></tr>"
        for row in brief.evidence.itertuples(index=False)
    )
    if not brief.measurement_rows.empty:
        cells = []
        for row in brief.measurement_rows.itertuples(index=False):
            peak = (
                f"{float(row.computed_peak):.4f}" if pd.notna(row.computed_peak) else "Unavailable"
            )
            source = (
                f"{float(row.published_poi):.4f}" if pd.notna(row.published_poi) else "Unavailable"
            )
            cells.append(
                f"<tr><td>{_safe(row.session_pitch)}</td><td>{_safe(row.label)}</td>"
                f"<td>{peak}</td><td>{source}</td><td>{_safe(row.unit)}</td><td>{_safe(row.status)}</td></tr>"
            )
        measurement_rows = "".join(cells)
        measurement_table = (
            '<div class="table-wrap"><table class="audit"><thead><tr><th>Pitch</th><th>Released quantity</th>'
            "<th>Trace max</th><th>POI</th><th>Unit</th><th>Check</th></tr></thead><tbody>"
            + measurement_rows
            + "</tbody></table></div>"
        )
    else:
        measurement_table = '<p class="notice">Source-summary audit is unavailable; no successful reproduction is claimed.</p>'
    status = brief.measurement_summary
    if status.get("all_passed") is True:
        check_text = f"{status['n_passed']} of {status['n_checks']} source comparisons passed"
    elif status.get("n_checks", 0):
        check_text = (
            f"Unresolved source checks: {status.get('n_failed', 0)} failed, "
            f"{status.get('n_unavailable', 0)} unavailable"
        )
    else:
        check_text = "Source-summary audit unavailable; no successful reproduction claimed"
    plots = "".join(_score_svg(brief, target) for target in TARGETS)
    provenance = brief.provenance
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pitching Performance and Elbow Loading — research brief</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#edf2f5;color:#172b3a;font:14px/1.42 system-ui,-apple-system,Segoe UI,sans-serif}}
.sheet{{max-width:900px;margin:24px auto;padding:34px;background:white;border-top:6px solid #007c91;box-shadow:0 3px 18px #172b3a14}}
h1{{font-size:29px;line-height:1.12;margin:0 0 8px}}h2{{font-size:18px;margin:18px 0 7px}}p{{margin:6px 0}}.eyebrow{{font-size:12px;color:#486274;margin-bottom:8px}}.muted,.caption{{color:#4f6574;font-size:12px}}
.stats,.contrasts,.plots{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.stats{{grid-template-columns:repeat(3,minmax(0,1fr));margin:15px 0}}.stat,.contrast{{background:#f2f7f8;border:1px solid #dce7ea;border-radius:6px;padding:11px}}.stat b{{font-size:22px;display:block}}.stat span{{font-size:12px}}.question{{border-left:4px solid #007c91;padding:8px 12px;background:#f5f9fa}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:6px 7px;border-bottom:1px solid #dce4e9;text-align:left;vertical-align:top}}th{{font-weight:650}}.results td{{text-align:right;font-variant-numeric:tabular-nums}}.results thead th{{background:#f1f6f8}}.evidence th{{width:30%}}.audit{{font-size:10px}}.audit th,.audit td{{padding:3px 5px}}.audit td:nth-child(3),.audit td:nth-child(4){{font-variant-numeric:tabular-nums}}
.plots{{margin-top:9px}}svg{{width:100%;height:auto;display:block}}.contrast p{{font-size:12px}}.notice{{padding:8px 10px;background:#fff6e9;border-left:3px solid #b37424}}a{{color:#006c80;overflow-wrap:anywhere}}.hash{{font:10px/1.4 ui-monospace,monospace;overflow-wrap:anywhere}}.foot{{border-top:1px solid #dce4e9;margin-top:14px;padding-top:9px;font-size:10px;color:#496170}}.screen-only{{max-width:900px;margin:15px auto;padding:0 12px;font-size:12px}}
@media(max-width:640px){{.sheet{{margin:0 0 16px;padding:19px 15px;box-shadow:none}}h1{{font-size:25px}}.stats{{gap:6px}}.stat{{padding:9px 7px}}.stat b{{font-size:20px}}.contrasts,.plots{{grid-template-columns:1fr}}.table-wrap{{overflow-x:auto}}.audit{{min-width:570px}}.evidence{{font-size:11px}}}}
@page{{size:A4;margin:11mm}}
@media print{{body{{background:white;font-size:9.2pt;line-height:1.27}}.sheet{{width:auto;max-width:none;margin:0;padding:0;border-top:3px solid #007c91;box-shadow:none;break-after:page}}.sheet:last-of-type{{break-after:auto}}.screen-only{{display:none}}h1{{font-size:20pt}}h2{{font-size:12pt;margin:10px 0 5px}}.eyebrow,.caption,.muted,.contrast p{{font-size:8pt}}.stats{{margin:9px 0;gap:8px}}.stat,.contrast{{padding:7px}}.stat b{{font-size:16pt}}.stat span{{font-size:8pt}}table{{font-size:8pt}}th,td{{padding:4px 5px}}.audit{{font-size:7pt}}.audit th,.audit td{{padding:2px 3px}}.plots{{gap:10px;margin-top:4px}}.plots svg{{max-height:112px}}.foot{{font-size:7pt;margin-top:8px;padding-top:5px}}.hash{{font-size:7pt}}h2,thead{{break-after:avoid}}tr,.contrast,.stat{{break-inside:avoid}}a{{text-decoration:none}}}}
</style></head><body>
<p class="screen-only">Two-page research brief. Use your browser’s Print → Save as PDF. Links or attachments should follow each program’s application instructions.</p>
<section class="sheet"><div class="eyebrow">Owen Garrett · AI-assisted research-software portfolio · v{_safe(provenance["application_version"])}</div>
<h1>Pitching Performance<br>and Elbow Loading</h1><p class="muted">Exploratory analysis of Driveline’s OpenBiomechanics Project · independent project, not a peer-reviewed publication.</p>
<div class="stats"><div class="stat"><b>{c["n_pitches"]}</b><span>recorded pitches</span></div><div class="stat"><b>{c["n_athletes"]}</b><span>athletes</span></div><div class="stat"><b>{c["pitches_per_athlete_min"]}–{c["pitches_per_athlete_max"]}</b><span>pitches per athlete</span></div></div>
<p class="question"><strong>Research question.</strong> {_safe(QUESTION)}</p>
<h2>Design and data trust</h2><p>One-to-one source pitch join; {c["n_sessions"]} sessions. Missing focal values: {sum(c["focal_missing"].values())}; {c["source_columns_with_missing"]} other POI columns contain missing observations. Missing outcomes remain missing.</p>
<p>{s["n_splits"]} shared athlete-grouped folds (seed {_safe(s["primary_seed"])}); four fixed baselines; ridge alpha {s["ridge_alpha"]:g}. Training-only median imputation, missingness indicators, and standardization. Predictors are age/mass/height, three rotational peaks, or all six. Outcomes, IDs, and filenames are excluded.</p>
<p class="caption">The comparison plan followed viewed Phase 1 results. This is exploratory, not preregistered or independently confirmatory. Predictors describe a completed pitch, not a pre-pitch forecast.</p>
<h2>Saved athlete-held-out results</h2><p class="caption">Equal-athlete MAE: average absolute error within athlete, then average athletes equally. Lower is closer.</p>
<table class="results"><thead><tr><th>Model</th>{header}</tr></thead><tbody>{result_rows}</tbody></table>
<div class="plots">{plots}</div><div class="contrasts">{contrasts}</div>
<p class="caption">Intervals use {s["bootstrap_replicates"]:,} paired athlete resamples of fixed out-of-fold errors and exclude full model-refitting uncertainty. The {s["n_partitions"]} overlapping refitted partitions are descriptive sensitivity checks, not independent replications or confidence intervals.</p>
<p class="notice">The source cohort is primarily collegiate and each athlete has one released assessment. These results do not establish external performance, longitudinal development, causal coaching effects, or injury risk.</p>
<footer class="foot"><a href="{PROJECT_URL}">Source code</a> · <a href="{APP_URL}?page=research">Research dashboard</a> · <a href="{PROJECT_URL}/blob/main/docs/PHASE2_RESULTS.md">Full exploratory results</a><br>{_safe(DATA_TERMS)} <a href="{LICENSE_URL}">Full source terms</a>.</footer></section>
<section class="sheet"><div class="eyebrow">Evidence, reproducibility, and next research question</div><h2 style="margin-top:0">What this work establishes</h2>
<table class="evidence"><tbody>{evidence_rows}</tbody></table>
<h2>Released-signal reproduction audit</h2><p class="caption"><strong>{_safe(check_text)}.</strong> Full-trace signed finite maxima versus published POIs; absolute tolerance 0.0001 in each quantity’s native units reflects source rounding, not physical accuracy or independent biomechanical validation. Trace gaps remain missing.</p>
{measurement_table}
<h2>A defensible next study</h2><p>Evaluate frozen definitions and models in an independently authorized cohort with compatible measurement conventions. Establish athlete independence with the data owner and freeze development choices before viewing evaluation outcomes. Report cohort shift and unfavorable results. Local audit/freeze/evaluate tooling is implemented; this study remains unperformed.</p>
<h2>Contribution and assistance</h2><p class="caption">{_safe(AI_STATEMENT)} <a href="{PROJECT_URL}/blob/main/docs/CONTRIBUTIONS_AND_AI.md">Contribution record</a>.</p>
<h2>Inspect the evidence</h2><p class="caption"><a href="{SOURCE_URL}">Pinned OBP source</a> · <a href="{PROJECT_URL}/blob/main/docs/MEASUREMENT_VERIFICATION.md">Measurement audit</a> · <a href="{PROJECT_URL}/blob/main/docs/REPRODUCIBILITY.md">Reproduction instructions</a> · <a href="{PROJECT_URL}/blob/main/docs/PHASE5_VALIDATION.md">Release checks</a></p>
<p class="hash">OBP commit: {COMMIT}<br>Analysis SHA-256: {_safe(provenance["analysis_sha256"])}<br>Producing project revision: {_safe(provenance["producing_project_commit"])}</p>
<footer class="foot">Net elbow varus moment is joint-level loading, not isolated UCL force. Peak hip–shoulder separation is not specifically separation at foot plant. Marker and processed-signal clocks remain unverified.<br>Generated (UTC) {_safe(brief.created_utc)}. Source-derived brief: retained OBP data terms; original software MIT. <a href="{LICENSE_URL}">Full source license</a>.</footer></section>
</body></html>"""


def brief_metadata_json(brief: ResearchBrief) -> str:
    """Retain machine-readable facts and hashes without private local file paths."""
    record = {
        **brief.provenance,
        "created_utc": brief.created_utc,
        "cohort": brief.cohort,
        "settings": brief.settings,
        "primary_comparisons": [asdict(summary) for summary in brief.primary],
        "model_metrics": json.loads(brief.metrics.to_json(orient="records")),
        "measurement_summary": brief.measurement_summary,
        "evidence": json.loads(brief.evidence.to_json(orient="records")),
        "measurement_audit_csv_sha256": _sha(brief.measurement_rows.to_csv(index=False).encode()),
        "evidence_csv_sha256": _sha(brief.evidence.to_csv(index=False).encode()),
    }
    return json.dumps(_jsonable(record), indent=2, allow_nan=False) + "\n"


def export_research_brief(
    project_root: Path, output_dir: Path, report_dir: Path | None = None
) -> dict:
    """Export source-bound public artifacts into a new directory, preserving existing files."""
    root, output = Path(project_root).resolve(), Path(output_dir).resolve()
    if output.exists():
        raise ValueError("The research brief output directory must be new")
    protected = root / "assets/demo"
    if output == root or output.is_relative_to(protected):
        raise ValueError("Research brief exports must not replace the source or reference snapshot")
    if report_dir is not None and output.is_relative_to(Path(report_dir).resolve()):
        raise ValueError("Research brief output must remain separate from input reports")
    brief = build_research_brief(root, report_dir)
    payloads = {
        "research-brief.html": brief_html(brief).encode(),
        "research-brief.md": brief_markdown(brief).encode(),
        "research-brief-provenance.json": brief_metadata_json(brief).encode(),
        "measurement-reproduction.csv": brief.measurement_rows.to_csv(index=False).encode(),
        "evidence-summary.csv": brief.evidence.to_csv(index=False).encode(),
    }
    output.mkdir(parents=True)
    try:
        for name, payload in payloads.items():
            (output / name).write_bytes(payload)
        manifest = {name: _sha(payload) for name, payload in payloads.items()}
        (output / "export-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    except OSError:
        shutil.rmtree(output)
        raise
    return {"files": manifest, "measurement_summary": brief.measurement_summary}


def render_research_brief(project_root: Path, report_dir: Path) -> None:
    """A faculty-readable evidence view using verified saved outputs only."""
    st.subheader("Research brief")
    st.write(QUESTION)
    st.caption("Owen Garrett · AI-assisted research-software portfolio · exploratory evidence")
    try:
        brief = build_research_brief(project_root, report_dir)
    except (OSError, ValueError, TypeError, KeyError) as error:
        st.error(f"The research brief cannot be verified: {error}")
        st.info("Restore the complete verified reports before using this brief in an application.")
        return
    cohort = brief.cohort
    first, second, third = st.columns(3)
    first.metric("Recorded pitches", cohort["n_pitches"])
    second.metric("Athletes", cohort["n_athletes"])
    third.metric("Sessions", cohort["n_sessions"])
    st.caption(
        f"{cohort['pitches_per_athlete_min']}–{cohort['pitches_per_athlete_max']} recorded pitches "
        "per athlete; repeated observations from one released assessment each."
    )
    st.download_button(
        "Download the printable research brief (HTML)",
        brief_html(brief),
        file_name="pitching-research-brief.html",
        mime="text/html",
        key="research_brief_html",
        type="primary",
        width="stretch",
    )
    st.caption("Open the HTML and use Print → Save as PDF. It contains two designed print pages.")
    text, metadata = st.columns(2)
    text.download_button(
        "Plain-text brief (Markdown)",
        brief_markdown(brief),
        file_name="pitching-research-brief.md",
        mime="text/markdown",
        key="research_brief_markdown",
        width="stretch",
    )
    metadata.download_button(
        "Evidence and provenance (JSON)",
        brief_metadata_json(brief),
        file_name="pitching-research-brief-provenance.json",
        mime="application/json",
        key="research_brief_metadata",
        width="stretch",
    )
    st.markdown("#### What the comparisons found")
    st.dataframe(_metrics_table(brief), width="stretch")
    st.caption("Equal-athlete mean absolute error: lower is closer to the recorded outcome.")
    for summary in brief.primary:
        st.write(_comparison_text(summary))
    st.caption(
        "Conditional intervals resample saved errors. They exclude full training-set/model-refitting "
        "uncertainty. Overlapping partition refits are descriptive, not independent replication."
    )
    st.markdown("#### Evidence and limits")
    st.dataframe(brief.evidence, hide_index=True, width="stretch")
    if brief.measurement_summary.get("all_passed") is not True:
        st.warning(
            "The released-scalar audit is unresolved or unavailable. No successful source-summary "
            "reproduction is claimed; inspect the individual records."
        )
    with st.expander("Inspect the released-scalar checks"):
        st.caption(
            "Source-summary reproduction compares maxima of supplied traces with supplied scalar "
            "POIs. It does not independently validate inverse dynamics or establish clock alignment."
        )
        st.dataframe(brief.measurement_rows, hide_index=True, width="stretch")
        st.download_button(
            "Measurement audit CSV",
            brief.measurement_rows.to_csv(index=False),
            file_name="measurement-reproduction.csv",
            mime="text/csv",
            key="research_brief_audit",
        )
    st.markdown("#### Contribution and next question")
    st.write(AI_STATEMENT)
    st.write(
        "The next scientific study is a frozen external evaluation on an independently authorized "
        "cohort with compatible definitions. The tooling is ready; that cohort and study are pending."
    )
    st.markdown(
        f"[Contribution and assistance record]({PROJECT_URL}/blob/main/docs/CONTRIBUTIONS_AND_AI.md) · "
        f"[Measurement verification]({PROJECT_URL}/blob/main/docs/MEASUREMENT_VERIFICATION.md)"
    )
    st.caption(DATA_TERMS)
