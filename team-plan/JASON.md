# Paste this into Claude Code (Jason)

---

I'm Jason. I'm on a 2-person, 6-hour DuploCloud Hack Day team with Stephen. We're building a **Clinical
Alert Triage** agent as a DuploCloud extension, with a Neo4j knowledge graph. The real goal is a demo
that attracts investors to J-Harmony and impresses AI companies that are hiring, so favour a polished,
reliable end-to-end path over extra features.

The DevKit is cloned at `~/my-agent` in WSL2 Ubuntu, and the platform runs there on Docker Desktop.
**The demo runs on Stephen's Windows machine**, and my laptop is the development box and the backup
(see `team-plan/README.md` §4). Our plan repo is `https://github.com/C7-Intelligence/hackday-clinical-alerts`. Right now it holds
only `team-plan/` and `data/`.

**Step 0: bootstrap (do this first, then stop and report):**
1. Check Docker Desktop is running and `cd ~/my-agent && docker compose ps` shows every service Up. If not,
   run `./run.sh` and wait for `✔ Platform ready`.
2. Adopt the DevKit into our plan repo without losing the plan files: in `~/my-agent`, run
   `./scripts/init-project.sh https://github.com/C7-Intelligence/hackday-clinical-alerts.git --no-sample --name clinical-alerts`,
   then `git pull origin main --allow-unrelated-histories --no-rebase`, resolve anything trivial, and
   `git push -u origin main`. Confirm `.env` is **not** committed.
3. Tell me it's pushed, so Stephen can clone it.

Then read these in full: `team-plan/README.md` (goal, plan, timeline, ownership) and
`team-plan/CONTRACT.md` (the interface with Stephen's engine and graph). Skim `samples/helloworld/`,
which is the agent-based provisioning pattern we're copying, and the Neo4j section of
`hackday/Sponsor Integrations.md`.

**My scope:** everything under `extensions/clinical-alerts/`, plus the portal-side setup, on branch
`jason/extension`. **Don't edit `engine/` or `data/`.** Those are Stephen's. If the contract needs to
change, stop and tell me so I can agree it with him.

Then do this in order:

1. `git checkout -b jason/extension`.
2. Run `/duplo-extension`. Choose **local**. Answer its interview using CONTRACT §2 exactly: extension
   id `c7.clinical-alerts`, resource `AlertTriage`, subType `alert-triage`, restSegment
   `extensions/alerttriages`, the three spec fields, the `TriageResult` shape from CONTRACT §3 (alerts as
   a list of typed objects, `counts` as an object), the left nav **Clinical ▸ Alert Triage**, and
   agent-based provisioning via a skill named `triage-patient`. The resource should select
   `neo4j-mcp-scope` so the agent gets the Neo4j MCP tools.
3. **Stub milestone:** the `triage-patient` skill posts `Processing` with the CONTRACT §5 sub-steps, then
   posts the sample `TriageResult` from CONTRACT §3 as a hard-coded result, then `Complete`. Build,
   deploy, and prove it renders at http://localhost:4210.
4. **Neo4j wiring:** walk me through the Neo4j section of `hackday/Sponsor Integrations.md` (MCP server →
   provider → credentials → `neo4j-mcp-scope` → attach to the `extension-dev` workspace). I'll type the
   Aura credentials into the portal myself, so don't ask me to paste them into chat. Verify with a HelpDesk
   ticket using that scope: "What schema do you see in neo4j?"
5. **UI requirements:**
   - List view: patient name + ID, and three coloured count chips (clinical / nudge / informational).
   - Create form: `patientId` is a dropdown of the 7 patients in `data/synthetic-patients/index.json`,
     shown as "SYN-00X — Name, age sex". Bake the list into the frontend at build time.
   - Detail page: summary banner, then Clinical / Nudge / Informational sections of alert cards (title,
     detail, rationale, recommended action, collapsible evidence table). Use the CONTRACT colours, and show
     an empty state per tier.
   - A persistent banner: **"Synthetic data — not for clinical use."**
   - It should look like a product, not a hackathon form. That matters for the investor demo.
6. **Integration** (once Stephen's engine tests pass and he's pushed `engine/graph/queries.cypher`): write
   `extensions/clinical-alerts/sync-engine.sh` per CONTRACT §4. The real skill does: run the engine CLI
   (exit 2 → `Failed` with the stderr reason) → write the graph with Stephen's Cypher via the MCP tools
   (on any error, post `Graph unavailable — skipped` and continue) → if `explain`, fill each `rationale`
   and the `summary` using Stephen's explain instructions (grounded only in `detail` + `evidence`; never add,
   remove or re-tier alerts) → post results → `Complete`.
7. Verify all 7 patients end to end against `data/expected-alerts.json`. Then run the cohort query and
   confirm it returns SYN-001 and SYN-007.
8. After merging to `main`, write `team-plan/DEPLOY.md`: the exact commands to deploy `main` on a fresh
   machine (pull, `sync-engine.sh`, build, deploy, and the portal steps for `neo4j-mcp-scope`). Stephen uses it on
   the demo machine. Keep my laptop deployed with the same build as the backup.

Working style: keep commits small and push often. Before anything that restarts containers, rewrites
`.env`, or switches the LLM, ask me first. When something fails, check `docs/troubleshooting.md` and the
`duplo-extension-dev` skill references before guessing.
