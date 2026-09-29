#!/usr/bin/env python3
"""Seed the Clinical Alert Triage knowledge graph in Neo4j (AuraDB Free).

Runs on Stephen's laptop, not in the agent container. Needs the official driver:

    python3 -m venv engine/graph/.venv && engine/graph/.venv/bin/pip install neo4j
    engine/graph/.venv/bin/python engine/graph/seed.py            # idempotent load + cohort check
    engine/graph/.venv/bin/python engine/graph/seed.py --reset    # wipe the demo labels, then reload
    engine/graph/.venv/bin/python engine/graph/seed.py --check    # only run the cohort check
    python3 engine/graph/seed.py --dry-run                        # no driver/network: show what would run

Credentials come from the environment (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, optional
NEO4J_DATABASE) or, failing that, from a KEY=VALUE file (the Aura credentials download works as-is).
The default file is engine/graph/neo4j.env, which is gitignored. The password is never printed.

What it loads (every Cypher statement comes from engine/graph/queries.cypher):
  1. uniqueness constraints
  2. therapy -> risk knowledge from data/therapy-risks.json
  3. all 7 synthetic members with active conditions and medications -> therapy classes
  4. each member's current alerts, by running the rules engine and the SAME `write-triage` statement the
     skill uses (skip with --no-alerts if you want live triages to be the only writer)
  5. the two demo cohort queries, checked against data/expected-alerts.json -> cohorts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
REPO = os.path.dirname(ENGINE)
DATA = os.path.join(REPO, "data")
PATIENTS = os.path.join(DATA, "synthetic-patients")
QUERIES = os.path.join(HERE, "queries.cypher")
DEFAULT_ENV_FILE = os.path.join(HERE, "neo4j.env")

sys.path.insert(0, ENGINE)
import triage as engine  # noqa: E402

COHORTS = {
    "trt-members-with-hematocrit-alert": "cohort-trt-hematocrit",
    "glp1-members-with-kidney-or-hydration-alert": "cohort-glp1-kidney",
}


# --------------------------------------------------------------------------- queries.cypher


def load_queries(path: str = QUERIES) -> dict[str, str]:
    """Parse `// @name <name>` blocks, each ending at the first line that ends with `;`."""
    queries: dict[str, str] = {}
    name, lines = None, []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = re.match(r"^\s*//\s*@name\s+(\S+)\s*$", line)
            if m:
                name, lines = m.group(1), []
                continue
            if name is None:
                continue
            if line.strip().startswith("//") and not lines:
                continue
            lines.append(line)
            if line.rstrip().endswith(";"):
                text = "\n".join(lines).rstrip().rstrip(";").strip()
                if name in queries:
                    raise ValueError(f"duplicate query name {name!r} in {path}")
                queries[name] = text
                name, lines = None, []
    if name is not None:
        raise ValueError(f"query {name!r} in {path} has no terminating ';'")
    return queries


# --------------------------------------------------------------------------- params


def triage_params(result: dict) -> dict:
    """Params for `write-triage` from a TriageResult. Mirrors the jq one-liner in queries.cypher."""
    return {
        "member": {k2: result[k1] for k1, k2 in (("patientId", "id"), ("patientName", "name"), ("age", "age"),
                                                 ("sex", "sex"), ("memberSince", "memberSince"))},
        "asOf": result["asOf"],
        "alerts": [{k: a[k] for k in ("id", "ruleId", "tier", "priority", "title")} for a in result["alerts"]],
    }


def member_params(patient: dict, as_of: date) -> dict:
    conditions = [
        {"code": c.get("code"), "display": c.get("display"), "onset": c.get("onset")}
        for c in patient.get("conditions") or [] if c.get("status", "active") == "active" and c.get("code")
    ]
    medications = [
        {"name": m.get("name"), "class": m.get("class"), "dose": m.get("dose"), "route": m.get("route"),
         "frequency": m.get("frequency"), "start": m.get("start")}
        for m in patient.get("medications") or []
        if m.get("status", "active") == "active" and m.get("name") and m.get("class")
    ]
    membership = patient.get("membership") or {}
    return {
        "member": {"id": patient["id"], "name": patient["name"], "age": engine.patient_age(patient, as_of),
                   "sex": patient["sex"], "memberSince": membership.get("since")},
        "conditions": conditions,
        "medications": medications,
    }


def load_members() -> list[dict]:
    with open(os.path.join(PATIENTS, "index.json"), encoding="utf-8") as fh:
        index = json.load(fh)
    return [engine.load_patient(os.path.join(PATIENTS, p["file"])) for p in index["patients"]]


def load_risks() -> list[dict]:
    with open(os.path.join(DATA, "therapy-risks.json"), encoding="utf-8") as fh:
        return json.load(fh)["risks"]


def load_expected_cohorts() -> dict[str, list[str]]:
    with open(os.path.join(DATA, "expected-alerts.json"), encoding="utf-8") as fh:
        return json.load(fh)["cohorts"]


def plan(as_of: date, reset: bool, with_alerts: bool, queries: dict[str, str]) -> list[tuple[str, dict]]:
    """The ordered list of (query name, params) the seed runs."""
    steps: list[tuple[str, dict]] = [(n, {}) for n in queries if n.startswith("seed-constraint-")]
    if reset:
        steps.append(("seed-reset", {}))
    steps.append(("seed-risks", {"risks": load_risks()}))
    members = load_members()
    steps += [("seed-member", member_params(p, as_of)) for p in members]
    if with_alerts:
        steps += [("write-triage", triage_params(engine.triage(p, as_of))) for p in members]
    return steps


# --------------------------------------------------------------------------- credentials


def read_env_file(path: str) -> dict[str, str]:
    values = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def credentials(env_file: str | None) -> dict[str, str]:
    creds = {k: os.environ[k] for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")
             if os.environ.get(k)}
    path = env_file or DEFAULT_ENV_FILE
    if not {"NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"} <= set(creds) and os.path.exists(path):
        for k, v in read_env_file(path).items():
            creds.setdefault(k, v)
    missing = [k for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD") if not creds.get(k)]
    if missing:
        sys.exit(f"seed: missing {', '.join(missing)}. Set them in the environment or in {path} "
                 f"(the Aura credentials file works as-is).")
    return creds


# --------------------------------------------------------------------------- run


def check_cohorts(run, queries: dict[str, str]) -> bool:
    expected = load_expected_cohorts()
    ok = True
    for cohort, query_name in COHORTS.items():
        rows = run(query_name, {})
        got = sorted({r["memberId"] for r in rows})
        want = sorted(expected[cohort])
        status = "OK " if got == want else "FAIL"
        ok &= got == want
        print(f"  [{status}] {cohort}: {', '.join(got) or '(none)'}" + ("" if got == want else f"  (expected {', '.join(want)})"))
        for r in rows:
            print(f"         {r['memberId']} {r['member']:<14} {r['tier']:<13} {r['alert']}")
    return ok


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("    (no rows)")
        return
    keys = list(rows[0].keys())
    widths = {k: max(len(k), *(len(str(r[k])) for r in rows)) for k in keys}
    print("    " + "  ".join(k.ljust(widths[k]) for k in keys))
    for r in rows:
        print("    " + "  ".join(str(r[k]).ljust(widths[k]) for k in keys))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Seed the Clinical Alert Triage graph (synthetic data only).")
    ap.add_argument("--env-file", help=f"KEY=VALUE credentials file (default {os.path.relpath(DEFAULT_ENV_FILE, REPO)})")
    ap.add_argument("--reset", action="store_true", help="delete all demo nodes first, then reload")
    ap.add_argument("--no-alerts", action="store_true", help="load members and knowledge only, no alerts")
    ap.add_argument("--check", action="store_true", help="only run the cohort check and population queries")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; don't connect to Neo4j")
    ap.add_argument("--as-of", default=engine.DEFAULT_AS_OF)
    args = ap.parse_args(argv)

    as_of = date.fromisoformat(args.as_of)
    queries = load_queries()
    steps = [] if args.check else plan(as_of, args.reset, not args.no_alerts, queries)

    if args.dry_run:
        for name, params in steps:
            print(f"-- {name}")
            if params:
                print(json.dumps(params, indent=2, ensure_ascii=False))
        print(f"-- then check: {', '.join(COHORTS.values())}")
        return 0

    try:
        from neo4j import GraphDatabase
    except ImportError:
        sys.exit("seed: the neo4j driver isn't installed. Run: python3 -m venv engine/graph/.venv && "
                 "engine/graph/.venv/bin/pip install neo4j")

    creds = credentials(args.env_file)
    database = creds.get("NEO4J_DATABASE") or None
    print(f"Connecting to {creds['NEO4J_URI']} as {creds['NEO4J_USERNAME']}"
          + (f" (database {database})" if database else ""))
    with GraphDatabase.driver(creds["NEO4J_URI"], auth=(creds["NEO4J_USERNAME"], creds["NEO4J_PASSWORD"])) as driver:
        driver.verify_connectivity()

        def run(name: str, params: dict) -> list[dict]:
            records, _, _ = driver.execute_query(queries[name], params, database_=database)
            return [r.data() for r in records]

        if steps:
            print(f"Seeding{' (reset first)' if args.reset else ''}...")
            for name, params in steps:
                rows = run(name, params)
                if name == "write-triage":
                    r = rows[0]
                    print(f"  write-triage {r['memberId']}: {r['alertsWritten']} alerts, {r['risksLinked']} risk links")
                elif name == "seed-member":
                    print(f"  member {rows[0]['memberId']}")
                elif name == "seed-risks":
                    print(f"  {rows[0]['risks']} therapy risks")
                elif name == "seed-reset":
                    print("  reset: demo nodes deleted")
            print("  constraints ensured")

        print("Cohort check (data/expected-alerts.json -> cohorts):")
        ok = check_cohorts(run, queries)
        print("Open alerts per therapy program:")
        print_table(run("alerts-per-program", {}))
        print("Trending toward a clinical alert:")
        print_table(run("trending-toward-clinical", {}))
        print("Club overview:")
        print_table(run("club-overview", {}))

    if not ok:
        print("seed: cohort check FAILED", file=sys.stderr)
        return 1
    print("Done. Cohorts match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
