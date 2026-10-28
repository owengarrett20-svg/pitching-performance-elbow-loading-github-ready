"""Separate pitcher-to-pitcher from pitch-to-pitch variation in speed and elbow moment.

This exploratory follow-on uses the verified analysis table only. It scales the
released peak internal elbow varus moment by body weight times height, partitions
variance between and within athletes, and contrasts within-athlete with
between-athlete speed slopes. Uncertainty resamples athletes, keeping each
athlete's pitches together. No model is fitted to new data and no value is
imputed: a pitch missing any required field is excluded from every statistic.
"""

from __future__ import annotations

from dataclasses import dataclass

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

GRAVITY = 9.80665
NORMALIZED = "elbow_moment_pct_bwh"
REQUIRED = (
    "session_pitch",
    "user",
    "pitch_speed_mph",
    "elbow_varus_moment",
    "session_mass_kg",
    "session_height_m",
)
DRAWS = 5000
SEED = 20261028
OUTCOMES = {
    "elbow_varus_moment": ("Elbow varus moment", "N·m"),
    NORMALIZED: ("Elbow varus moment / (body weight × height)", "% BW·H"),
}


def normalized_elbow_moment(frame: pd.DataFrame) -> pd.Series:
    """Moment as a percentage of body weight (N) times height (m); invalid sizes stay missing."""
    moment = pd.to_numeric(frame["elbow_varus_moment"], errors="coerce")
    mass = pd.to_numeric(frame["session_mass_kg"], errors="coerce")
    height = pd.to_numeric(frame["session_height_m"], errors="coerce")
    scale = (mass * GRAVITY * height).where((mass > 0) & (height > 0))
    result = 100 * moment / scale
    return result.replace([np.inf, -np.inf], np.nan).rename(NORMALIZED)


def variation_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Complete-case pitch rows with the normalized moment added."""
    missing = set(REQUIRED) - set(frame)
    if missing:
        raise ValueError(f"Variation analysis is missing fields: {', '.join(sorted(missing))}")
    table = frame[list(REQUIRED)].copy()
    for name in ("session_pitch", "user"):
        if table[name].isna().any():
            raise ValueError("Every pitch needs nonmissing pitch and athlete identifiers")
        table[name] = table[name].astype(str)
    if table.session_pitch.duplicated().any():
        raise ValueError("Each pitch identifier must appear once")
    for name in REQUIRED[2:]:
        table[name] = pd.to_numeric(table[name], errors="coerce")
    table[NORMALIZED] = normalized_elbow_moment(table)
    numeric = ["pitch_speed_mph", "elbow_varus_moment", NORMALIZED]
    table[numeric] = table[numeric].replace([np.inf, -np.inf], np.nan)
    return table.dropna(subset=numeric).reset_index(drop=True)


@dataclass(frozen=True)
class AthleteSums:
    """Per-athlete sufficient statistics; any athlete resample is a count vector over them."""

    n: np.ndarray
    mean_x: np.ndarray
    mean_y: dict[str, np.ndarray]
    sxx: np.ndarray
    sxy: dict[str, np.ndarray]
    syy: dict[str, np.ndarray]
    athletes: list[str]


def athlete_sums(table: pd.DataFrame) -> AthleteSums:
    groups = table.groupby("user", sort=True)
    centered = table[["pitch_speed_mph", *OUTCOMES]] - groups[
        ["pitch_speed_mph", *OUTCOMES]
    ].transform("mean")
    x = centered["pitch_speed_mph"]
    sums = pd.DataFrame({"sxx": x**2})
    for name in OUTCOMES:
        sums[f"sxy_{name}"] = x * centered[name]
        sums[f"syy_{name}"] = centered[name] ** 2
    per_athlete = sums.groupby(table["user"], sort=True).sum()
    means = groups[["pitch_speed_mph", *OUTCOMES]].mean()
    return AthleteSums(
        n=groups.size().to_numpy(float),
        mean_x=means["pitch_speed_mph"].to_numpy(),
        mean_y={name: means[name].to_numpy() for name in OUTCOMES},
        sxx=per_athlete["sxx"].to_numpy(),
        sxy={name: per_athlete[f"sxy_{name}"].to_numpy() for name in OUTCOMES},
        syy={name: per_athlete[f"syy_{name}"].to_numpy() for name in OUTCOMES},
        athletes=list(means.index),
    )


def _icc(weights: np.ndarray, n: np.ndarray, means: np.ndarray, ssw: np.ndarray) -> np.ndarray:
    """One-way random-effects ICC(1) with the unbalanced-group n0 adjustment.

    ``weights`` holds athlete multiplicities (rows are resamples). Duplicated
    athletes count as distinct groups, as in a cluster bootstrap.
    """
    k = weights.sum(axis=1)
    total = weights @ n
    grand = (weights @ (n * means)) / total
    ssb = (weights * n * (means[None, :] - grand[:, None]) ** 2).sum(axis=1)
    within = weights @ ssw
    msb = ssb / (k - 1)
    msw = within / (total - k)
    n0 = (total - (weights @ n**2) / total) / (k - 1)
    return (msb - msw) / (msb + (n0 - 1) * msw)


def _statistics(sums: AthleteSums, weights: np.ndarray) -> dict[str, np.ndarray]:
    weights = np.atleast_2d(weights).astype(float)
    result = {
        "icc_pitch_speed_mph": _icc(weights, sums.n, sums.mean_x, sums.sxx),
        "within_speed_sd": np.sqrt((weights @ sums.sxx) / (weights @ sums.n - weights.sum(axis=1))),
    }
    for name in OUTCOMES:
        result[f"icc_{name}"] = _icc(weights, sums.n, sums.mean_y[name], sums.syy[name])
        within = (weights @ sums.sxy[name]) / (weights @ sums.sxx)
        # Between-athlete slope: ordinary least squares on athlete means, one
        # point per athlete (resampled multiplicity), independent of pitch counts.
        total = weights.sum(axis=1)
        mx = (weights @ sums.mean_x) / total
        my = (weights @ sums.mean_y[name]) / total
        dx = sums.mean_x[None, :] - mx[:, None]
        dy = sums.mean_y[name][None, :] - my[:, None]
        between = (weights * dx * dy).sum(axis=1) / (weights * dx**2).sum(axis=1)
        result[f"within_slope_{name}"] = within
        result[f"between_slope_{name}"] = between
        result[f"slope_difference_{name}"] = within - between
    return result


STATISTICS = {
    "icc_pitch_speed_mph": ("Share of speed variance between athletes (ICC)", ""),
    "icc_elbow_varus_moment": ("Share of elbow-moment variance between athletes (ICC)", ""),
    f"icc_{NORMALIZED}": ("Share of normalized-moment variance between athletes (ICC)", ""),
    "within_speed_sd": ("Pitch-to-pitch speed SD within an athlete", "mph"),
    "within_slope_elbow_varus_moment": ("Within-athlete slope, elbow moment", "N·m per mph"),
    "between_slope_elbow_varus_moment": ("Between-athlete slope, elbow moment", "N·m per mph"),
    "slope_difference_elbow_varus_moment": ("Within − between slope, elbow moment", "N·m per mph"),
    f"within_slope_{NORMALIZED}": ("Within-athlete slope, normalized moment", "% BW·H per mph"),
    f"between_slope_{NORMALIZED}": ("Between-athlete slope, normalized moment", "% BW·H per mph"),
    f"slope_difference_{NORMALIZED}": (
        "Within − between slope, normalized moment",
        "% BW·H per mph",
    ),
}


def variation_study(
    frame: pd.DataFrame, *, draws: int = DRAWS, seed: int = SEED, level: float = 0.95
) -> pd.DataFrame:
    """Point estimates with athlete-cluster percentile intervals (fixed seed)."""
    table = variation_table(frame)
    sums = athlete_sums(table)
    if len(sums.athletes) < 3:
        raise ValueError("At least three athletes are needed to separate athlete variation")
    if (sums.n < 2).all():
        raise ValueError("Within-athlete variation needs athletes with repeated pitches")
    estimate = {
        name: float(value[0]) for name, value in _statistics(sums, np.ones(len(sums.n))).items()
    }
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(len(sums.n), np.full(len(sums.n), 1 / len(sums.n)), size=draws)
    # A resample that repeats one athlete has no between-athlete spread; its
    # undefined statistics are counted out of the valid resamples below.
    with np.errstate(divide="ignore", invalid="ignore"):
        resampled = _statistics(sums, counts)
    alpha = (1 - level) / 2
    rows = []
    for name, (label, unit) in STATISTICS.items():
        values = resampled[name][np.isfinite(resampled[name])]
        low, high = np.quantile(values, [alpha, 1 - alpha]) if len(values) else (np.nan, np.nan)
        rows.append(
            {
                "statistic": name,
                "label": label,
                "unit": unit,
                "estimate": estimate[name],
                "low": float(low),
                "high": float(high),
                "valid_resamples": len(values),
            }
        )
    result = pd.DataFrame(rows)
    result.attrs.update(
        pitches=len(table),
        athletes=len(sums.athletes),
        draws=draws,
        seed=seed,
        level=level,
    )
    return result


def athlete_lines(table: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Each athlete's own least-squares line over that athlete's observed speed range."""
    rows = []
    for athlete, pitches in table.groupby("user", sort=True):
        x = pitches["pitch_speed_mph"].to_numpy()
        y = pitches[outcome].to_numpy()
        if len(x) < 2 or np.ptp(x) == 0:
            continue
        slope, intercept = np.polyfit(x, y, 1)
        for speed in (x.min(), x.max()):
            rows.append(
                {"user": athlete, "pitch_speed_mph": speed, outcome: intercept + slope * speed}
            )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner="Resampling athletes…", max_entries=4)
def _cached_study(frame: pd.DataFrame) -> pd.DataFrame:
    return variation_study(frame)


def _format(value: float, unit: str) -> str:
    if not np.isfinite(value):
        return "Undefined"
    digits = 3 if unit in {"", "% BW·H per mph"} else 2
    return f"{value:.{digits}f}"


def render_athlete_variation(frame: pd.DataFrame) -> None:
    """Exploratory pitcher-versus-pitch decomposition with athlete-cluster uncertainty."""
    st.subheader("Is elbow loading a pitcher trait or a pitch-to-pitch change?")
    st.write(
        "Pitchers who throw harder also tend to be bigger, and bigger bodies produce larger "
        "joint moments. This view scales elbow moment by body weight × height, then separates "
        "differences **between pitchers** from changes **within one pitcher's session**."
    )
    try:
        table = variation_table(frame)
        study = _cached_study(frame)
    except (ValueError, KeyError, TypeError) as error:
        st.warning(f"The variation analysis cannot be computed from this table: {error}.")
        return
    values = study.set_index("statistic")
    outcome = st.radio(
        "Elbow moment scale",
        list(OUTCOMES),
        index=1,
        format_func=lambda name: OUTCOMES[name][1],
        horizontal=True,
        key="variation_outcome",
    )
    label, unit = OUTCOMES[outcome]
    cards = st.columns(3)
    icc = values.loc[f"icc_{outcome}"]
    cards[0].metric(
        "Variance between pitchers",
        f"{icc.estimate:.0%}",
        help="Intraclass correlation: the share of total variance explained by which pitcher threw.",
    )
    for column, kind, title in (
        (cards[1], "within", "Within-pitcher slope"),
        (cards[2], "between", "Between-pitcher slope"),
    ):
        row = values.loc[f"{kind}_slope_{outcome}"]
        column.metric(f"{title} ({unit}/mph)", _format(row.estimate, f"{unit} per mph"))
        column.caption(
            f"95% interval {_format(row.low, f'{unit} per mph')} to "
            f"{_format(row.high, f'{unit} per mph')}"
        )
    difference = values.loc[f"slope_difference_{outcome}"]
    contains_zero = difference.low <= 0 <= difference.high
    st.info(
        f"Within − between slope: {_format(difference.estimate, f'{unit} per mph')} {unit}/mph "
        f"(95% interval {_format(difference.low, f'{unit} per mph')} to "
        f"{_format(difference.high, f'{unit} per mph')}). "
        + (
            "The interval includes zero: these data do not distinguish the within-pitcher "
            "and between-pitcher speed relationships on this scale."
            if contains_zero
            else "The interval excludes zero: on this scale the within-pitcher and "
            "between-pitcher speed relationships differ in this sample."
        )
    )
    x_title, y_title = "Pitch speed (mph)", f"{label} ({unit})"
    base = alt.Chart(table).encode(
        x=alt.X("pitch_speed_mph:Q", title=x_title, scale=alt.Scale(zero=False)),
        y=alt.Y(f"{outcome}:Q", title=y_title, scale=alt.Scale(zero=False)),
    )
    pitches = base.mark_circle(size=26, color="#9DB7C2", opacity=0.6).encode(
        tooltip=[
            alt.Tooltip("session_pitch:N", title="Pitch ID"),
            alt.Tooltip("user:N", title="Athlete ID"),
            alt.Tooltip("pitch_speed_mph:Q", title="Speed (mph)", format=".1f"),
            alt.Tooltip(f"{outcome}:Q", title=f"{label} ({unit})", format=".2f"),
        ]
    )
    lines = (
        alt.Chart(athlete_lines(table, outcome))
        .mark_line(color="#C96C2D", strokeWidth=1.6, opacity=0.85)
        .encode(
            x=alt.X("pitch_speed_mph:Q", title=x_title),
            y=alt.Y(f"{outcome}:Q", title=y_title),
            detail="user:N",
        )
    )
    trend = (
        base.transform_aggregate(
            speed="mean(pitch_speed_mph)", value=f"mean({outcome})", groupby=["user"]
        )
        .transform_regression("speed", "value")
        .mark_line(color="#172B3A", strokeDash=[6, 4], strokeWidth=2)
        .encode(x=alt.X("speed:Q", title=x_title), y=alt.Y("value:Q", title=y_title))
    )
    st.altair_chart(
        alt.layer(pitches, lines, trend)
        .properties(height=400)
        .configure_axis(labelFontSize=12, titleFontSize=13, titlePadding=12, gridOpacity=0.18)
        .configure_view(stroke=None),
        width="stretch",
    )
    st.caption(
        "Grey dots are pitches. Each short orange line is one pitcher's own speed relationship "
        "over that session's speed range; the dashed line fits pitcher averages. Short orange "
        "lines show how little speed varies within a session."
    )
    shown = study.assign(
        estimate=[_format(row.estimate, row.unit) for row in study.itertuples()],
        interval=[
            f"{_format(row.low, row.unit)} to {_format(row.high, row.unit)}"
            for row in study.itertuples()
        ],
    )[["label", "unit", "estimate", "interval"]]
    st.dataframe(
        shown.rename(
            columns={
                "label": "Statistic",
                "unit": "Unit",
                "estimate": "Estimate",
                "interval": "95% athlete-resampled interval",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.download_button(
        "Download these statistics (CSV)",
        data=study.to_csv(index=False).encode("utf-8"),
        file_name="athlete-variation-statistics.csv",
        mime="text/csv",
        key="variation_download",
    )
    with st.expander("Methods and limits"):
        st.markdown(
            f"""
- **Sample:** {study.attrs["pitches"]:,} fastballs from {study.attrs["athletes"]:,} athletes,
  one recorded session each, from the verified study table. Pitches missing speed, moment,
  mass, or height are excluded from every statistic.
- **Scaling:** moment ÷ (mass × {GRAVITY} m/s² × height) × 100, a common body-size
  normalization in pitching biomechanics. Mass and height are session values.
- **ICC(1):** one-way random-effects intraclass correlation with the unbalanced-group
  n₀ adjustment.
- **Slopes:** the within-athlete slope pools each athlete's speed and moment deviations
  from their own means; the between-athlete slope is least squares on athlete means,
  one point per athlete.
- **Uncertainty:** {study.attrs["draws"]:,} athlete-cluster bootstrap resamples (seed
  {study.attrs["seed"]}), percentile intervals. Pitches stay with their athlete.
- **Status:** exploratory and defined after viewing this dataset; not preregistered or
  externally replicated. Within-session speed varies only about
  {values.loc["within_speed_sd"].estimate:.1f} mph, so within-athlete slopes describe a
  narrow range and should not be extrapolated to larger speed changes.
- **Interpretation:** these are associations among completed pitches. They do not show
  that throwing harder causes higher loading in a given pitcher, and internal net moment
  is not UCL force or injury risk.
"""
        )
