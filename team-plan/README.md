# Hack Day Plan — Clinical Alert Triage Agent

**Team:** Jason Redwine + Stephen · **Event:** DuploCloud Hack Day, 2026-09-29 · **Time box:** 6 hours

> Start of day: each of us opens Claude Code and pastes our own prompt file:
> - Jason → [`JASON.md`](JASON.md)
> - Stephen → [`STEPHEN.md`](STEPHEN.md)
>
> **This file and [`CONTRACT.md`](CONTRACT.md) are the source of truth.** If a decision changes, change it
> here first and tell the other person.

---

## 0. Why we're really here

The goal is **not** to wire in the most sponsors. It's to:

1. **Attract investors to J-Harmony.** The demo should look like a slice of the product: clinical
   intelligence that's safe, explainable, and aware of the whole patient population.
2. **Stand out to AI companies in San Francisco.** Judges and sponsors are hiring. Show engineering
   judgement: a deterministic safety core, an LLM used only where it adds value, a knowledge graph, and
   tests that prove it.

Every scope decision below serves those two goals. If a feature doesn't help the pitch, cut it.

> **TODO (Jason, before the day):** add J-Harmony's one-line pitch and the investor "ask" to §6 so the
> demo closes on it.

---

## 1. What we're building

A **Clinical Alert Triage** agent that runs inside the DuploCloud platform as an extension.

A user picks a (synthetic) patient in the portal → the platform opens a provisioning ticket → the agent
runs our triage skill, which:

1. Loads the patient record.
2. Runs a **deterministic rules engine** that raises alerts in three tiers:
   - 🔴 **Clinical**: safety-critical, act now (critical potassium, positive sepsis screen, dangerous INR).
   - 🟠 **Nudge**: care gaps and preventive care (overdue A1c, missing statin, missing flu shot, overdue screening).
   - 🔵 **Informational**: FYI context (upcoming appointment, interpreter needed, new normal results).
3. Writes the patient, their meds and conditions, and the alerts into a **Neo4j knowledge graph**. The
   graph connects drug classes → known interactions → alerts, so it can answer **population** questions:
   *"Which patients on an ACE inhibitor or ARB have a clinical alert?"*
4. Has the LLM write a **plain-language rationale** per alert and a one-paragraph patient summary.
   **The LLM explains; it never decides whether an alert fires.** That's the safety story.
5. Posts the results back, and the portal renders colour-coded alert cards.

**The pitch in one breath:** *rules decide, the graph connects, the LLM explains.*

---

## 2. Sponsor tools: what's worth it

| Sponsor | What it gives us | Verdict |
| --- | --- | --- |
| **Neo4j** (AuraDB Free + MCP server) | The agent can read and write a graph database during a ticket | ✅ **Core.** Patient ↔ medication ↔ drug class ↔ interaction ↔ alert is naturally a graph. It moves the demo from one patient at a time to population health, which is an investor-grade story. |
| **Crusoe / Nebius via OpenRouter** | Runs the agent's LLM on open-weight models (Qwen, Kimi, GPT-OSS) hosted on their GPUs, via `./scripts/switch-llm.sh gateway` | 🟡 **Optional, last hour only.** Useful as one line in the pitch: because rules decide, swapping to an open model **doesn't change which alerts fire**. That's portability and cost control, and healthcare buyers care about both. The risk: open models are weaker at tool calling and can break the live demo. Only do it if the 3:30 checkpoint is green, **never demo on it**, and switch back with `./scripts/switch-llm.sh anthropic`. |
| **OpenRouter** | Not a separate tool. It's the gateway Crusoe/Nebius are reached through. | Same as above |
| **Vultr** | The agent can manage Vultr cloud servers and networks through the API | ❌ **Skip.** Cloud infrastructure management has nothing to do with clinical alerting. Wiring it in would be exactly the "plugged in, doing nothing" the judges penalise. |

---

## 3. Architecture and who owns what

```
 Portal (Angular remote)         C# backend (typed resource)       Provisioning skill (agent)
 ┌────────────────────┐  POST   ┌─────────────────────────┐ ticket ┌──────────────────────────────┐
 │ Clinical ▸ Alert   │ ──────▶ │ AlertTriage resource    │ ─────▶ │ 1. status Processing          │
 │ Triage: pick pt,   │         │ Spec / Result types     │        │ 2. python3 triage.py  ◀───────┼── Stephen: engine
 │ list, detail cards │ ◀────── │ status + results APIs   │ ◀───── │ 3. write graph (Neo4j MCP) ◀──┼── Stephen: graph model
 └────────────────────┘ render  └─────────────────────────┘ write  │ 4. LLM rationale + summary    │
         JASON                          JASON               back   │ 5. POST results, Complete     │
                                                                   └──────────────────────────────┘
                                                                     JASON owns SKILL.md + wiring
```

| Area | Owner | Path (in the DevKit repo on the day) | Branch |
| --- | --- | --- | --- |
| Extension: manifest, C# backend, Angular UI, `SKILL.md`, build/deploy, Neo4j scope wiring in the portal | **Jason** | `extensions/clinical-alerts/` | `jason/extension` |
| Rules engine (`triage.py`), rules, tests | **Stephen** | `engine/` | `stephen/engine` |
| Neo4j: graph model, seed loader, Cypher queries | **Stephen** | `engine/graph/` | `stephen/engine` |
| Synthetic patients, expected alerts, interaction knowledge | **Stephen** (seeded already) | `data/` | `stephen/engine` |
| Interface between the two | **Both** | `team-plan/CONTRACT.md` | `main` only |

**The one rule that avoids merge pain: Jason doesn't edit `engine/` or `data/`, and Stephen doesn't edit
`extensions/`.**

The engine is **pure Python 3.11 stdlib**. The agent container has Python 3.11, `jq` and Node 22, and
nothing else is guaranteed. The agent reaches Neo4j through the **MCP server** attached to the ticket's
scope, not from Python. Stephen's seed loader runs on his laptop, where `pip install neo4j` is fine.

**Resilience:** alerts come from the engine alone. If Aura or the venue wifi dies, triage still works and
only the graph step is skipped, marked "Graph unavailable". The demo never depends on the network for
its core path.

---

## 4. Demo machine

**The demo runs on Stephen's Windows machine** (the most powerful one), under WSL2 Ubuntu + Docker Desktop.
Setup: [`WINDOWS-SETUP.md`](WINDOWS-SETUP.md).

- Both of us develop against our **own** local platform. Jason builds and tests the extension on his
  laptop, and Stephen runs the engine and graph on his.
- From the **3:30 checkpoint**, `main` is deployed and tested on **Stephen's machine**. That's the only
  build that matters for judging.
- Stephen's portal needs its own Neo4j MCP server, provider, credentials and scope (the same steps Jason
  did on his). Stephen types the Aura credentials into his own portal.
- **Jason's laptop is the backup.** Keep it running with the same `main` build deployed, so if Stephen's
  machine fails during judging we switch laptops in under a minute.
- Before the demo: plug in power, turn off Windows Update restarts and notifications (Focus / Do Not
  Disturb), close heavy apps, and have Docker Desktop already running.

---

## 5. Timeline

### Before the day (by 9/28 evening)
- [ ] **Stephen:** set up the demo machine per [`WINDOWS-SETUP.md`](WINDOWS-SETUP.md) (WSL2, Docker Desktop,
      DevKit, Claude Code). Use a work email. Confirm http://localhost:4210 signs in.
- [ ] **Stephen:** create an **AuraDB Free** instance at console.neo4j.io and **download the credentials
      file immediately** (the password is shown once). Share it with Jason privately, not in git.
- [ ] **Jason:** confirm the stack on his (backup) laptop still starts (open Docker Desktop, then `./run.sh`).
- [ ] **Jason:** fill in the J-Harmony pitch TODO in §0 / §6.
- [ ] **Both:** join the Hack Day Slack and watch the 15-minute walkthrough (vimeo.com/1228174847).

### On the day (6 hours)

| Time | Jason | Stephen | Sync point |
| --- | --- | --- | --- |
| 0:00–0:20 | Bootstrap the repo (JASON.md step 0), check the stack is up, create `jason/extension` | Clone the bootstrapped repo, create `stephen/engine`, `./run.sh` | 5 min: re-read CONTRACT.md together |
| 0:20–2:30 | `/duplo-extension` → scaffold the `AlertTriage` resource, UI, and a **stub** skill that posts the sample result from CONTRACT §3. Register the Neo4j MCP server + scope in the portal (`hackday/Sponsor Integrations.md`, ~15 min). | Build `engine/triage.py` + all rules until `engine/tests` pass. Build `engine/graph/` (model, seed loader, cohort queries) and seed Aura with all 7 patients + interaction knowledge. | **2:30:** the stub renders in the portal, the tests are green, and a HelpDesk ticket with `neo4j-mcp-scope` answers the cohort question |
| 2:30–3:30 | Replace the stub with the real skill: engine → graph write → explain → results | Pair on integration. Hand Jason the "explain" instructions and the Cypher for the skill's graph step. | **3:30:** real alerts for all 7 patients render, and each triage shows up in the graph |
| 3:30–4:45 | UI polish: tier grouping, count chips, evidence table, empty states, a "Population" link or panel showing the cohort query | Hardening + a Neo4j Browser/Bloom view of the graph for the demo (saved queries and styling) | Merge to `main`, then deploy on **Stephen's machine (demo)** and Jason's (backup). Stephen wires `neo4j-mcp-scope` in his portal. |
| 4:45–5:30 | Optional: the Crusoe/Nebius portability experiment (§2). Never demo on it. | Optional: acknowledge/snooze a Nudge | |
| 5:30–6:00 | **Demo rehearsal ×2 on Stephen's machine** (§6). Freeze code. Jason presents. | Drives the machine during the demo. | |

If a checkpoint slips by 30+ minutes, cut in this order: optional items → UI polish → graph visual styling.
**Never cut the end-to-end path.**

---

## 6. Demo script (≈4 minutes, written for investors and hiring managers)

1. **Problem (20s):** "Clinicians see hundreds of alerts a day and ignore most of them. Alert fatigue
   kills. We triage alerts into *act now*, *nudge*, and *FYI*, and we explain every one."
2. **SYN-007 Grace Thompson (hero):** create the triage and narrate the live sub-status. All three tiers
   fire: Clinical (metformin with eGFR 27), Nudge (mammogram overdue), and Informational. Open the
   Clinical card to show the evidence (the eGFR lab) and the LLM's plain-language rationale.
3. **SYN-003 Daniel Reyes:** a sepsis screen fires from vitals + lactate, and the Spanish interpreter flag shows.
4. **SYN-006 Sofia Alvarez (control):** only Informational alerts. "It doesn't cry wolf."
5. **The graph (45s):** switch to Neo4j and ask *"Which patients on an ACE inhibitor or ARB have a
   clinical alert?"* Show the graph: patients → meds → drug class → interaction → alert. "This is how you
   go from one patient to managing a whole population."
6. **Why it's trustworthy (30s):** rules decide, the graph connects, the LLM explains. Show the
   `engine/tests` passing. The LLM is swappable (mention the open-model run if we did it).
7. **Close:** *[J-Harmony pitch + ask. TODO Jason.]* The agent was hot-loaded into a running DuploCloud
   platform with no restart.

---

## 7. Definition of done

- [ ] "Clinical ▸ Alert Triage" appears in the portal left nav (hot-loaded, no restart).
- [ ] Creating a triage for any of `SYN-001`…`SYN-007` goes Processing → Complete, with live sub-status updates.
- [ ] The detail page groups alerts Clinical / Nudge / Informational, each with title, rationale, evidence and action.
- [ ] Each patient's alerts exactly match `data/expected-alerts.json` (rule IDs).
- [ ] Every completed triage writes its alerts into Neo4j, and the cohort query returns SYN-001 and SYN-007.
- [ ] If Neo4j is unreachable, triage still completes and marks the graph step skipped.
- [ ] A missing or bad patient ID ends in **Failed** with a readable fault, not a hang.
- [ ] Every screen is labelled **synthetic data, not for clinical use**.

---

## 8. Guardrails

- **Synthetic data only.** No real PHI, ever, including in prompts, screenshots, Slack and Neo4j.
- Rule thresholds are **illustrative for a demo**, not clinical guidance. Say so on screen.
- Never commit `.env` or the Neo4j credentials file. `.env` is already gitignored.
- The demo runs on **Stephen's machine**. Test the final build there, not only on Jason's laptop.
