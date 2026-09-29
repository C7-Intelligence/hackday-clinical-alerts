# Deploy `main` on a machine (demo = Stephen's, backup = Jason's)

> ⚠️ Synthetic data only. Not for clinical use.

Run everything in **WSL2 Ubuntu**, in the clone of this repo (e.g. `~/hackday-clinical-alerts`), with Docker
Desktop running. First-time machine setup is [`WINDOWS-SETUP.md`](WINDOWS-SETUP.md).

## 1. Platform up

```bash
cd ~/hackday-clinical-alerts
docker compose ps            # every service Up? If not (or first time):
./run.sh                     # wait for "✔ Platform ready", then sign in at http://localhost:4210
```

Only one DevKit stack can hold the ports. If another clone (e.g. `~/my-agent`) is running, `./stop.sh` it first.
`.env` is created by `run.sh` and is never committed. Keep `DUPLO_TARGET=local`.

## 2. Pull, sync, build, deploy

```bash
git checkout main && git pull
./extensions/clinical-alerts/sync-engine.sh                       # copies engine/ + data/ into the skill. EVERY build.
./scripts/build-extension.sh  extensions/clinical-alerts          # ~1–3 min first time (npm + SDK fetch)
./scripts/deploy-extension.sh extensions/clinical-alerts/dist/extension.zip
```

Expect `sync-engine: engine …, 7 members, write-triage.cypher …`, then `==> Done`, then `==> Loaded (HTTP 200)`.
Refresh the portal: **Clinical ▸ Alert Triage** appears in the left nav. No restart needed.

Re-deploying changed code: bump `version` in `extensions/clinical-alerts/manifest.json` (and the matching
`assemblyDir` / skill `folder`), then repeat step 2.

## 3. Neo4j scope (portal, once per machine, ~10 min)

Full walkthrough with screenshots: [`hackday/Sponsor Integrations.md` → Neo4j](../hackday/Sponsor%20Integrations.md).
Names must match exactly: the create form looks up `neo4j-mcp-scope` by name.

1. **AI Admin → MCP Servers → Add**: Name `neo4j-mcp`, Provider Type `Other` (type `other`), Config Type `Raw`,
   and paste the JSON config from the Sponsor Integrations doc (it uses `${credential.uri}` etc., with no secrets in it).
2. **Providers → IT → Other → Add**: Name `neo4j-mcp`, Type `Other`, Account ID = the Aura `uri`.
3. **Credentials** `neo4j-credentials`: four String fields, all lowercase: `uri`, `username`, `password`,
   `database`. **Type the password from the Aura credentials file yourself. Never paste it into chat, Slack or git.**
4. **Scope** `neo4j-mcp-scope`: credential `neo4j-credentials` + MCP server `neo4j-mcp`.
5. **Attach** it to the `extension-dev` workspace.
6. **Verify**: AI DevOps → new HelpDesk ticket → Select Scopes → `neo4j-mcp-scope` → ask
   *"What schema do you see in neo4j?"* The agent should call the Neo4j tools and list `Member`, `Alert`, `Risk`, ….

## 4. Smoke test (2 min)

1. Clinical ▸ Alert Triage → **New triage**. The form should say **"Knowledge graph connected"**. If it
   says "not attached", redo step 3.5.
2. Pick **SYN-001 — David Park**, **Run triage**. In about 60–90 s: Clinical 1 · Nudge 2 · Info 3, every card has an
   "AI explanation", and the **Knowledge graph** phase on the right is **green** ("Member + 6 alerts written to Neo4j").
   Amber means the graph step was skipped: check the scope, then the agent ticket (**Agent ticket** button).
3. In Neo4j Browser run the `cohort-trt-hematocrit` query from `engine/graph/queries.cypher` → SYN-001, SYN-002.

## 5. Before judging

- Pre-run a completed triage for **every member** (SYN-001…007). If the wifi or LLM is slow on stage, open an
  existing result instead of waiting on a live run.
- Clear old test rows so the list shows one clean run per member (open the row → ⋮ → Delete).
- Jason's laptop runs the **same `main` commit** as the backup. Check with `git log -1 --oneline` on both.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Triage sits on one step for 5+ min ("⚠ Stalled") | The agent lost its LLM connection (network). Run a new triage; delete the stalled row after. |
| `Failed` with "patient file not found" | You built without `sync-engine.sh`. Run step 2 again. |
| Nav item missing after deploy | Hard-refresh the portal (Ctrl+Shift+R). |
| Build fails on `npm ci` | Make sure `extensions/clinical-alerts/frontend/vendor/*.tgz` exists (`git pull`). |
| Anything else | `docs/troubleshooting.md`, then `./logs.sh claude-code-agent`. |
