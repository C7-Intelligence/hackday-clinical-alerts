# Harmony

**Proactive care that runs like an MSP, now with AI.**

Harmony is an AI agent that watches every member of a medical membership the way a managed service
provider watches a network: continuously, by severity, and before anything breaks. It reads each member's
labs, vitals and therapies, and it raises three kinds of alerts. It explains every one in plain language,
and it links what it finds across the whole membership in a knowledge graph.

Built in one day at **The AI Conference Hack Day** (San Francisco, 2026-09-29) by **J-Harmony × Cyber7Group**.

> ⚠️ **Demo with synthetic data only.** Every member is fictional, and the thresholds are illustrative. Harmony
> isn't a medical device and doesn't give medical advice.

---

## The problem

Healthcare waits for you to get sick. Labs come back, sit in a portal, and get looked at weeks later, if
ever. Meanwhile the patterns that matter build up quietly: a hematocrit creeping up on testosterone
therapy, a BUN rising because a GLP-1 is making someone too nauseous to drink water. And when clinicians
*do* get alerts, they get hundreds of undifferentiated ones, and they learn to ignore them.

**J-Harmony** is *a Proactive Medical Care Club*. One all-inclusive monthly membership covers the
**Big 5**: Concierge Care, HRT/TRT, Aesthetics, Longevity, and Proactive Medical Care. **Cyber7Group**
runs the intelligence and infrastructure underneath. Harmony is the engine that makes "proactive" real.

## What Harmony does

For each member, Harmony sorts findings into three tiers, the same way an MSP sorts incidents:

| Tier | MSP equivalent | What it means | Examples |
| --- | --- | --- | --- |
| 🔴 **Clinical** | P1 incident | Act today; the care team reviews | Hematocrit ≥ 54% on TRT · BP ≥ 180/120 · creatinine up 1.5× on a GLP-1 |
| 🟠 **Nudge** | Maintenance ticket | Get ahead of it this week | Hematocrit trending up on TRT · BP creeping up on TRT · PSA overdue · BUN/creatinine rising on a GLP-1 (hydrate) · A1c or colorectal screening overdue |
| 🔵 **Informational** | Status update | Keep the member informed | Weight-loss progress on a GLP-1 · upcoming visit · new normal results |

Then it:
- **explains** each alert in one or two plain sentences, grounded in the member's own evidence;
- **writes the member, their therapies and their alerts into a Neo4j knowledge graph**, so questions about
  the whole membership become one query: *"Which TRT members have a hematocrit problem?"*;
- **shows it all** in the portal: colour-coded alert cards, an evidence table behind every alert, and a
  live progress rail as the agent works.

### Example: David, 51, on TRT and tirzepatide

| | Alert | Why |
| --- | --- | --- |
| 🔴 | **Hematocrit 54.8% on testosterone therapy** | Up from 49.5% → 52.1% → 54.8% over three quarters: clot risk |
| 🟠 | **Blood pressure elevated on TRT** | 144/90, then 148/94 |
| 🟠 | **BUN 26 on GLP-1: hydrate** | BUN/creatinine ratio 24: nausea, not drinking enough |
| 🔵 | **Down 14% body weight** | 112.0 → 96.3 kg since starting tirzepatide |
| 🔵 | Upcoming TRT dose review · new normal result | |

Across the membership, the graph shows **Marcus** (hematocrit 52.6% and rising) on the same path as David.
Harmony flags him *before* he becomes David. That's proactive.

## How it works

```
 Portal (Angular)          Extension backend (C#)          AI agent (Claude, in a ticket)
 ┌─────────────────┐  POST ┌─────────────────────┐ ticket  ┌───────────────────────────────────┐
 │ Clinical ▸      │──────▶│ AlertTriage          │───────▶│ 1. Load member record             │
 │ Alert Triage    │       │ resource: spec,      │        │ 2. Rules engine (Python) ─ decides│
 │ list · detail · │◀──────│ status, results      │◀───────│ 3. Neo4j via MCP ───────── connects│
 │ lifecycle rail  │render └─────────────────────┘ results │ 4. LLM rationale ───────── explains│
 └─────────────────┘                                        │ 5. Post results → Complete         │
                                                            └───────────────────────────────────┘
```

**Rules decide, the graph connects, the AI explains.**

1. **Rules decide.** Twelve small, deterministic rules in pure Python (standard library only) decide
   *whether* an alert fires. The same input always gives the same alerts, with no network or LLM calls,
   and 39 tests pin every member's expected result.
2. **The graph connects.** Members, medications, therapy classes, known therapy risks and alerts go into
   **Neo4j**. That turns one-patient triage into population health: cohorts, trends, and "who's next".
3. **The AI explains.** The LLM writes the rationale and summary *after* the rules have run. It can't add,
   remove or re-tier an alert, and it's grounded only in that alert's evidence.

If the graph is unreachable, triage still completes and marks the graph step as skipped. The safety-critical
path never depends on the network.

## Built with

- **DuploCloud AI DevOps platform (DevKit).** Harmony is a platform extension: a typed resource with a C#
  backend and an Angular federated UI, hot-loaded into a running platform with no restart. Triage runs as
  an agent-based provisioning ticket.
- **Claude (Anthropic).** Powers the provisioning agent and the plain-language explanations. The extension
  itself was built with Claude Code.
- **Neo4j AuraDB** through the Neo4j MCP server. The agent writes and queries the knowledge graph as part of
  every triage.
- **Python 3.11** for the rules engine (standard library only, deterministic, unit-tested).

## Try it

Prerequisites: the DuploCloud DevKit running locally (Docker + WSL2 on Windows; see
[`team-plan/WINDOWS-SETUP.md`](team-plan/WINDOWS-SETUP.md)).

```bash
./run.sh                                                      # start the platform
python3 -m unittest discover engine/tests                     # 39 engine tests
python3 engine/triage.py --patient-id SYN-001 --data-dir data/synthetic-patients
./scripts/build-extension.sh  extensions/clinical-alerts
./scripts/deploy-extension.sh extensions/clinical-alerts/dist/extension.zip
```

Open http://localhost:4210 → **Clinical ▸ Alert Triage → New triage**, and pick a member.

## Repository map

| Path | What's there |
| --- | --- |
| [`extensions/clinical-alerts/`](extensions/clinical-alerts/) | The Harmony extension: manifest, C# backend, Angular UI, `triage-patient` agent skill |
| [`engine/`](engine/README.md) | Rules engine, tests, Neo4j graph model and seed loader, LLM explain instructions |
| [`data/`](data/README.md) | 7 synthetic J-Harmony members, the rule catalogue, expected alerts, therapy-risk knowledge |
| [`team-plan/`](team-plan/README.md) | How we split the day: plan, the extension ⇄ engine contract, per-person Claude Code prompts |
| [`docs/DEVKIT-README.md`](docs/DEVKIT-README.md) | The upstream DuploCloud DevKit readme |

## What we built on the day

Before the event we prepared the **plan, the extension ⇄ engine contract, and the synthetic member data**.
Everything else was built on Hack Day: the extension, the rules engine and tests, the graph model, and the
agent skill. Two people worked in parallel against a written contract, each with their own Claude Code session.

## Team

- **Jason Redwine**: J-Harmony × Cyber7Group · extension, portal UI, agent skill, platform integration
- **Stephen [Last name]**: J-Harmony × Cyber7Group · rules engine, tests, Neo4j knowledge graph

## Disclaimer

Harmony is a hackathon prototype. All member data is synthetic, and the alert thresholds are illustrative,
not clinical guidance. It isn't a medical device and isn't intended to diagnose, treat or replace clinical
judgement.

Built on the [DuploCloud DevKit](https://github.com/duplocloud/devkit) (Apache 2.0); see [`LICENSE`](LICENSE)
and [`NOTICE`](NOTICE).
