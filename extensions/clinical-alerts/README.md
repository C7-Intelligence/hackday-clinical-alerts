# Clinical Alerts (`c7.clinical-alerts`)

J-Harmony × Cyber7Group Hack Day extension: **Clinical ▸ Alert Triage** in the DuploCloud portal.
Pick a synthetic member, and the `triage-patient` agent skill runs the deterministic alert rules, writes the
member and alerts into Neo4j, has the LLM explain each alert, and posts a colour-coded result.
*Rules decide, the graph connects, the LLM explains.* Interface: [`team-plan/CONTRACT.md`](../../team-plan/CONTRACT.md).

> ⚠️ Synthetic data only. Not for clinical use.

| | |
|---|---|
| Resource | `AlertTriage` · subType `alert-triage` · `…/environment/extensions/alerttriages` · Mongo `extension_alerttriage` |
| Mode | Agent (skill `triage-patient`) |
| Spec | `patientId` (SYN-001…007), `includeInformational` (default true), `explain` (default true), `scopeIds` (auto: `neo4j-mcp-scope`) |
| Result | `TriageResult` (CONTRACT §3) + optional `graphStatus` |

```
backend/     AlertTriage.cs (spec/result/entity/service), AlertTriageController.cs
frontend/    Angular 22 Native-Federation remote `c7ClinicalAlerts`: list · add · view
             scripts/gen-patients.mjs bakes data/synthetic-patients/index.json into the member dropdown (npm prebuild)
skills/      triage-patient: SKILL.md (agent: graph write + explain) + triage.sh (status, engine, guard, write-back)
             triage.py, rules/, data/, write-triage.cypher are COPIED in by sync-engine.sh (gitignored)
```

## Build and deploy (from the repo root)

```bash
./extensions/clinical-alerts/sync-engine.sh          # copy engine/ + data/ into the skill (every build)
./scripts/build-extension.sh  extensions/clinical-alerts
./scripts/deploy-extension.sh extensions/clinical-alerts/dist/extension.zip
```

Bump `manifest.json` `version` (and the matching `assemblyDir` / skill `folder`) before re-deploying changed backend code.
