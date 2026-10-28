# Phase 3: a readable, interactive research showcase

This milestone improves how visitors explore the existing evidence. It introduces
no new athletes, footage, models, or scientific validation claim. Phase 1 and
Phase 2 methods, source licensing, and limitations remain in force.

## Visitor questions

1. What was measured, and why does it matter?
2. What did the comparisons actually find?
3. Can I inspect a recorded pitch, its source measurements, and the errors?
4. Can I verify the methods and reproduce the result?
5. What would a collaboration with appropriately authorized data involve?

The first screen should answer the first two questions in plain language, show
one genuine marker example, and offer clear paths into exploration. Research
tables and provenance remain available through deliberate navigation.

## Implemented scope

- A guided opening with verified full-cohort results and plain-language error
  definitions.
- Separate routes for recorded-pitch exploration, motion, study results, and
  methods/collaboration. Only the active route is rendered.
- Interactive charts, keyboard-accessible pitch selection, and comparisons
  between recorded observations. Athlete means remain a different unit from
  individual pitches.
- Shareable links that use source pitch IDs and a page identifier only.
- Existing measured-marker and processed-trace examples, with no claim of camera
  coverage or verified synchronization for every pitch.
- A non-sensitive public introduction route and documentation for a future,
  independently authorized data collaboration.

## Scientific boundaries

All displayed research findings come from verified saved reports. Sidebar
filters do not alter the full-cohort study contrasts or conditional intervals.
Exploratory comparisons describe observations and do not estimate an effect of
changing mechanics. There is no injury prediction, tissue-force estimate,
normative technique ranking, or synthetic slider-generated pitch.

The source does not establish the instrument used to measure pitch speed.
Rotational athlete means average released per-pitch peak summaries; they are not
time-averaged motion traces. Marker movies remain measured skin-marker views.

OBP excludes professional-sports and financial-analysis affiliates from data
use without its specific written paid license. The original software's MIT
license does not grant those data rights. Future team-data work requires an
appropriate independent permission and data-handling arrangement; the public
demonstration is not a confidential upload service.

## Acceptance checks

- Opening results match the saved Phase 2 scores and correctly retain the
  uncertain elbow-moment increment.
- Chart selections and A/B comparisons refer to actual eligible recorded IDs;
  invalid or filtered-out IDs cannot be substituted for another pitch's motion.
- Both outcomes, filtering, empty states, missing measurements, and stale-result
  protection remain usable.
- A clean hosted checkout needs no raw downloads, model fitting, or bootstrap
  calculation to render any page.
- Desktop and phone-width browser checks cover navigation, text readability,
  charts, and horizontal overflow.

## Local verification

The development suite passed 201 tests; an additional replay-navigation
regression passed separately, for 202 passing tests in total. Lint, formatting,
and the locked deployment-dependency export also pass.

Real Chromium checks at 1440×1000 and 390×844 covered all five views, genuine
chart-point clicks, consecutive pitch selections, prepared-motion deep links,
outcome/model toggles, and explicit missing-replay states. No JavaScript
exceptions or document-level horizontal overflow were observed. The phone's
opening exploration control is visible in the first screen. Desktop and phone
captures are retained in `docs/images/dashboard-overview.png` and
`docs/images/dashboard-mobile.png`.

These are local release checks, not verification of a newly deployed public
version, usability research with coaches, peer review, or external validation.

The next scientific milestone remains an appropriately licensed external or
longitudinal validation study. Improving the presentation does not complete that
research milestone.
