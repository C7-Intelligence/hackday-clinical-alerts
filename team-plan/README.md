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

> **J-Harmony: "A Proactive Medical Care Club."** The **Big 5**: Concierge Care, HRT/TRT, Aesthetics,
> Longevity, and Proactive Medical Care. The demo builds to *proactive*. See §6.

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
- [ ] **Jason:** fill in J-Harmony's services in the §6 talk track, and prep the §6 assets (Stephen's photo stays off git).
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

## 6. Demo script: **J-Harmony, "A Proactive Medical Care Club"**

**Demo length isn't published.** Ask in the Hack Day Slack / hackday@duplocloud.net before the day. Plan
for **3 minutes** and keep the 5-minute version ready. Jason speaks and Stephen drives the demo machine.

> The event's top prize is a pitch to VCs on The AI Conference main stage the next day, so this is an
> investor pitch with a live product in the middle. DuploCloud's judges score the **working product**, not
> the slides, so the live part is never the thing we cut.

### 3-minute run-of-show

| Time | Who | Beat |
| --- | --- | --- |
| 0:00–0:30 | Jason | **J-Harmony + services** |
| 0:30–2:00 | Jason talks, Stephen drives | **Live product**: SYN-007, then the Neo4j graph |
| 2:00–2:40 | Jason | **Proactive**: how this agent powers J-Harmony's patient portal |
| 2:40–3:00 | Both | **The reveal**: Stephen's photo, then he stands |

### Talk track (draft; make it your own)

**0:00 — J-Harmony (30s)**
> "I'm Jason, this is Stephen. We're building **J-Harmony — a Proactive Medical Care Club.**
> Members get our **Big 5**: Concierge Care, HRT/TRT, Aesthetics, Longevity, and Proactive Medical Care.
> Today, healthcare waits for you to get sick. We don't. Let us show you the engine behind that fifth one."

**0:30 — Live product (90s)**, with Stephen driving:
1. "Meet Grace, a synthetic member." Create the triage for **SYN-007** and narrate the live status.
2. All three tiers land: 🔴 **Clinical** ("she's still on metformin and her kidney function just dropped
   to 27, which is dangerous"), 🟠 **Nudge** ("her mammogram is overdue"), 🔵 **Informational** ("nephrology
   visit Friday").
3. Open the Clinical card: "Every alert shows its evidence. The rules decide, and the AI explains in
   plain language. It never invents an alert."
4. Switch to Neo4j: "Now across the whole club: which members on blood-pressure drugs have a
   clinical alert?" The graph lights up SYN-001 and SYN-007. "One patient becomes population health."

**2:00 — Proactive (40s)**
> "Here's where it goes. This agent runs behind J-Harmony's **patient portal**. Every night it
> reviews every member across all of the Big 5, from their concierge visits to their HRT labs to their longevity
> plan. Care gaps become friendly nudges in the portal. Real risks go straight to their concierge care
> team. FYIs keep members informed. Members stop falling through the cracks, because we reach them
> first. That's what *proactive* means."

**2:40 — The reveal (20s)**
> "And proactive care changes lives. We know, because one of us lived it."
>
> *Flip to Stephen's photo: same black shirt, 70 lb lighter.* "Stephen, stand up."
>
> *(Applause, hopefully.)* "That's J-Harmony. Thank you."

Keep the reveal to **20 seconds or less**. Let the applause happen, but don't wait on it. Use the last
line as the cue that you're done.

### 5-minute version (if we get it)

Add after SYN-007: **SYN-003 Daniel Reyes** (a sepsis screen fires from vitals + lactate, and the Spanish
interpreter flag shows) and **SYN-006 Sofia Alvarez** (FYIs only: "it doesn't cry wolf"). Before "Proactive",
add 20s of **why it's trustworthy**: deterministic rules + tests, a knowledge graph, and a swappable LLM,
all hot-loaded into a running DuploCloud platform with no restart.

### Assets to prepare before the day

- [ ] **Stephen's photo** (same black shirt, 70 lb lighter), stored on the demo machine locally and **not in
      this repo**. Have it open in a background window or as a slide so the flip is one keystroke.
- [ ] J-Harmony title slide/logo (optional, for 0:00) and a closing slide with the one-liner + contact.
- [ ] Browser tabs pre-opened on the demo machine: portal (Alert Triage list), Neo4j Browser with the cohort query saved.
- [ ] Rehearse to a timer twice. If you run over at 2:00, skip the Neo4j step, never the reveal.

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
