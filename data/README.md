# Synthetic patient data and alert rules

> ⚠️ **Entirely synthetic.** These are fictional people made up for a hackathon demo. Any resemblance to real
> persons is coincidental. Thresholds are **illustrative for a demo, not clinical guidance.**

All dates are anchored to **as-of = 2026-09-29** (Hack Day). The engine evaluates every rule relative to it.

## Patients

| ID | Name | Age/Sex | 🔴 Clinical | 🟠 Nudge | 🔵 Informational |
| --- | --- | --- | --- | --- | --- |
| SYN-001 | Walter Okafor | 72 M | Hyperkalemia on ACEi + spironolactone | — | Upcoming appt, advance directive |
| SYN-002 | Priya Raman | 58 F | — | A1c overdue, no statin (diabetes), flu vaccine | — |
| SYN-003 | Daniel Reyes | 44 M | Sepsis screen positive | — | Interpreter (Spanish), new result |
| SYN-004 | Eleanor Whitfield | 81 F | INR 5.2 on warfarin + new ciprofloxacin | — | Upcoming appt, advance directive, new result |
| SYN-005 | Marcus Lee | 52 M | — | Colorectal screening, flu vaccine | New result |
| SYN-006 | Sofia Alvarez | 34 F | — | — | Interpreter (Spanish), upcoming appt |
| SYN-007 | Grace Thompson | 67 F | Metformin with eGFR 27 | Mammogram overdue | Upcoming appt, new result |

**SYN-007 is the demo hero** because all three tiers fire. **SYN-006 is the control**: informational only.
Exact expected rule IDs per patient are in [`expected-alerts.json`](expected-alerts.json).
The drug-class interaction knowledge that seeds the Neo4j graph is in [`drug-interactions.json`](drug-interactions.json).

## Record format (`synthetic-patients/SYN-00X.json`)

A simplified, FHIR-inspired shape. Labs and vitals carry LOINC codes. Conditions carry ICD-10 codes.

| Key | Contents |
| --- | --- |
| `id`, `mrn`, `name`, `birthDate`, `sex`, `preferredLanguage`, `advanceDirectiveOnFile`, `synthetic` | Demographics |
| `conditions[]` | `code` (ICD-10), `display`, `onset`, `status` (`active`/`resolved`), `tags[]` (e.g. `diabetes`) |
| `medications[]` | `name`, `dose`, `route`, `frequency`, `class`, `start`, `status` (`active`/`stopped`) |
| `labs[]` | `code` (LOINC), `display`, `value`, `unit`, `date`, `interpretation` (`N`/`H`/`L`/`HH`/`LL`) |
| `vitals[]` | `code` (LOINC), `display`, `value`, `unit`, `dateTime` |
| `immunizations[]` | `vaccine`, `date` |
| `screenings[]` | `type` (`colonoscopy`/`fit`/`mammogram`/`retinal_exam`), `date`, `result` |
| `appointments[]` | `date`, `department`, `reason` |
| `encounters[]` | `type`, `date`, `reason` |

Medication `class` values the rules key on: `ACE inhibitor`, `ARB`, `potassium-sparing diuretic`,
`vitamin K antagonist`, `fluoroquinolone`, `biguanide`, `statin`.

## Rule catalogue

"Latest" means the most recent result by date that is on or before as-of.

### 🔴 Clinical (priority 1)

| Rule ID | Fires when | Evidence to attach |
| --- | --- | --- |
| `CLIN-HYPERKALEMIA` | Latest potassium (LOINC `2823-3`) ≥ 6.0 mmol/L. Mention the escalation in `detail` if the patient is on an active ACE inhibitor/ARB **and** a potassium-sparing diuretic. | K lab, the interacting meds |
| `CLIN-SEPSIS-SCREEN` | Within 24 h of as-of: ≥ 2 SIRS criteria (temp > 38.0 or < 36.0 °C `8310-5`; HR > 90 `8867-4`; RR > 20 `9279-1`; WBC > 12 or < 4 ×10³/µL `6690-2`) **and** hypoperfusion (lactate ≥ 2.0 mmol/L `2524-7` **or** systolic BP ≤ 100 mmHg `8480-6`) | Each abnormal vital/lab |
| `CLIN-INR-SUPRATHERAPEUTIC` | Active `vitamin K antagonist` and latest INR (`6301-6`) > 4.0. Mention any interacting med (`fluoroquinolone`) started in the last 14 days. | INR lab, warfarin, interacting med |
| `CLIN-METFORMIN-RENAL` | Active `biguanide` and latest eGFR (`98979-8`) < 30 | eGFR lab, metformin |

### 🟠 Nudge (priority 2)

| Rule ID | Fires when |
| --- | --- |
| `NUDGE-A1C-OVERDUE` | Active condition tagged `diabetes` and no HbA1c (`4548-4`) in the last 180 days |
| `NUDGE-STATIN-DIABETES` | Active `diabetes`, age 40–75, and no active `statin` |
| `NUDGE-FLU-VACCINE` | No `influenza` immunization on or after 2026-08-01 (the 2026–27 season) |
| `NUDGE-COLORECTAL-SCREEN` | Age 45–75, no `colonoscopy` in the last 10 years, and no `fit` in the last 365 days |
| `NUDGE-MAMMOGRAM` | Female, age 50–74, and no `mammogram` in the last 730 days |

### 🔵 Informational (priority 3)

| Rule ID | Fires when |
| --- | --- |
| `INFO-UPCOMING-APPT` | An appointment 0–14 days after as-of (one alert, listing the soonest) |
| `INFO-INTERPRETER` | `preferredLanguage` isn't `en` |
| `INFO-ADVANCE-DIRECTIVE` | `advanceDirectiveOnFile` is true |
| `INFO-NEW-RESULT` | Any lab with `interpretation` = `N` dated 0–3 days before as-of (one alert, listing them) |

Age is whole years on the as-of date.
