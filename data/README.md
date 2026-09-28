# Synthetic J-Harmony member data and alert rules

> ⚠️ **Entirely synthetic.** These are fictional members made up for a hackathon demo. Any resemblance to real
> persons is coincidental. Thresholds are **illustrative for a demo, not clinical guidance.**

All dates are anchored to **as-of = 2026-09-29** (Hack Day). The engine evaluates every rule relative to it.

The data reflects what J-Harmony actually sees in its **Big 5** (Concierge Care, HRT/TRT, Aesthetics,
Longevity, Proactive Medical Care), especially the two most common lab stories:

- **TRT**: hematocrit creeping up (erythrocytosis), blood pressure rising, PSA monitoring falling behind.
- **GLP-1 (semaglutide / tirzepatide)**: nausea and poor intake → dehydration → **BUN and creatinine going up**,
  and sometimes a real acute kidney injury. Plus the good news: weight coming off.

## Members

| ID | Name | Age/Sex | Big 5 services | 🔴 Clinical | 🟠 Nudge | 🔵 Informational |
| --- | --- | --- | --- | --- | --- | --- |
| **SYN-001** | **David Park** | 51 M | Concierge, HRT/TRT, Proactive | **Hematocrit 54.8% on TRT** | **BP elevated on TRT**, **BUN/creatinine up on tirzepatide** | **Down 14% body weight**, upcoming appt, new result |
| SYN-002 | Marcus Lee | 46 M | HRT/TRT, Proactive | — | **Hematocrit trending up** (47.1 → 49.8 → 52.6), PSA overdue | Upcoming appt, new result |
| SYN-003 | Priya Raman | 58 F | Concierge, Proactive | **Creatinine 0.9 → 1.6 on semaglutide (AKI)** | A1c overdue | New result |
| SYN-004 | Sofia Alvarez | 38 F | Aesthetics, Proactive | — | **BUN/creatinine up on semaglutide** | Down 13.6% body weight, upcoming appt |
| SYN-005 | Robert Hayes | 63 M | HRT/TRT, Concierge | **BP 184/112 on TRT** | — | New result |
| SYN-006 | Elena Brooks | 44 F | Longevity | — | — | Upcoming appt, new result |
| SYN-007 | James Whitaker | 55 M | Concierge, Proactive | — | Colorectal screening | — |

- **SYN-001 David Park is the short-demo hero.** He's on TRT **and** tirzepatide, so one member shows all
  three tiers *and* both J-Harmony lab stories in 90 seconds.
- **SYN-006 Elena Brooks is the control** (FYIs only), for the "it doesn't cry wolf" beat.
- The boundary cases are deliberate. SYN-005's hematocrit went up then down (no trend alert). SYN-003 lost
  9% (under the 10% weight-progress line). SYN-005's two-reading BP nudge is replaced by the clinical alert.

Exact expected rule IDs per member are in [`expected-alerts.json`](expected-alerts.json). The therapy → risk
knowledge that seeds the Neo4j graph is in [`therapy-risks.json`](therapy-risks.json).

## Record format (`synthetic-patients/SYN-00X.json`)

A simplified, FHIR-inspired shape. Labs and vitals carry LOINC codes. Conditions carry ICD-10 codes.

| Key | Contents |
| --- | --- |
| `id`, `mrn`, `name`, `birthDate`, `sex`, `synthetic` | Demographics |
| `services[]` | Enrolled J-Harmony Big 5 services |
| `conditions[]` | `code` (ICD-10), `display`, `onset`, `status` (`active`/`resolved`), `tags[]` (e.g. `diabetes`) |
| `medications[]` | `name`, `dose`, `route`, `frequency`, `class`, `start`, `status` (`active`/`stopped`) |
| `labs[]` | `code` (LOINC), `display`, `value`, `unit`, `date`, `interpretation` (`N`/`H`/`L`/`HH`/`LL`) |
| `vitals[]` | `code` (LOINC), `display`, `value`, `unit`, `dateTime` |
| `screenings[]` | `type` (`colonoscopy`/`fit`), `date`, `result` |
| `appointments[]` | `date`, `service`, `reason` |
| `encounters[]` | `type`, `date`, `reason` |

Medication `class` values the rules key on: `androgen` (testosterone) and `GLP-1 receptor agonist`
(semaglutide; tirzepatide, a dual GIP/GLP-1 agonist, is grouped here too).

LOINC codes used: hematocrit `4544-3`, total testosterone `2986-8`, PSA `2857-1`, BUN `3094-0`,
creatinine `2160-0`, potassium `2823-3`, HbA1c `4548-4`, ApoB `1884-6`, LDL `13457-7`, systolic BP `8480-6`,
diastolic BP `8462-4`, body weight `29463-7`.

## Rule catalogue

"Latest" means the most recent result on or before as-of. "On TRT" means an active `androgen`. "On GLP-1"
means an active `GLP-1 receptor agonist`.

### 🔴 Clinical (priority 1)

| Rule ID | Fires when | Evidence to attach |
| --- | --- | --- |
| `CLIN-TRT-ERYTHROCYTOSIS` | On TRT and latest hematocrit ≥ 54.0 % | Hematocrit history, testosterone med |
| `CLIN-BP-SEVERE` | Latest BP reading has systolic ≥ 180 **or** diastolic ≥ 120 mmHg (any member) | That BP reading |
| `CLIN-GLP1-AKI` | On GLP-1 and latest creatinine ≥ 1.5 × the previous creatinine drawn within the 180 days before it | Both creatinines, BUN, GLP-1 med |

### 🟠 Nudge (priority 2)

| Rule ID | Fires when |
| --- | --- |
| `NUDGE-TRT-HCT-TREND` | On TRT, latest hematocrit ≥ 50.0 and < 54.0 %, and the last 3 hematocrits are strictly increasing |
| `NUDGE-TRT-BP-ELEVATED` | On TRT, the 2 most recent readings **both** have systolic ≥ 140 **or** both have diastolic ≥ 90, and `CLIN-BP-SEVERE` didn't fire |
| `NUDGE-TRT-PSA-OVERDUE` | On TRT, male, age ≥ 40, and no PSA in the last 365 days |
| `NUDGE-GLP1-HYDRATION` | On GLP-1, latest BUN > 20 mg/dL, BUN ÷ creatinine (same draw date) > 20, and `CLIN-GLP1-AKI` didn't fire |
| `NUDGE-A1C-OVERDUE` | Active condition tagged `diabetes` and no HbA1c in the last 180 days |
| `NUDGE-COLORECTAL-SCREEN` | Age 45–75, no `colonoscopy` in the last 10 years, and no `fit` in the last 365 days |

### 🔵 Informational (priority 3)

| Rule ID | Fires when |
| --- | --- |
| `INFO-WEIGHT-PROGRESS` | On GLP-1 and latest weight ≤ 90 % of the most recent weight on or before the GLP-1 start date (report the % lost) |
| `INFO-UPCOMING-APPT` | An appointment 0–14 days after as-of (one alert, listing the soonest) |
| `INFO-NEW-RESULT` | Any lab with `interpretation` = `N` dated 0–3 days before as-of (one alert, listing them) |

Age is whole years on the as-of date.
