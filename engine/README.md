# Rules engine

> ⚠️ Synthetic data only. Thresholds are **illustrative for a demo, not clinical guidance.**

**Rules decide, the graph connects, the LLM explains.** This is "rules decide": 12 small, deterministic
rules in pure Python 3.11 stdlib. The engine makes no network or LLM calls and doesn't read the clock.
Every date is relative to `--as-of`, so the same input always gives the same alerts. The LLM never decides
whether an alert fires. It only writes the `rationale` and `summary` text afterwards (see
[`EXPLAIN.md`](EXPLAIN.md)).

```bash
python3 engine/triage.py --patient-id SYN-001 --data-dir data/synthetic-patients
python3 engine/triage.py --patient data/synthetic-patients/SYN-001.json --as-of 2026-09-29 --no-informational
python3 -m unittest discover engine/tests          # 39 tests
```

- Output: one `TriageResult` JSON object on stdout (CONTRACT §3), with `rationale` and `summary` set to `null`.
- Exit `0` on success, including when there are no alerts. Exit `2` with a one-line reason on stderr for
  a missing file, invalid JSON, a missing required field (`id`, `name`, `birthDate`, `sex`), a section that
  isn't a list, an unsafe `--patient-id`, or a bad `--as-of`.
- `--data-dir` defaults to `./data` next to `triage.py` (the skill-folder layout in CONTRACT §4), then to
  `../data/synthetic-patients`.

## Layout

```
engine/
  triage.py            CLI, loading/validation, result assembly, sorting, counts
  rules/
    __init__.py        RULES registry: rule ID -> function(patient, as_of) -> [alert, ...]
    common.py          date parsing, record access, evidence builders (shared, pure)
    clinical.py        CLIN-* rules and their thresholds
    nudge.py           NUDGE-* rules and their thresholds
    informational.py   INFO-* rules and their thresholds
  tests/               stdlib unittest: expected alerts, CLI, robustness, boundaries, graph (offline)
  graph/               Neo4j model, seed loader, Cypher (see graph/README.md)
  EXPLAIN.md           instructions for the LLM "explain" step
```

`triage.py` puts its own directory on `sys.path`, and the rules use package-relative imports. So copying
`triage.py` and `rules/` into `.claude/skills/triage-patient/` works from any working directory, which a
test checks.

## Rules

Definitions: **latest** means the most recent result on or before as-of. **On TRT** means an active
medication of class `androgen` that started on or before as-of. **On GLP-1** means an active
`GLP-1 receptor agonist`. **Age** is whole years on the as-of date. "Within N days" means
0 ≤ (as-of − date) ≤ N.

### 🔴 Clinical (priority 1): act today

| Rule | Fires when | Threshold | Evidence |
| --- | --- | --- | --- |
| `CLIN-TRT-ERYTHROCYTOSIS` | On TRT and latest hematocrit ≥ threshold | **Hct ≥ 54.0 %** | All hematocrits (newest first) and the TRT medication |
| `CLIN-BP-SEVERE` | Latest BP reading (any member) meets either limit | **SBP ≥ 180 or DBP ≥ 120 mmHg** | That reading's systolic and diastolic |
| `CLIN-GLP1-AKI` | On GLP-1 and latest creatinine ≥ ratio × the previous creatinine, and that previous one was drawn within the lookback before the latest | **≥ 1.5×, 180-day lookback** | Both creatinines, BUN from the same draw, and the GLP-1 |

### 🟠 Nudge (priority 2): get ahead of it

| Rule | Fires when | Threshold | Evidence |
| --- | --- | --- | --- |
| `NUDGE-TRT-HCT-TREND` | On TRT, latest hematocrit in the band, and the last 3 are strictly increasing | **50.0 ≤ Hct < 54.0 %** | The last 3 hematocrits and the TRT |
| `NUDGE-TRT-BP-ELEVATED` | On TRT, both of the 2 most recent readings have high systolic, **or** both have high diastolic, and `CLIN-BP-SEVERE` didn't fire | **SBP ≥ 140 / DBP ≥ 90 mmHg** | Both readings and the TRT |
| `NUDGE-TRT-PSA-OVERDUE` | On TRT, male, age ≥ 40, no PSA within the interval | **365 days** | Last PSA (if any), the TRT, and age |
| `NUDGE-GLP1-HYDRATION` | On GLP-1, latest BUN above the limit, BUN ÷ creatinine from the same draw date above the ratio, and `CLIN-GLP1-AKI` didn't fire | **BUN > 20 mg/dL, ratio > 20** | BUN, creatinine, and the GLP-1 |
| `NUDGE-A1C-OVERDUE` | An active condition tagged `diabetes` and no HbA1c within the interval | **180 days** | Last HbA1c (if any) and the diabetes condition |
| `NUDGE-COLORECTAL-SCREEN` | Age in the band, no colonoscopy within 10 years, **and** no FIT within 365 days | **Age 45–75** | Last colorectal screening (if any) and age |

### 🔵 Informational (priority 3): keep them in the loop

| Rule | Fires when | Threshold | Evidence |
| --- | --- | --- | --- |
| `INFO-WEIGHT-PROGRESS` | On GLP-1 and latest weight ≤ ratio × baseline. Baseline is the most recent weight on or before the (earliest active) GLP-1 start date. Reports the % lost. | **≤ 90 % of baseline (≥ 10 % lost)** | Latest and baseline weights, and the GLP-1 |
| `INFO-UPCOMING-APPT` | Any appointment 0–14 days after as-of. One alert names the soonest and counts the rest. | **14 days** | Every appointment in the window |
| `INFO-NEW-RESULT` | Any lab with interpretation `N` dated 0–3 days before as-of. One alert lists them all. | **3 days** | Each such lab |

Alerts are sorted by priority, then rule ID. `counts` always has all three tiers, and they match `alerts`.
`--no-informational` drops the informational tier and sets its count to 0.

## Readings we chose where `data/README.md` was ambiguous

Each of these is the reading that makes `data/expected-alerts.json` pass. None of them changes an
expected alert.

1. **AKI "previous creatinine"** is the one drawn immediately before the latest (on an earlier day). The
   rule fires only if that draw is within 180 days of the latest. We don't search back for the lowest
   value in the window.
2. **BP readings** pair systolic and diastolic by identical timestamp. A reading with only one half still
   counts: the missing half just can't meet a threshold.
3. **"Same draw date"** for the hydration ratio means the same calendar date, ignoring time.
4. **Weight baseline** uses the earliest start date among the member's active GLP-1s. The latest weight
   can be any date on or before as-of.
5. **"Within 10 years"** for colonoscopy is calendar-based (the same day 10 years earlier; 29 Feb falls
   back to 28 Feb). The other windows are exact day counts.
6. **Stopped medications** and medications starting after as-of don't count as "on" a therapy. Resolved
   conditions don't count for the A1c rule.
7. **Results dated after as-of** are ignored everywhere. That's what keeps back-dated runs honest.

## Hardening

- Dates can come with or without times: `2026-09-26`, `2026-09-26T09:05:00`, `…Z`, or `…-07:00`.
  Offsets are converted to UTC before the date part is taken. A test reruns all 7 members with labs as UTC timestamps, vitals as bare dates and appointments with offsets.
- Missing or `null` optional sections (`conditions`, `labs`, `vitals`, …) are treated as empty.
- Individual entries with a non-numeric value or an unparseable date are skipped. They don't crash the triage.
- `--patient-id` only accepts `[A-Za-z0-9_-]`, so it can't be used to read files outside `--data-dir`.
- A missing or invalid record ends in exit 2 with a readable reason, which the skill turns into
  `status: Failed`.

## Why it's trustworthy (slide notes)

- **Deterministic core.** Same record plus the same as-of always gives the same alerts. There's no model
  in the decision path, so swapping the LLM (Anthropic ↔ an open-weight model) can't change which alerts fire.
- **Every alert shows its receipts.** Each one carries the exact labs, vitals and medications that
  triggered it.
- **Tested at the edges.** 39 tests: each member's expected alerts, threshold boundaries
  (hematocrit exactly 54.0 % and 50.0 vs 49.9 %, age 44 vs 45, the 180-day lookback), escalation replacing its nudge (severe BP over
  elevated BP, AKI over hydration), bad input, and the copied-skill layout.
- **Small and readable.** One function per rule, with thresholds as named constants at the top of each
  file. A clinician can review the whole thing in 15 minutes.
