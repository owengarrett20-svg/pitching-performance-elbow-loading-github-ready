"""Read-only, printable reports of recorded observations and verified held-out errors.

Reports never fit a model, infer missing measurements, rank technique, or treat
one released session as evidence of longitudinal development.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape

import numpy as np
import pandas as pd

from pitching import __version__
from pitching.data import COMMIT, REPOSITORY, VARIABLES
from pitching.phase2_dashboard import Phase2Reports

DATA_TERMS = (
    "OBP measurements and derived reports retain CC BY-NC-SA 4.0 with the additional "
    "professional-sports / financial-analysis affiliation restriction. Such use requires "
    "the licensor's specific written paid license. The software's MIT license does not "
    "grant those data rights."
)
LICENSE_URL = f"{REPOSITORY}/blob/{COMMIT}/LICENSE-DATA.md"
MODEL = "ridge_combined"
ERROR_COLUMNS = [
    "session_pitch",
    "user",
    "target",
    "fold",
    "observed",
    "predicted",
    "residual",
    "absolute_error",
]


@dataclass(frozen=True)
class AthleteReport:
    """Scoped observations, optional verified errors, and their provenance."""

    athlete_id: str
    pitches: pd.DataFrame
    summary: pd.DataFrame
    predictions: pd.DataFrame
    metadata: dict
    notices: tuple[str, ...]


def _number(value: object, digits: int = 2) -> str:
    try:
        numeric = float(value)
    except (ValueError, TypeError):
        return "Missing"
    return f"{numeric:,.{digits}f}" if np.isfinite(numeric) else "Missing"


def _safe(value: object) -> str:
    return escape(str(value), quote=True)


def _numeric(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.copy()
    for column in VARIABLES:
        try:
            table[column] = pd.to_numeric(table[column], errors="raise").astype(float)
        except (ValueError, TypeError) as error:
            raise ValueError(f"Report measurement {column} must be numeric or missing") from error
        if np.isinf(table[column]).any():
            raise ValueError(f"Report measurement {column} contains an infinite value")
    return table


def _reference_matches(selected: pd.DataFrame, reports: Phase2Reports) -> bool:
    reference = reports.analysis.copy()
    reference["session_pitch"] = reference.session_pitch.astype(str)
    reference["user"] = reference.user.astype(str)
    wanted = selected.session_pitch.tolist()
    reference = reference.loc[reference.session_pitch.isin(wanted)].set_index("session_pitch")
    observed = selected.set_index("session_pitch")
    if set(reference.index) != set(observed.index) or reference.index.duplicated().any():
        return False
    reference = reference.reindex(observed.index)
    if not reference.user.equals(observed.user):
        return False
    for column in VARIABLES:
        if column not in reference:
            return False
        values = pd.to_numeric(reference[column], errors="coerce").to_numpy(dtype=float)
        if not np.allclose(
            values, observed[column].to_numpy(), equal_nan=True, atol=1e-9, rtol=1e-9
        ):
            return False
    return (
        "session" not in selected
        or "session" not in reference
        or reference.session.astype(str).equals(observed.session.astype(str))
    )


def matched_predictions(selected: pd.DataFrame, reports: Phase2Reports) -> pd.DataFrame:
    """Read primary combined OOF rows only after identity, values, and folds agree."""
    if not _reference_matches(selected, reports):
        raise ValueError("Selected observations differ from the verified study table")
    payload = reports.verified_bytes.get("phase2_oof_predictions.csv")
    assignments_payload = reports.verified_bytes.get("phase2_fold_assignments.csv")
    if payload is None or assignments_payload is None:
        raise ValueError("Verified primary predictions and fold assignments are unavailable")
    predictions = pd.read_csv(
        io.BytesIO(payload), dtype={"session_pitch": "string", "user": "string"}
    )
    if not {*ERROR_COLUMNS, "model"}.issubset(predictions):
        raise ValueError("The saved predictions are missing report fields")
    predictions = predictions.loc[
        predictions.model.eq(MODEL) & predictions.session_pitch.isin(selected.session_pitch)
    ].copy()
    if predictions.duplicated(["session_pitch", "target"]).any():
        raise ValueError("The primary predictions contain repeated pitch/outcome rows")
    expected = {
        (str(row.session_pitch), target)
        for row in selected.itertuples(index=False)
        for target in ("pitch_speed_mph", "elbow_varus_moment")
        if pd.notna(getattr(row, target))
    }
    if set(zip(predictions.session_pitch, predictions.target)) != expected:
        raise ValueError("Saved primary predictions do not cover the report's observed outcomes")
    assignments = pd.read_csv(
        io.BytesIO(assignments_payload), dtype={"session_pitch": "string", "user": "string"}
    )
    if not {"session_pitch", "user", "fold"}.issubset(assignments):
        raise ValueError("The saved fold assignments are incomplete")
    if assignments.session_pitch.duplicated().any():
        raise ValueError("Saved fold assignments must have one row per pitch")
    assignments = assignments.set_index("session_pitch")
    measured = selected.set_index("session_pitch")
    for name in ["observed", "predicted", "residual", "absolute_error", "fold"]:
        predictions[name] = pd.to_numeric(predictions[name], errors="raise")
        if not np.isfinite(predictions[name].to_numpy(dtype=float)).all():
            raise ValueError(f"The primary predictions contain nonfinite {name} values")
    for row in predictions.itertuples(index=False):
        if str(row.user) != str(measured.loc[row.session_pitch, "user"]):
            raise ValueError("Prediction and recorded athlete identities disagree")
        if not np.isclose(
            row.observed, measured.loc[row.session_pitch, row.target], atol=1e-9, rtol=1e-9
        ):
            raise ValueError("Prediction outcomes differ from the recorded measurements")
        if (
            row.session_pitch not in assignments.index
            or str(assignments.loc[row.session_pitch, "user"]) != str(row.user)
            or assignments.loc[row.session_pitch, "fold"] != row.fold
        ):
            raise ValueError("Predictions and recorded athlete-fold assignments disagree")
        if row.fold < 1 or row.fold != int(row.fold):
            raise ValueError("Prediction fold identifiers are invalid")
        if not np.isclose(row.residual, row.observed - row.predicted, atol=1e-8, rtol=1e-9):
            raise ValueError("The saved prediction residual is inconsistent")
        if not np.isclose(row.absolute_error, abs(row.residual), atol=1e-8, rtol=1e-9):
            raise ValueError("The saved absolute prediction error is inconsistent")
    return (
        predictions[ERROR_COLUMNS].sort_values(["target", "session_pitch"]).reset_index(drop=True)
    )


def prepare_athlete_report(
    frame: pd.DataFrame,
    athlete_id: str,
    verified_reports: Phase2Reports | None = None,
    *,
    created_utc: datetime | None = None,
) -> AthleteReport:
    """Summarize one athlete's supplied rows, retaining observed missing values."""
    required = {"session_pitch", "user", *VARIABLES}
    if not required.issubset(frame):
        raise ValueError(f"Missing report columns: {', '.join(sorted(required - set(frame)))}")
    if frame[["session_pitch", "user"]].isna().any().any():
        raise ValueError("Report identifiers cannot be missing")
    table = frame.copy()
    for column in ["session_pitch", "user"]:
        table[column] = table[column].astype(str)
        if table[column].str.strip().eq("").any():
            raise ValueError("Report identifiers cannot be empty")
    if table.session_pitch.duplicated().any():
        raise ValueError("A report requires one row per recorded pitch")
    table = _numeric(table)
    athlete = str(athlete_id)
    selected = table.loc[table.user.eq(athlete)].sort_values("session_pitch").copy()
    if selected.empty:
        raise ValueError("The selected athlete has no recorded pitches in the supplied table")
    columns = [
        name for name in ["session_pitch", "user", "session", *VARIABLES] if name in selected
    ]
    pitches = selected[columns].reset_index(drop=True)
    summaries = []
    for variable, (label, unit) in VARIABLES.items():
        values = pitches[variable].dropna()
        summaries.append(
            {
                "variable": variable,
                "measurement": label,
                "unit": unit,
                "n_observed": len(values),
                "n_missing": int(pitches[variable].isna().sum()),
                "mean": float(values.mean()) if len(values) else None,
                "minimum": float(values.min()) if len(values) else None,
                "maximum": float(values.max()) if len(values) else None,
            }
        )
    predictions = pd.DataFrame(columns=ERROR_COLUMNS)
    notices = []
    reference_verified = False
    if verified_reports is not None:
        reference_verified = _reference_matches(pitches, verified_reports)
        try:
            predictions = matched_predictions(pitches, verified_reports)
        except (ValueError, KeyError, TypeError, pd.errors.ParserError) as error:
            notices.append(f"Saved prediction errors are withheld: {error}.")
    else:
        notices.append("No verified Phase 2 study was supplied; no model errors are shown.")
    session_values = pitches.get("session")
    if (
        session_values is None
        or session_values.isna().any()
        or session_values.astype(str).str.strip().eq("").any()
    ):
        session_count = None
        notices.append("The report table does not establish complete session identifiers.")
    else:
        session_count = int(session_values.astype(str).nunique())
    if session_count == 1:
        notices.append(
            "These recorded pitches come from one released assessment session. "
            "They do not establish longitudinal change or a reliable long-term consistency trait."
        )
    else:
        notices.append(
            "This report describes only the supplied observations. No longitudinal trend "
            "or reliable long-term consistency estimate is computed."
        )
    notices.append(
        "Peak rotation measures may occur at different instants. Peak hip–shoulder separation "
        "is not specifically the value at foot contact."
    )
    notices.append(
        "Internal net elbow varus moment is joint-level loading, not ligament force, "
        "an injury probability, or a safe/unsafe threshold. Recorded differences do not "
        "estimate the effect of changing mechanics."
    )
    reference_athlete_rows = None
    if reference_verified and verified_reports is not None:
        reference_athlete_rows = int(verified_reports.analysis.user.astype(str).eq(athlete).sum())
    created = created_utc or datetime.now(UTC)
    if created.tzinfo is None:
        raise ValueError("Report creation time must include a timezone")
    observed_csv, identifier_escapes = _observations_csv(pitches)
    if identifier_escapes:
        notices.append(
            "Spreadsheet-sensitive CSV identifiers have a protective apostrophe prefix. "
            "Their original strings are retained in the companion provenance JSON. "
            "Observed numeric measurements are unchanged."
        )
    metadata = {
        "report_schema_version": 1,
        "software_version": __version__,
        "created_utc": created.astimezone(UTC).isoformat(timespec="seconds"),
        "athlete_id": athlete,
        "n_recorded_pitches": len(pitches),
        "n_sessions": session_count,
        "reference_athlete_pitches_available": reference_athlete_rows,
        "supplied_table_pitches": len(table),
        "supplied_table_athletes": int(table.user.nunique()),
        "reference_identity_and_measurements_verified": reference_verified,
        "source": "Driveline Baseball Research & Development, OpenBiomechanics Project"
        if reference_verified
        else "Caller-supplied table; source identity has not been verified",
        "source_commit": COMMIT if reference_verified else None,
        "source_url": f"{REPOSITORY}/tree/{COMMIT}" if reference_verified else None,
        "verified_study_analysis_sha256": verified_reports.metadata.get("analysis_sha256")
        if reference_verified and verified_reports is not None
        else None,
        "observations_csv_sha256": hashlib.sha256(observed_csv.encode()).hexdigest(),
        "csv_identifier_policy": "Preserve identifier strings; prefix spreadsheet-sensitive "
        "identifiers with an apostrophe in CSV only and retain original strings below. "
        "Numeric measurements are never escaped or modified.",
        "csv_identifier_escapes": identifier_escapes,
        "verified_primary_predictions_sha256": (
            hashlib.sha256(
                verified_reports.verified_bytes["phase2_oof_predictions.csv"]
            ).hexdigest()
            if len(predictions) and verified_reports is not None
            else None
        ),
        "producing_study_commit": verified_reports.metadata.get("project_git_commit")
        if reference_verified and verified_reports is not None
        else None,
        "model": MODEL if len(predictions) else None,
        "primary_partition_seed": verified_reports.spec.get("primary_seed")
        if len(predictions) and verified_reports is not None
        else None,
        "error_scope": "Saved primary-partition athlete-held-out combined ridge predictions; "
        "per-athlete MAE averages that athlete's recorded pitch errors separately for each outcome. "
        "The complete study's primary score averages athlete MAEs equally.",
        "data_terms": DATA_TERMS,
        "full_data_license_url": LICENSE_URL,
        "interpretation": "Descriptive recorded observations and saved held-out errors; "
        "no causal, clinical, or injury prediction claim.",
    }
    return AthleteReport(
        athlete, pitches, pd.DataFrame(summaries), predictions, metadata, tuple(notices)
    )


def _observations_csv(pitches: pd.DataFrame) -> tuple[str, list[dict]]:
    """Protect spreadsheet text identifiers while preserving original strings in metadata."""
    exported = pitches.copy()
    escapes: list[dict] = []
    for column in ("session_pitch", "user", "session"):
        if column not in exported:
            continue
        values = []
        for row, value in enumerate(exported[column], start=1):
            if pd.isna(value):
                values.append(value)
                continue
            text = str(value)
            sensitive = text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(
                ("=", "+", "-", "@")
            )
            values.append("'" + text if sensitive else text)
            if sensitive:
                escapes.append({"row": row, "column": column, "original": text})
        exported[column] = values
    return exported.to_csv(index=False, lineterminator="\n"), escapes


def report_csv(report: AthleteReport) -> str:
    """Export observed rows; missing cells stay empty and text IDs are spreadsheet-safe."""
    return _observations_csv(report.pitches)[0]


def report_metadata_json(report: AthleteReport) -> str:
    return json.dumps(report.metadata, indent=2, allow_nan=False) + "\n"


def _observed_plot(report: AthleteReport, variable: str) -> str:
    """Small independent-unit dot plot; identifier order is never called time."""
    values = report.pitches[variable].to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    # Keep the intrinsic figure close to a phone's content width so SVG text
    # remains readable when the card shrinks; max-height caps desktop scaling.
    width, height, left, right, top, bottom = 360, 175, 30, 16, 30, 40
    if not len(finite):
        return '<p class="muted">No observed values for this measurement.</p>'
    low, high = float(finite.min()), float(finite.max())
    span = high - low
    padding = span * 0.18 if span else max(abs(low) * 0.03, 1.0)
    low, high = low - padding, high + padding
    n = len(values)
    plot_width = width - left - right

    def x(index: int) -> float:
        return left + (index + 0.5) * plot_width / n

    def y(value: float) -> float:
        return top + (high - value) / (high - low) * (height - top - bottom)

    marks = []
    for index, (identifier, value) in enumerate(zip(report.pitches.session_pitch, values)):
        safe_id = _safe(identifier)
        if np.isfinite(value):
            marks.append(
                f'<circle cx="{x(index):.2f}" cy="{y(value):.2f}" r="5" fill="#007C91">'
                f"<title>Pitch {safe_id}: {_safe(_number(value))}</title></circle>"
                f'<text x="{x(index):.2f}" y="{y(value) - 10:.2f}" text-anchor="middle">'
                f"{_safe(_number(value))}</text>"
            )
        else:
            marks.append(f'<text x="{x(index):.2f}" y="85" text-anchor="middle">Missing</text>')
        # The report remains legible for larger supplied tables: full IDs stay in
        # accessible point titles and the observation table.
        if n <= 5:
            label = str(identifier)
            label = label if len(label) <= 10 else label[:7] + "…"
            marks.append(
                f'<text x="{x(index):.2f}" y="{height - 17}" text-anchor="middle">'
                f"{_safe(label)}</text>"
            )
    label, unit = VARIABLES[variable]
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Observed {_safe(label)} in {_safe(unit)} for recorded pitches" '
        'xmlns="http://www.w3.org/2000/svg">'
        "<style>text{font:12px system-ui,sans-serif;fill:#334155}</style>"
        f'<line x1="{left}" x2="{width - right}" y1="{height - bottom}" '
        f'y2="{height - bottom}" stroke="#CBD5E1"/>' + "".join(marks) + "</svg>"
    )


def render_report_html(report: AthleteReport) -> str:
    """Self-contained, script-free HTML with screen, phone, and print layouts."""
    meta = report.metadata
    cards = []
    for row in report.summary.itertuples(index=False):
        cards.append(
            '<section class="measurement">'
            f"<h3>{_safe(row.measurement)} <span>({_safe(row.unit)})</span></h3>"
            '<div class="summary">'
            f"<div><strong>{_safe(_number(row.mean))}</strong><span>Observed mean</span></div>"
            f"<div><strong>{_safe(_number(row.minimum))} – {_safe(_number(row.maximum))}</strong>"
            "<span>Observed minimum – maximum</span></div>"
            f"<div><strong>{int(row.n_observed)} / {len(report.pitches)}</strong>"
            f"<span>Measured pitches · {int(row.n_missing)} missing</span></div></div>"
            + _observed_plot(report, row.variable)
            + "</section>"
        )
    observations = []
    for row in report.pitches.itertuples(index=False):
        observations.append(
            "<tr>"
            f'<th scope="row">{_safe(row.session_pitch)}</th>'
            + "".join(f"<td>{_safe(_number(getattr(row, name)))}</td>" for name in VARIABLES)
            + "</tr>"
        )
    errors = '<p class="muted">No verified held-out model errors are available for this report.</p>'
    if not report.predictions.empty:
        error_cards, error_rows = [], []
        for target, group in report.predictions.groupby("target", sort=False):
            label, unit = VARIABLES[target]
            error_cards.append(
                '<div class="error-card">'
                f"<h3>{_safe(label)}</h3>"
                f"<strong>{_safe(_number(group.absolute_error.mean()))} {_safe(unit)}</strong>"
                f"<p>Mean absolute error across {len(group)} recorded pitches for this athlete.</p>"
                "</div>"
            )
            for row in group.itertuples(index=False):
                error_rows.append(
                    "<tr>"
                    f'<th scope="row">{_safe(row.session_pitch)}</th>'
                    f"<td>{_safe(label)} ({_safe(unit)})</td>"
                    f"<td>{_safe(_number(row.observed))}</td>"
                    f"<td>{_safe(_number(row.predicted))}</td>"
                    f"<td>{_safe(_number(row.absolute_error))}</td><td>{int(row.fold)}</td></tr>"
                )
        errors = (
            "<p>These are saved <strong>primary-partition, athlete-held-out combined ridge</strong> "
            "predictions. This athlete was excluded from training each model used for their "
            "reported predictions. Opening or exporting this report does not fit a model.</p>"
            '<div class="error-cards">'
            + "".join(error_cards)
            + '</div><p class="muted">The complete study gives each athlete equal weight. '
            "These individual-athlete errors are descriptive details, not a new independent "
            "validation study or a prediction interval.</p>"
            '<div class="table-wrap"><table><thead><tr><th>Pitch</th><th>Outcome / unit</th>'
            "<th>Observed</th><th>Predicted</th><th>Absolute error</th><th>Fold</th></tr></thead><tbody>"
            + "".join(error_rows)
            + "</tbody></table></div>"
        )
    available = meta.get("reference_athlete_pitches_available")
    available_sentence = (
        f"This report contains {len(report.pitches)} of {available} pitches for this athlete "
        "in the verified study table."
        if available is not None
        else "This report contains only the selected athlete's rows in the supplied table."
    )
    sessions = meta.get("n_sessions")
    session_sentence = (
        f"{sessions} recorded session{'s' if sessions != 1 else ''}."
        if sessions is not None
        else "Session coverage is not established."
    )
    notices = "".join(f"<li>{_safe(item)}</li>" for item in report.notices)
    columns = "".join(
        f"<th>{_safe(label)}<br><span>({_safe(unit)})</span></th>"
        for label, unit in VARIABLES.values()
    )
    provenance = "".join(
        f"<dt>{_safe(label)}</dt><dd>{_safe(meta.get(key) or 'Not available')}</dd>"
        for key, label in [
            ("source", "Source identity"),
            ("source_commit", "Pinned source revision"),
            ("verified_study_analysis_sha256", "Verified study analysis-file SHA-256"),
            ("producing_study_commit", "Producing study revision"),
            ("software_version", "Report software version"),
            ("created_utc", "Created in UTC"),
            ("observations_csv_sha256", "Observed-row CSV SHA-256"),
            ("verified_primary_predictions_sha256", "Verified primary prediction-file SHA-256"),
        ]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recorded athlete report · {_safe(report.athlete_id)}</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#F3F6F8;color:#172B3A;font:16px/1.55 system-ui,-apple-system,sans-serif}}
main{{max-width:1000px;margin:32px auto;background:white;padding:40px;border-radius:14px}}h1{{font-size:2rem;line-height:1.15;margin:.4em 0}}h2{{font-size:1.4rem;margin-top:2rem}}h3{{font-size:1.05rem;margin:.2em 0 .8em}}p{{max-width:78ch}}.eyebrow{{color:#007C91;font-weight:700}}.muted,span{{color:#536579}}.callout{{border-left:4px solid #007C91;background:#F3F8FA;padding:14px 18px}}.measurement{{border:1px solid #D5DFE7;border-radius:10px;padding:20px;margin:18px 0;break-inside:avoid}}.summary,.error-cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}}.summary strong,.summary span{{display:block}}.summary strong{{font-size:1.22rem}}.summary span{{font-size:.85rem}}svg{{display:block;width:100%;height:auto;max-height:220px}}.error-cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.error-card{{padding:18px;border:1px solid #D5DFE7;border-radius:10px}}.error-card strong{{font-size:1.5rem}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:.85rem}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #D5DFE7;vertical-align:top}}th{{font-weight:600}}td,th,dd{{overflow-wrap:anywhere}}dt{{font-weight:600;margin-top:12px}}dd{{margin:0;font-size:.85rem}}footer{{border-top:1px solid #D5DFE7;margin-top:32px;padding-top:20px;font-size:.85rem}}a{{color:#007C91}}li{{margin:10px 0}}
@media(max-width:640px){{body{{background:white}}main{{margin:0;padding:22px 16px;border-radius:0}}h1{{font-size:1.65rem}}.measurement{{padding:14px}}.summary,.error-cards{{grid-template-columns:1fr;gap:12px}}svg text{{font-size:14px}}}}
@media print{{body{{background:white;font-size:10pt}}main{{max-width:none;margin:0;padding:0}}h1{{font-size:22pt}}h2{{break-after:avoid}}.measurement{{padding:12px}}.summary{{grid-template-columns:repeat(3,minmax(0,1fr))}}.error-cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}a{{color:inherit}}.table-wrap{{overflow:visible}}table{{font-size:8pt}}tr{{break-inside:avoid}}}}
</style></head><body><main>
<header><div class="eyebrow">Pitching Performance and Elbow Loading · Owen Garrett</div>
<h1>Recorded athlete report</h1><p><strong>Pseudonymous athlete {_safe(report.athlete_id)}</strong> · {len(report.pitches)} recorded pitches · {_safe(session_sentence)}</p>
<p class="callout">A descriptive report of measured observations and verified saved model errors. This is not an injury assessment or a prescription for changing mechanics.</p></header>
<section><h2>What this report covers</h2><p>{_safe(available_sentence)} The supplied table contains {meta["supplied_table_pitches"]} pitches from {meta["supplied_table_athletes"]} athletes.</p>
<p>Pitch identifiers define the display order. They are not a time axis. Means and ranges describe the included pitches; rotation means average per-pitch peak summaries.</p></section>
<section><h2>Observed measurements</h2>{"".join(cards)}</section>
<section><h2>Recorded pitch values</h2><div class="table-wrap"><table><thead><tr><th>Pitch</th>{columns}</tr></thead><tbody>{"".join(observations)}</tbody></table></div><p class="muted">Missing observations remain missing. No interpolation or outcome imputation is performed.</p></section>
<section><h2>How close were the saved predictions?</h2>{errors}</section>
<section><h2>Interpretation and limits</h2><ul>{notices}</ul></section>
<section><h2>Provenance</h2><dl>{provenance}</dl><p class="muted">Checksums identify these exact report inputs. They are not an independent validation of the measurements or study.</p></section>
<footer><p>Source attribution: Driveline Baseball Research &amp; Development, OpenBiomechanics Project, when verified above. Changes: selected recorded athlete rows, summarized observed values, plotted per-pitch measurements, and displayed saved held-out errors.</p><p>{_safe(DATA_TERMS)} <a href="{LICENSE_URL}">Full pinned upstream data terms</a>.</p><p>Original software is MIT-licensed. Preserve data attribution and terms with this HTML, the observed CSV, and its companion metadata. Print this page to save a PDF.</p></footer>
</main></body></html>"""
