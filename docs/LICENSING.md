# Licensing, attribution, and permitted scope

This project analyzes the OpenBiomechanics Project (OBP), published by Driveline Baseball Research & Development. Its source snapshot is commit [`44b98dae05cceb016f080ab39d105c85b8639084`](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084).

## Separate the software from the data

Independently written project software is available under this project's MIT license. That permission does **not** grant unrestricted rights to the OBP measurements, biomechanics documentation, or derived data products.

Upstream uses two licenses:

- **Software:** MIT, as stated in [the upstream code license](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-CODE.md). An unchanged copy is retained at [licenses/UPSTREAM-LICENSE-CODE.md](licenses/UPSTREAM-LICENSE-CODE.md).
- **Data and biomechanics documentation:** [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), **with the additional professional-organization exclusion quoted below**, as stated in [the upstream data license](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md). The exact supplied terms are retained at [licenses/UPSTREAM-LICENSE-DATA.md](licenses/UPSTREAM-LICENSE-DATA.md).

The upstream data terms require attribution, a license link, an indication of adaptations, noncommercial use, and ShareAlike distribution of adaptations. They also prohibit additional restrictions. Do not label the complete project, data, or derived figures as unrestricted MIT material. This is a research portfolio using openly accessible data with restricted reuse terms.

## Additional upstream exclusion

The upstream data license contains this exact additional restriction:

> **Any employee or contractor employed by, associated with, or a significant shareholder of a professional sports organization or financial analysis firm is forbidden to use The OpenBiomechanics Project data for any use whatsoever.**

The preceding upstream paragraph states that such use requires a specific written commercial (paid) license. The complete text, including the licensor's description of commercial use, remains authoritative; see the retained license above and [openbiomechanics.org](https://openbiomechanics.org).

This project is prepared for independent, noncommercial research and portfolio study. An aspiration to work in professional sports does not by itself establish a current affiliation. A future team role, consultancy, affiliation, or commercial application requires checking these terms and obtaining the written permission required by the licensor before reusing the OBP material in that setting. Public availability does not remove this condition.

## Attribution and adaptations

Suggested attribution for shared research outputs:

> Source: Driveline Baseball Research & Development, The OpenBiomechanics Project, commit 44b98dae05cceb016f080ab39d105c85b8639084. Data and biomechanics documentation: CC BY-NC-SA 4.0 with the additional restrictions in LICENSE-DATA.md. Adaptations by this project include validated table joins, missing-data summaries, exploratory plots, and athlete-grouped baseline analyses. Driveline does not endorse this project.

Retain that source information and link to the exact upstream data license when sharing data-derived artifacts. Treat redistributed cleaned tables, figures, and research reports derived from OBP material under the upstream data terms, including its additional exclusion. Do not publish a hosted data dashboard for a commercial or excluded organizational use under the code's MIT license.

[VARIABLES.md](VARIABLES.md) and [RESEARCH_PLAN.md](RESEARCH_PLAN.md) adapt and summarize the upstream biomechanics definitions and dataset documentation. These documentation adaptations are distributed under CC BY-NC-SA 4.0 with the additional upstream exclusion, with changes described here and source links in each document. Independently authored software remains separately licensed.

The upstream citation metadata is retained at [licenses/UPSTREAM-CITATION.cff](licenses/UPSTREAM-CITATION.cff). Keep the citation and license notices with copies of upstream material. This project does not acquire footage, redistribute MLB video, or infer media rights from the data license.

## Visual learning assets

The bundled `assets/motion/` clips/arrays and `assets/traces/` signals derive from checksum-verified OBP data and retain the upstream data terms. `assets/lessons/` contains original instructional diagrams adapted from source definitions, explicitly distinguished from measured pitch data. Preserve the adjacent manifests, attribution and license notes. The optional OBP-CV camera embed is a separate officially linked source recording; no footage is redistributed or associated with the study's selected POI row. See [VIDEO_METHODS.md](VIDEO_METHODS.md) for exact sources and the unverified camera-playback limitation.

The committed `assets/demo/` reference reports and `docs/images/` data-derived preview also retain the same upstream data terms and attribution. The hosted entry point verifies their integrity; hosting does not change their permitted uses.
