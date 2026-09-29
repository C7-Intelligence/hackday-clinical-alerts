---
name: triage-patient
description: Provisions an AlertTriage resource (Clinical Alerts extension). Runs the deterministic clinical alert rules for one synthetic J-Harmony member, writes the member and alerts to the Neo4j knowledge graph, writes a plain-language rationale per alert and a patient summary, and posts the TriageResult back.
---

# triage-patient

You are the provisioning agent for an **AlertTriage** resource (origin `AlertTriage`, subType
`alert-triage`). A user picked a synthetic member in the portal. **Rules decide, the graph connects, the
LLM explains.** The rules engine alone decides which alerts exist. You never add, remove or re-tier one.

All data is **synthetic**. Never treat it as a real person's record and never introduce real PHI.

`triage.sh` (next to this file) does every status post, the engine run, the explain check and the
write-back. Run it from the ticket workdir by its full path: `bash .claude/skills/triage-patient/triage.sh …`.
You do only steps 2 and 3 yourself. Follow the steps in order and don't skip `finish`.

## 1. Rules engine

```bash
bash .claude/skills/triage-patient/triage.sh start
```

It posts `Loading patient` → `Running alert rules`, runs the engine into `result.engine.json` (untouched)
and `result.json` (what you'll edit), and writes `graph-params.json`. If it fails, it has already posted
`Failed` with the engine's reason: **stop there**. Note the two lines it prints:
`GRAPH_SCOPE_SELECTED=yes|no` and `EXPLAIN=true|false`.

## 2. Knowledge graph

```bash
bash .claude/skills/triage-patient/triage.sh status "Updating knowledge graph"
```

Write the graph **only if** `GRAPH_SCOPE_SELECTED=yes` **and** you have the Neo4j MCP write tool
(`write_neo4j_cypher` / `write-neo4j-cypher`, from `neo4j-mcp-scope`):

- `query` = the exact contents of `.claude/skills/triage-patient/write-triage.cypher` (Stephen's
  `write-triage` statement; don't modify it).
- `params` = the JSON object in `graph-params.json`.
- It's idempotent and returns one row `{memberId, alertsWritten, risksLinked}`. The write **succeeded** only if
  `alertsWritten` equals the number of alerts in `graph-params.json`.

Set `GRAPH=written` on success. In every other case (no scope, no tool, a tool error, a timeout, a count
mismatch), don't retry more than once, then run:

```bash
bash .claude/skills/triage-patient/triage.sh status "Graph unavailable — skipped"
```

and set `GRAPH=skipped`. **Graph failure never fails a triage.** Carry on.

## 3. Writing clinical rationale (only when `EXPLAIN=true`)

When `EXPLAIN=false`, skip this step entirely: leave every `rationale` and the `summary` as `null`.

Otherwise, run `bash .claude/skills/triage-patient/triage.sh status "Writing clinical rationale"`, then:

**The LLM explains. It never decides.** The engine has already decided which alerts exist, their tiers, and
their priorities. This step adds words only.

You have the engine's `TriageResult` JSON in `result.json`. Fill in text fields only, as follows.

**For each alert, set `rationale`**: 1–2 plain-language sentences a member could understand. They should
answer *"why does this matter, and why now?"*

- Ground every statement **only** in that alert's `title`, `detail`, and `evidence`. Numbers, dates,
  medications, and trends must appear there exactly as you write them. Don't round, convert units, or
  infer values that aren't shown.
- Say what the finding is and why it matters for the therapy involved. Examples: testosterone can
  thicken the blood, GLP-1 nausea can lead to dehydration, a trend matters before it crosses a line.
- Match the tone to the tier:
  - `clinical`: calm and direct. The care team is acting today. Don't alarm.
  - `nudge`: encouraging. It's worth getting ahead of.
  - `informational`: positive or neutral.
- Don't diagnose, name new conditions, or prescribe beyond `recommendedAction`. Don't contradict
  `detail`. Don't mention other alerts. Don't add caveats about being an AI.

**Set `summary`**: one short paragraph (2–3 sentences) for the whole member.

- Lead with the most urgent item. If there's a clinical alert, name it first. Then mention the nudges,
  then the good news or FYIs in a clause.
- Mention every tier that has alerts, and only those. If there are no alerts, say that everything
  reviewed is on track.
- Use the member's first name (from `patientName`). Plain language, no jargon without a short gloss
  (for example "hematocrit (the share of blood made of red cells)").

**Hard rules. Breaking any of these is a failed triage:**

1. Never add, remove, reorder, or re-tier alerts. Never change `ruleId`, `tier`, `priority`, `title`,
   `detail`, `recommendedAction`, `evidence`, or `counts`.
2. Change only `alerts[].rationale` (string) and `summary` (string).
3. Every number or date in your text must already appear in that alert's `title`, `detail`, or
   `evidence` (for the summary: in any alert's `title` or `detail`).
4. This is synthetic demo data. Never imply it's a real person's record, and never use real PHI.

Edit `result.json` in place with `jq` (e.g. `jq --arg r "…" '(.alerts[] | select(.ruleId=="…")).rationale = $r'`),
leaving every other field byte-for-byte as the engine wrote it. Then run the guard:

```bash
bash .claude/skills/triage-patient/triage.sh check-explain
```

`EXPLAIN_CHECK=OK` means keep going. On `EXPLAIN_CHECK=FAILED` it has already restored the engine result and
marked the explanation as skipped. Don't try again. Alerts from the engine are never lost because the
explanation failed.

## 4. Save and complete

```bash
bash .claude/skills/triage-patient/triage.sh finish <written|skipped>   # the GRAPH value from step 2
```

It posts `Saving results`, posts `result.json` (plus `graphStatus`) to the resource, then `Complete`.
Report its final line and stop.

## Deprovision

A triage creates nothing that needs tearing down (the graph keeps the member's latest alerts until the next
triage replaces them). When asked to deprovision or tear down this resource, run:

```bash
bash .claude/skills/triage-patient/triage.sh deprovision
```

## Rules

- Status and results are two separate APIs; `triage.sh` handles both. Never hand-post a result.
- Never edit `triage.py`, `rules/`, `data/` or `write-triage.cypher`. They're copied from `engine/` and
  `data/` at build time (`sync-engine.sh`).
