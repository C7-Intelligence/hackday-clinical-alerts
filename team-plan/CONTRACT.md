# Contract: extension ⇄ engine

This is the interface between Jason's extension and Stephen's engine. **Change it only on `main`, and
only after telling each other.**

## 1. Engine CLI (Stephen implements, Jason calls)

```bash
python3 triage.py --patient <path/to/SYN-00X.json> [--as-of 2026-09-29] [--no-informational]
```

- Prints **one JSON object** (the `TriageResult` in §3, without `summary` or `rationale`) to **stdout**.
- `--as-of` defaults to `2026-09-29`. Every date rule is relative to it, which keeps the demo deterministic.
- Exit `0` on success (including "no alerts"). Exit `2` if the patient file is missing or invalid, with a
  one-line reason on **stderr**. The skill turns that into `status: Failed` with `faults: [<reason>]`.
- Pure Python 3.11 stdlib. No network access, no LLM calls.

Convenience: `python3 triage.py --patient-id SYN-003 --data-dir <dir>` resolves `<dir>/SYN-003.json`.

## 2. Resource shape (Jason implements via `/duplo-extension`)

- Extension id: `c7.clinical-alerts` · Name: **Clinical Alerts**
- Resource: `AlertTriage` · subType `alert-triage` · restSegment `extensions/alerttriages`
- Provisioning mode: agent-based (a skill runs in the ticket, like the `helloworld` sample)
- Left nav: collapsible section **Clinical** → item **Alert Triage** (mat icon `medical_services`)

**Spec**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `patientId` | string | yes | Dropdown populated from `data/synthetic-patients/index.json` (`SYN-001`…`SYN-007`) |
| `includeInformational` | bool | no (default `true`) | Passes `--no-informational` when false |
| `explain` | bool | no (default `true`) | When true, the agent writes `rationale` + `summary` |

**Result** is `TriageResult` (§3).

## 3. `TriageResult` JSON

```json
{
  "patientId": "SYN-001",
  "patientName": "David Park",
  "age": 51,
  "sex": "male",
  "services": ["Concierge Care", "HRT/TRT", "Proactive Medical Care"],
  "asOf": "2026-09-29",
  "engineVersion": "0.1.0",
  "synthetic": true,
  "counts": { "clinical": 1, "nudge": 2, "informational": 3 },
  "alerts": [
    {
      "id": "SYN-001:CLIN-TRT-ERYTHROCYTOSIS",
      "ruleId": "CLIN-TRT-ERYTHROCYTOSIS",
      "tier": "clinical",
      "priority": 1,
      "title": "Hematocrit 54.8% on testosterone therapy",
      "detail": "Hematocrit 54.8% on 2026-09-26 (up from 52.1% and 49.5%) on testosterone cypionate 180 mg weekly.",
      "recommendedAction": "Care team review today: consider holding or reducing TRT dose and repeat CBC.",
      "evidence": [
        { "kind": "lab", "code": "4544-3", "display": "Hematocrit", "value": 54.8, "unit": "%", "date": "2026-09-26" },
        { "kind": "lab", "code": "4544-3", "display": "Hematocrit", "value": 52.1, "unit": "%", "date": "2026-06-15" },
        { "kind": "medication", "display": "Testosterone cypionate 180 mg IM weekly", "date": "2024-06-10" }
      ],
      "rationale": null
    }
  ],
  "summary": null
}
```

- `tier` is one of `clinical` | `nudge` | `informational`. `priority` is 1 for clinical, 2 for nudge, 3 for informational.
- Alerts are sorted by priority, then ruleId.
- `evidence[].kind` is one of `lab` | `vital` | `medication` | `condition` | `immunization` | `screening` | `appointment` | `demographic`.
- `rationale` (per alert) and `summary` (per patient) are `null` from the engine. The **agent** fills them
  in the skill when `explain` is true: 1–2 plain-language sentences each, which must not contradict `detail`.
- UI colours: clinical `#C62828`, nudge `#EF6C00`, informational `#1565C0`.

## 4. Packaging (Jason's build step)

At build time, copy into the skill folder so the ticket workdir has everything:

```
extensions/clinical-alerts/skills/triage-patient/
  SKILL.md                 # Jason: status → run engine → explain → results → Complete
  triage.py                # copied from engine/triage.py
  rules/                   # copied from engine/rules/ (if Stephen splits rules out)
  data/                    # copied from data/synthetic-patients/
```

From the ticket workdir the skill runs:
`python3 .claude/skills/triage-patient/triage.py --patient-id <id> --data-dir .claude/skills/triage-patient/data`

Add a small script (e.g. `extensions/clinical-alerts/sync-engine.sh`) that does the copy, and run it before
every `./scripts/build-extension.sh extensions/clinical-alerts`.

## 5. Status sub-steps (shown live in the UI)

`Loading patient` → `Running alert rules` → `Updating knowledge graph` → `Writing clinical rationale` →
`Saving results` → Complete

If the Neo4j MCP tools aren't available or error out, post the sub-status `Graph unavailable — skipped`
and **carry on**. Graph failure never fails a triage.

## 6. Neo4j graph model (Stephen designs, the skill writes via MCP)

```
(:Member {id, name, age, sex, synthetic:true})
  -[:ENROLLED_IN]->(:Service {name})                  // J-Harmony Big 5
  -[:HAS_CONDITION]->(:Condition {code, display})
  -[:TAKES]->(:Medication {name})-[:IN_CLASS]->(:TherapyClass {name})
  -[:HAS_ALERT {asOf}]->(:Alert {id, ruleId, tier, title})
(:TherapyClass)-[:HAS_RISK]->(:Risk {id, risk, monitor})   // from data/therapy-risks.json
(:Alert)-[:EXPLAINED_BY]->(:Risk)                          // via Risk.relatedRules
```

- The seed (all 7 members + `data/therapy-risks.json`) is loaded ahead of time by
  `engine/graph/seed.py`, which runs on Stephen's laptop with the `neo4j` pip driver.
- At triage time the skill **MERGEs** the `Member` node and its `HAS_ALERT` alerts, replacing that
  patient's previous alerts. It must be idempotent: re-running a triage doesn't duplicate nodes.
- Stephen supplies the exact Cypher in `engine/graph/queries.cypher`. That includes the write statement
  the skill uses and the two demo cohort queries (expected results are in `data/expected-alerts.json` → `cohorts`):
  - *TRT members (`androgen`) with a hematocrit alert* → **SYN-001, SYN-002** (the short-demo query)
  - *GLP-1 members with a kidney or hydration alert* → **SYN-001, SYN-003, SYN-004**
- The skill uses the MCP tools (`write-neo4j-cypher`, `read-neo4j-cypher`) exposed by `neo4j-mcp-scope`.
  The triage resource must select that scope.
