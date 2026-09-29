"""Offline checks for engine/graph (no Neo4j needed).

These don't execute Cypher. They check that queries.cypher parses into the named statements the seed and
skill rely on, that the params we send match the jq shape in CONTRACT/queries.cypher, and that the graph
model's linking rule (alert -> risk only via a therapy the member takes) yields the expected cohorts.
Live verification against Aura is `python engine/graph/seed.py --check`.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "graph"))
import seed  # noqa: E402
import triage  # noqa: E402

AS_OF = date(2026, 9, 29)


class Queries(unittest.TestCase):
    def setUp(self):
        self.q = seed.load_queries()

    def test_named_statements_present(self):
        for name in ("write-triage", "cohort-trt-hematocrit", "cohort-glp1-kidney", "alerts-per-program",
                     "trending-toward-clinical", "seed-risks", "seed-member", "seed-reset"):
            self.assertIn(name, self.q)

    def test_statements_are_single_and_parameterised(self):
        for name, text in self.q.items():
            self.assertNotIn(";", text, name)
        write = self.q["write-triage"]
        for p in ("$member.id", "$asOf", "$alerts"):
            self.assertIn(p, write)
        self.assertIn("MERGE (m:Member {id: $member.id})", write)
        self.assertIn("DETACH DELETE old", write)

    def test_no_credentials_in_repo_files(self):
        for path in (seed.QUERIES, os.path.join(ENGINE, "graph", "seed.py")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotRegex(text, r"neo4j\+s://[a-z0-9]{8}\.databases")


class Params(unittest.TestCase):
    def test_triage_params_shape(self):
        result = triage.triage(triage.load_patient(os.path.join(seed.PATIENTS, "SYN-001.json")), AS_OF)
        p = seed.triage_params(result)
        self.assertEqual(set(p), {"member", "asOf", "alerts"})
        self.assertEqual(p["member"], {"id": "SYN-001", "name": "David Park", "age": 51, "sex": "male",
                                       "memberSince": "2024-05-01"})
        self.assertEqual(p["asOf"], "2026-09-29")
        self.assertEqual(len(p["alerts"]), 6)
        for a in p["alerts"]:
            self.assertEqual(set(a), {"id", "ruleId", "tier", "priority", "title"})
        json.dumps(p)  # serialisable for the MCP tool

    def test_member_params_only_active(self):
        for patient in seed.load_members():
            mp = seed.member_params(patient, AS_OF)
            self.assertEqual(len(mp["medications"]),
                             sum(1 for m in patient["medications"] if m["status"] == "active"))


class GraphSemantics(unittest.TestCase):
    """Simulate the model: alert -EXPLAINED_BY-> risk iff member takes the risk's class and ruleId in relatedRules."""

    @classmethod
    def setUpClass(cls):
        risks = seed.load_risks()
        cls.links = {}  # memberId -> list of (alert tier, ruleId, riskId, therapyClass)
        cls.classes = {}
        for patient in seed.load_members():
            mp = seed.member_params(patient, AS_OF)
            classes = {m["class"] for m in mp["medications"]}
            cls.classes[patient["id"]] = classes
            alerts = seed.triage_params(triage.triage(patient, AS_OF))["alerts"]
            cls.links[patient["id"]] = [
                (a["tier"], a["ruleId"], r["id"], r["therapyClass"])
                for a in alerts for r in risks if r["therapyClass"] in classes and a["ruleId"] in r["relatedRules"]
            ]
        cls.expected = seed.load_expected_cohorts()

    def cohort(self, therapy_class, risk_ids):
        return sorted(m for m, links in self.links.items()
                      if any(tc == therapy_class and rid in risk_ids for _, _, rid, tc in links))

    def test_trt_hematocrit_cohort(self):
        self.assertEqual(self.cohort("androgen", {"RISK-TRT-ERYTHROCYTOSIS"}),
                         self.expected["trt-members-with-hematocrit-alert"])

    def test_glp1_kidney_cohort(self):
        self.assertEqual(self.cohort("GLP-1 receptor agonist", {"RISK-GLP1-DEHYDRATION", "RISK-GLP1-AKI"}),
                         self.expected["glp1-members-with-kidney-or-hydration-alert"])

    def test_trending_toward_clinical(self):
        risks = {r["id"]: r for r in seed.load_risks()}
        trending = sorted({m for m, links in self.links.items() for tier, _, rid, _ in links
                           if tier == "nudge" and any(x.startswith("CLIN-") for x in risks[rid]["relatedRules"])
                           and not any(t == "clinical" and r2 == rid for t, _, r2, _ in links)})
        self.assertEqual(trending, ["SYN-001", "SYN-002"])  # David's BP, Marcus's hematocrit


if __name__ == "__main__":
    unittest.main()
