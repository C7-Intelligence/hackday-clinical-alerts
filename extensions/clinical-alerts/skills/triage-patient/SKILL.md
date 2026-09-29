---
name: triage-patient
description: Provisions an AlertTriage resource (Clinical Alerts extension). Runs clinical alert triage for one synthetic J-Harmony member and posts the TriageResult back to the resource. STUB version - posts a hard-coded SYN-001 result.
---

# triage-patient

You are the provisioning agent for an **AlertTriage** resource (origin `AlertTriage`, subType
`alert-triage`). A user picked a synthetic member in the portal; your job is to triage them and report back.

> **Current version: STUB.** It walks the status sub-steps and posts a fixed SYN-001 (David Park) result.
> The real flow (engine → Neo4j graph → explain) replaces it once the engine lands (CONTRACT §4).

## Inputs

- `shared/alert-triage.json`: the resource: `id`, `ownerWorkspaceId`, `spec.patientId`,
  `spec.includeInformational`, `spec.explain`, `spec.scopeIds`.
- `$DUPLO_BASE` (fall back to `$DUPLO_HOST`) + `$DUPLO_TOKEN`: a token valid only for THIS resource's
  `…/{id}/status` and `…/{id}/results`.

Write-back base: `RES=${DUPLO_BASE:-$DUPLO_HOST}/v1/aiservicedesk/user/data/workspaces/<ownerWorkspaceId>/environment/extensions/alerttriages/<id>`

## Provision

Run the helper from the ticket workdir, exactly as written (the skill is mounted under `.claude/skills/`):

```bash
bash .claude/skills/triage-patient/stub.sh
```

It posts `Processing` with the sub-steps `Loading patient` → `Running alert rules` → `Updating knowledge graph`
→ `Writing clinical rationale` → `Saving results`, posts `sample-result.json` to `$RES/results`, then
`Complete`. On a missing `patientId` it posts `Failed` with a readable fault. Do not edit the result, do not
invent alerts, and do not do any other work. Report the script's final line and stop.

## Deprovision

A triage creates nothing durable, so when asked to deprovision or tear down this resource, just post:

```bash
curl -fsS -X POST "$RES/status" -H "Authorization: Bearer $DUPLO_TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"DeProvisioned"}'
```

## Rules

- Status and results are two separate APIs; never put the result in a status payload.
- All data is **synthetic**. Never add real patient information.
