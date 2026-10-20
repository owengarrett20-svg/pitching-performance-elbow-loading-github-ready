# Audit an independently authorized dataset locally

The new-data adapter turns one explicitly mapped, pitch-level CSV into a
checksum-bound canonical dataset. It checks declarations, identifiers, numeric
validity, units, and missingness. It does not fit models, upload measurements,
establish legal permission, or independently prove measurement equivalence.

The external-validation workflow is a separate step described in
[EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md). No independent cohort has been
provided or evaluated as part of this release.

## Agree the study before transferring measurements

Begin with a non-sensitive measurement dictionary and research question. Agree
the data owner, permitted inputs and outputs, access, retention, and an approved
analysis environment before any athlete-data transfer. Public GitHub issues and
this public demonstration are not confidential transfer channels.

Development and external evaluation require separately reviewed datasets and
mappings. Record a stable athlete-ID namespace; a different namespace does not
establish different athletes. Owner confirmation of independence is required by
the evaluation protocol. Do not rename repeated athletes to make an independent
cohort appear to exist.

OBP data and derived assets, reports, and models retain their upstream terms,
including the professional-sports/financial-analysis affiliation exclusion.
The original software's MIT license does not grant those data rights. Future
team work needs independently authorized development and evaluation data. Read
[LICENSING.md](LICENSING.md) and [COLLABORATION.md](COLLABORATION.md).

## Prepare a single pitch-level table

One row must represent one recorded pitch. The adapter does not join separate
POI, metadata, force, or motion tables. If your input requires a join, establish
and document its intended cardinality and matching coverage first. A flattened
CSV with unique IDs cannot, by itself, prove that its upstream joins were correct.

All eleven canonical fields must have a mapped source column. Measurements may
be genuinely missing; identifier cells must be present. Extra source columns are
ignored and counted. They are not automatically used as predictors.

| Canonical field | Canonical unit | Required meaning |
| --- | --- | --- |
| `session_pitch` | identifier | A globally unique recorded-pitch key |
| `user` | identifier | A stable pseudonymous athlete key |
| `session` | identifier | A unique assessment-session key belonging to one athlete |
| `age_yrs` | years | Age at assessment |
| `session_mass_kg` | kg | Body mass at assessment |
| `session_height_m` | m | Body height at assessment |
| `max_shoulder_internal_rotational_velo` | deg/s | Peak internal shoulder rotation angular velocity |
| `max_rotation_hip_shoulder_separation` | deg | Peak thorax–pelvis separation angle |
| `max_torso_rotational_velo` | deg/s | Peak torso axial rotation angular velocity |
| `pitch_speed_mph` | mph | Recorded pitch speed |
| `elbow_varus_moment` | N*m | Peak internal net elbow varus moment |

The supplied [mapping template](../schemas/new_data_mapping.example.json) contains
the exact required definition tokens. The accompanying
[dictionary CSV](../schemas/new_data_dictionary.csv) lists the fields, roles,
units, and required reviews. The templates contain no sample athlete observations
and intentionally fail validation until the actual declarations are completed.

For the three rotational quantities and elbow moment, review the anatomical
frame, axis, sign, reference system, preprocessing, and analysis window before
confirming the declaration. A peak separation angle and a foot-plant angle are
different quantities. An external valgus moment and an internal net varus moment
cannot be relabeled through this adapter. The software performs no sign flips.

## Complete the mapping

In your existing project terminal, create a local study area and copy the
template. These commands are for PowerShell:

```powershell
New-Item -ItemType Directory -Force local_studies
Copy-Item schemas/new_data_mapping.example.json local_studies/development_mapping.json
```

Edit the copied file using your normal editor. Complete:

- Dataset name, population and pitch types, and collection protocol.
- The stable athlete-ID namespace used across assessments and cohorts.
- The owner's authorized-use declaration and its actual basis/scope.
- Each source-column name, its native unit, and the exact required definition.
- Definition confirmations after reviewing the collection protocol.
- Native and canonical sign conventions and confirmation for signed quantities.

The authorization and confirmation flags are operator attestations. They are not
legal verification or automated biomechanical validation. Keep restrictions and
permitted scope in the rights basis; additional dataset metadata is retained in
the prepared provenance. The mapping cannot map the same source column into two
canonical fields, which guards against simple duplicated-outcome leakage.

The input CSV's identifier strings are preserved exactly. Leading zeros remain
meaningful: athlete `001` and athlete `1` stay different. A literal identifier
such as `NA` remains an identifier. Empty IDs and edge whitespace are rejected
instead of silently merging or rewriting identities. `session_pitch` must be
unique across the entire input; a session cannot belong to multiple athletes.

## Run the audit

Place the authorized source CSV in the approved local study area. Run the audit
with a **new output directory**:

```powershell
uv run --frozen pitching new-data audit --csv local_studies/development.csv --mapping local_studies/development_mapping.json --output local_studies/development
```

Existing output directories are refused, including empty ones. Input files are
preserved. Correct a failed input or mapping and select a new output path; do not
edit generated canonical data to bypass an error. Run one command at a time and
check its exit status before proceeding to a model workflow.

`local_studies/` is excluded from Git. An ignore rule does not secure a machine,
grant permission, or make a hosted service private. Use the environment approved
by the data owner, and review any files you intend to publish separately.

### Supported unit conversions

| Native unit | Canonical unit | Multiplication |
| --- | --- | --- |
| lb | kg | 0.45359237 |
| cm | m | 0.01 |
| rad/s | deg/s | 180 / π |
| rad | deg | 180 / π |
| m/s | mph | 2.2369362920544025 |

Canonical units are also accepted unchanged. Age uses `years`; moment uses the
literal mapping unit `N*m`. Conversions are deterministic and recorded. Other
units are refused. Unit conversion does not establish semantic equivalence or
correct an uncertain sign convention.

### Missing and invalid observations

Numeric blank cells and the case-insensitive tokens `NA`, `N/A`, `NaN`, `null`,
and `none` become missing values. This policy applies to numeric measurements
only. Missing outcomes remain missing, even if another field could supply a
related value. The adapter does not impute predictors or targets.

Nonnumeric cells, positive/negative infinity, and conversion overflow stop the
audit. Observed mass, height, and speed must be positive; age cannot be negative.
The adapter does not impose invented normative cutoffs or remove unusual finite
measurements. Report and review the population, protocol, and distributions.

All-missing predictors and per-outcome missing rows are explicitly reported.
Whether enough observed development/evaluation data exist for a model is checked
by the later workflow. Preparation alone does not establish model readiness.

## Inspect the prepared directory

| Artifact | Contents |
| --- | --- |
| `canonical.csv` | The eleven mapped fields, with canonical units and retained missingness |
| `audit.json` | Counts, identifier policies, missing targets, all-missing predictors, ignored-column count, and conversions |
| `missingness.csv` | Every canonical field's missing count and fraction |
| `mapping.json` | The reviewed mapping bytes used for preparation |
| `provenance.json` | Source/mapping/artifact SHA-256 hashes, declarations, units, definitions, and status |

The loader verifies the fixed artifact set and checks canonical schema,
identifiers, units, definitions, audit counts, missingness, and conversion records
for agreement. Modified or stale prepared files fail validation. The original
source CSV's hash is retained, but its raw rows are not copied into the output.

Checksums detect accidental corruption and internal inconsistencies. They are
not a cryptographic signature, an independent measurement audit, evidence of
authorized use, or proof that two cohorts contain different athletes. Preserve
the original permission and collection records separately.

After inspecting the audit, follow [EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md)
to complete and freeze the actual protocol and development models before reading
or evaluating the external outcomes. No prepared table or local external result
is automatically added to the public dashboard or reference snapshot.
