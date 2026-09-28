# Paste this into Claude Code (Stephen)

---

I'm Stephen. I'm on a 2-person, 6-hour DuploCloud Hack Day team with Jason. We're building a **Clinical
Alert Triage** agent as a DuploCloud extension, with a Neo4j knowledge graph. The real goal is a demo
that attracts investors to J-Harmony and impresses AI companies that are hiring, so correctness and a
clean, explainable design matter more than extra features.

**My machine is the demo machine** (Windows 11 + WSL2 Ubuntu + Docker Desktop; see
`team-plan/WINDOWS-SETUP.md` and `team-plan/README.md` §4). Work inside Ubuntu, not in `/mnt/c`.

**Setup:** make sure Docker Desktop is running. Jason has bootstrapped our repo (DevKit + plan). Clone
`https://github.com/C7-Intelligence/hackday-clinical-alerts` to `~/hackday-clinical-alerts`. If the
`~/my-agent` DevKit stack from my pre-day setup is running, run `./stop.sh` there first, then run `./run.sh`
in the new clone. Then read these in
full: `team-plan/README.md` (goal, plan, timeline, ownership), `team-plan/CONTRACT.md` (my engine's CLI,
its output, and the graph model), and `data/README.md` (the rule catalogue and patient format).

**My scope:** the rules engine and graph in `engine/`, plus `data/`, on branch `stephen/engine`. **Don't
edit `extensions/`.** That's Jason's. If the contract needs to change, stop and tell me so I can agree it
with him.

Do this in order:

1. `git checkout -b stephen/engine`.
2. **Engine.** Build `engine/triage.py` to CONTRACT §1. It must be **pure Python 3.11 stdlib**,
   deterministic, and do no network or LLM calls.
   - `engine/triage.py`: CLI, loading, result assembly, sorting, counts.
   - `engine/rules/`: one small function per rule ID in `data/README.md`, each taking `(patient, as_of)`
     and returning zero or more alerts in the CONTRACT §3 shape, with real `evidence` from the record.
   - Keep imports relative to `triage.py`'s own directory, because it gets copied into a skill folder
     (CONTRACT §4).
3. **Tests.** Write `engine/tests/test_expected.py` (stdlib `unittest`). Every patient's rule-ID set must
   equal `data/expected-alerts.json`. Also test: an unknown ID exits 2, malformed JSON exits 2,
   `--no-informational` drops that tier, `counts` matches `alerts`, and missing optional sections don't
   crash. Run with `python3 -m unittest discover engine/tests`.
4. **Neo4j graph** (CONTRACT §6). I have the AuraDB Free credentials file locally. Load it from an
   env var or a gitignored file, and **never commit it or print the password**.
   - `engine/graph/seed.py` (a `pip install neo4j` venv is fine; it runs on my laptop, not in the agent):
     idempotently load all 7 members, their services, conditions, meds → therapy classes, and
     `data/therapy-risks.json`.
     Add a `--reset` flag to wipe and reload the demo data.
   - `engine/graph/queries.cypher`: the parameterised **write** statement the skill runs per triage
     (MERGE patient, replace that patient's alerts, link alerts to risks), the two **cohort queries** in CONTRACT §6 (results must match
     `cohorts` in `data/expected-alerts.json`), and 2–3 more investor-friendly queries (e.g. "open alerts per
     Big 5 service", "members trending toward a clinical alert").
   - A Neo4j Browser/Bloom setup for the demo: saved queries and node colours by tier, documented in
     `engine/graph/README.md`.
5. **2:30 checkpoint:** tests green, graph seeded, everything pushed. Tell Jason, and paste him the output
   of `python3 engine/triage.py --patient-id SYN-001 --data-dir data/synthetic-patients`.
6. **Explain instructions:** draft the text Jason's `SKILL.md` uses to make the agent write each alert's
   `rationale` and the patient `summary`: plain language, 1–2 sentences, grounded only in `detail` +
   `evidence`, and never adding, removing or re-tiering alerts. Put it in `engine/EXPLAIN.md` and pair with
   Jason on integration.
7. **Hardening:** handle dates with or without times, and write `engine/README.md` listing each rule, its
   tier, its logic and its threshold. That README is part of the "why it's trustworthy" slide.

8. **Demo machine (from the 3:30 checkpoint):** pull `main` and deploy the extension on my machine using
   Jason's `team-plan/DEPLOY.md`. Walk me through wiring `neo4j-mcp-scope` in *my* portal
   (`hackday/Sponsor Integrations.md`, Neo4j section); I'll type the Aura credentials myself. Then run all 7
   members plus both cohort queries end to end on this machine, and fix anything that differs from Jason's.
   Nothing is done until it works here.

If a rule in `data/README.md` is ambiguous, pick the reading that makes `data/expected-alerts.json` pass and
note it in `engine/README.md`. **Don't change the expected alerts to fit the code** unless we agree the
data is wrong.
