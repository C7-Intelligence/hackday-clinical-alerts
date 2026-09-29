# Knowledge graph (Neo4j AuraDB Free)

> ⚠️ Synthetic data only. Not for clinical use.

**Rules decide, the graph connects, the LLM explains.** This folder is "the graph connects": it turns
one-patient-at-a-time alerts into population questions like *"Which TRT members have a hematocrit
problem?"*

| File | What it is |
| --- | --- |
| [`queries.cypher`](queries.cypher) | Every Cypher statement: the skill's write step, the two demo cohorts, the investor queries, and the seed statements. Each is tagged `// @name …`. |
| [`seed.py`](seed.py) | Loads the 7 members + therapy-risk knowledge + current alerts into Aura, then checks both cohorts against `data/expected-alerts.json`. |
| [`style.grass`](style.grass) | Neo4j Browser colours: alerts coloured by tier using the CONTRACT colours. |

## Model

```
(:Member {id, name, age, sex, memberSince, plan:'All-Inclusive', synthetic:true})
  -[:HAS_CONDITION]->(:Condition {code, display})
  -[:TAKES {dose, route, frequency, start}]->(:Medication {name})-[:IN_CLASS]->(:TherapyClass {name})
  -[:HAS_ALERT {asOf}]->(:Alert:Clinical|Nudge|Informational {id, ruleId, tier, priority, title, asOf})
(:TherapyClass)-[:HAS_RISK]->(:Risk {id, risk, monitor, relatedRules})      // data/therapy-risks.json
(:Alert)-[:EXPLAINED_BY]->(:Risk)
```

This is CONTRACT §6 with three small additions: a tier label on each alert (so Browser can colour by
tier), `priority`/`asOf` on alerts, and medication details on `TAKES`.

**Linking rule:** an alert is `EXPLAINED_BY` a risk only if the member **takes a medication in that risk's
therapy class** and the alert's `ruleId` is in `Risk.relatedRules`. So Robert's (SYN-005) severe BP links
to the TRT hypertension risk because he's on testosterone. The same alert on a member who isn't on TRT
wouldn't be blamed on TRT.

## Seed it (Stephen's laptop, once, and again after any data change)

```bash
cd ~/hackday-clinical-alerts
python3 -m venv engine/graph/.venv
engine/graph/.venv/bin/pip install neo4j

# Credentials: copy the Aura download to the gitignored path (or export NEO4J_URI/USERNAME/PASSWORD).
cp ~/Downloads/Neo4j-*-Created-*.txt engine/graph/neo4j.env

engine/graph/.venv/bin/python engine/graph/seed.py --reset
```

Expected output ends with:

```
Cohort check (data/expected-alerts.json -> cohorts):
  [OK ] trt-members-with-hematocrit-alert: SYN-001, SYN-002
  [OK ] glp1-members-with-kidney-or-hydration-alert: SYN-001, SYN-003, SYN-004
Open alerts per therapy program:
    program  members  clinical  nudge  informational
    TRT      3        2         4      6
    GLP-1    3        2         4      6
    Other    2        0         1      2
Trending toward a clinical alert:
    memberId  member      nudge                                        ...
    SYN-001   David Park  Blood pressure elevated on TRT (148/94 mmHg)  ...
    SYN-002   Marcus Lee  Hematocrit trending up on TRT (52.6%)         ...
Done. Cohorts match.
```

| Flag | Does |
| --- | --- |
| *(none)* | Idempotent load: safe to run any number of times. |
| `--reset` | Deletes every `Member/Condition/Medication/TherapyClass/Risk/Alert` node first, then reloads. Use before the demo. |
| `--no-alerts` | Loads members and knowledge only, so live triages are the only thing writing alerts. The cohort check will fail until all 7 are triaged. |
| `--check` | Only runs the cohort check and population queries. |
| `--dry-run` | Prints every statement name and its params. No driver or network needed. |

The seed writes alerts with **the same `write-triage` statement the skill uses**, so a green seed also
proves the skill's Cypher.

The password is read from the environment or the file and is never printed. `neo4j.env` and `.venv/`
are gitignored.

## The skill's graph step (for Jason's `SKILL.md`)

After the engine runs, build the params with `jq` and call the Neo4j MCP **write** tool with the
`write-triage` statement from `queries.cypher` (copy it verbatim, from `MERGE` to the `RETURN` line,
without the trailing `;`):

```bash
jq '{member: {id: .patientId, name: .patientName, age, sex, memberSince},
     asOf,
     alerts: [.alerts[] | {id, ruleId, tier, priority, title}]}' result.json > graph-params.json
```

- Tool: `write-neo4j-cypher`, with `query` = the `write-triage` statement and `params` = the contents of
  `graph-params.json`.
- It returns one row: `{memberId, alertsWritten, risksLinked}`. For SYN-001 that's 6 alerts and 3 risk links.
- It's idempotent. Re-running a triage replaces that member's alerts and never duplicates nodes.
- On any tool error or missing tool: post `Graph unavailable — skipped` and carry on (CONTRACT §5).

## Demo queries

Open **https://browser.neo4j.io**, connect with the Aura URI and credentials, then:

1. **Style:** browser.neo4j.io is now the new Query app, which ignores `.grass` files. Instead, run a
   query, click each label chip in *Results overview* and pick a colour: Clinical red, Nudge orange,
   Informational blue, Member grey, Risk teal, TherapyClass purple. Then click the ⇅ icon next to
   *Nodes* and drag **Alert** to the bottom of the list, so the tier colour wins over the grey Alert
   colour. `style.grass` still works in the classic Browser or Neo4j Desktop.
2. **Save the queries:** paste each one below into the editor and click ☆ (save as favourite). Name them
   exactly as shown so they're easy to find on stage.

| Favourite name | `queries.cypher` @name | When |
| --- | --- | --- |
| 1 · TRT + hematocrit (graph) | `cohort-trt-hematocrit-graph` | **Short demo.** Lights up David and Marcus. |
| 2 · GLP-1 + kidney/hydration (graph) | `cohort-glp1-kidney-graph` | 5-min demo. David, Priya, Sofia. |
| 3 · TRT + hematocrit (table) | `cohort-trt-hematocrit` | If the picture is too busy. |
| 4 · GLP-1 + kidney/hydration (table) | `cohort-glp1-kidney` | |
| 5 · Alerts per program | `alerts-per-program` | "TRT vs GLP-1 vs other", as a table. |
| 6 · Trending toward clinical | `trending-toward-clinical` | "Call Marcus before he's David." |
| 7 · Club overview | `club-overview` | One-line population summary. |
| 8 · Knowledge map | `knowledge-map` | What the graph knows before any triage. |
| 9 · Member 360 | `:param memberId => 'SYN-001'`, then `member-360` | Everything about David. |

For the graph views, turn on **Connect result nodes** in Browser settings, so the `HAS_ALERT` edges between
nodes already on screen are drawn.

**Bloom / Aura Explore (optional):** perspective → `Alert` category → *Rule-based styling* on property
`tier`: `clinical` → `#C62828`, `nudge` → `#EF6C00`, `informational` → `#1565C0`. Add a search phrase
*"TRT members with hematocrit alerts"* that runs `cohort-trt-hematocrit-graph`.

## Before the demo

- Aura Free **pauses after 3 days without writes**. Open console.neo4j.io the morning of, and resume the
  instance if it's paused.
- Run `seed.py --reset` once, so the graph matches the data exactly, then do the live SYN-001 triage on
  top. The write step is idempotent, so the cohorts don't change.
- Keep a Browser tab open, already connected, with favourite 1 ready to run.

## Verification status

- All statements pass Neo4j's own Cypher 5 linter (`@neo4j-cypher/language-support`: syntax **and**
  semantics).
- `engine/tests/test_graph.py` checks the parser, the param shapes, and the cohort logic offline.
- **Not yet run against a live Neo4j.** The first `seed.py --reset` on Stephen's laptop is the live test.
  It exits non-zero if either cohort doesn't match.
