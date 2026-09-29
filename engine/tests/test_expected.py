"""Engine tests. Run from the repo root: python3 -m unittest discover engine/tests"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
REPO = os.path.dirname(ENGINE)
DATA = os.path.join(REPO, "data")
PATIENTS = os.path.join(DATA, "synthetic-patients")
TRIAGE = os.path.join(ENGINE, "triage.py")
AS_OF = date(2026, 9, 29)

sys.path.insert(0, ENGINE)
import triage  # noqa: E402
from rules import RULES  # noqa: E402

with open(os.path.join(DATA, "expected-alerts.json"), encoding="utf-8") as fh:
    EXPECTED = json.load(fh)


def load(pid: str) -> dict:
    with open(os.path.join(PATIENTS, f"{pid}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def run_cli(*args, script=TRIAGE):
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True, timeout=30)


def rule_ids(result: dict) -> set:
    return {a["ruleId"] for a in result["alerts"]}


class ExpectedAlerts(unittest.TestCase):
    def test_every_patient_matches_expected_alerts(self):
        for pid, expected in EXPECTED["patients"].items():
            with self.subTest(patient=pid):
                proc = run_cli("--patient-id", pid, "--data-dir", PATIENTS)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(rule_ids(json.loads(proc.stdout)), set(expected))

    def test_rule_catalogue_is_complete(self):
        expected_ids = {r for ids in EXPECTED["patients"].values() for r in ids}
        self.assertTrue(expected_ids <= set(RULES))
        self.assertEqual(len(RULES), 12)

    def test_patient_path_and_patient_id_agree(self):
        a = run_cli("--patient", os.path.join(PATIENTS, "SYN-001.json"))
        b = run_cli("--patient-id", "SYN-001", "--data-dir", PATIENTS)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_deterministic(self):
        runs = {run_cli("--patient-id", "SYN-001", "--data-dir", PATIENTS).stdout for _ in range(3)}
        self.assertEqual(len(runs), 1)


class ResultShape(unittest.TestCase):
    def setUp(self):
        self.results = {pid: triage.triage(load(pid), AS_OF) for pid in EXPECTED["patients"]}

    def test_counts_match_alerts(self):
        for pid, r in self.results.items():
            with self.subTest(patient=pid):
                self.assertEqual(set(r["counts"]), {"clinical", "nudge", "informational"})
                for tier, n in r["counts"].items():
                    self.assertEqual(n, sum(1 for a in r["alerts"] if a["tier"] == tier))

    def test_sorted_by_priority_then_rule_id(self):
        for pid, r in self.results.items():
            keys = [(a["priority"], a["ruleId"]) for a in r["alerts"]]
            self.assertEqual(keys, sorted(keys), pid)

    def test_alert_fields(self):
        kinds = {"lab", "vital", "medication", "condition", "immunization", "screening", "appointment", "demographic"}
        priority = {"clinical": 1, "nudge": 2, "informational": 3}
        for pid, r in self.results.items():
            self.assertEqual(r["patientId"], pid)
            self.assertIsNone(r["summary"])
            self.assertTrue(r["synthetic"])
            self.assertEqual(r["asOf"], "2026-09-29")
            for a in r["alerts"]:
                with self.subTest(alert=a["id"]):
                    self.assertEqual(a["id"], f"{pid}:{a['ruleId']}")
                    self.assertEqual(a["priority"], priority[a["tier"]])
                    self.assertTrue(a["ruleId"].split("-")[0] in {"CLIN", "NUDGE", "INFO"})
                    for key in ("title", "detail", "recommendedAction"):
                        self.assertTrue(isinstance(a[key], str) and a[key])
                    self.assertIsNone(a["rationale"])
                    self.assertTrue(a["evidence"], "every alert carries evidence")
                    for ev in a["evidence"]:
                        self.assertIn(ev["kind"], kinds)
                        self.assertTrue(ev["display"])
                        if "value" in ev:  # backend types value as double?
                            self.assertIsInstance(ev["value"], (int, float))
                            self.assertNotIsInstance(ev["value"], bool)
                        self.assertNotIn(None, ev.values())

    def test_header_fields_for_syn_001(self):
        r = self.results["SYN-001"]
        self.assertEqual((r["patientName"], r["age"], r["sex"], r["memberSince"]),
                         ("David Park", 51, "male", "2024-05-01"))
        self.assertEqual(r["counts"], {"clinical": 1, "nudge": 2, "informational": 3})
        clin = r["alerts"][0]
        self.assertEqual(clin["title"], "Hematocrit 54.8% on testosterone therapy")
        self.assertEqual(clin["detail"], "Hematocrit 54.8% on 2026-09-26 (up from 52.1% and 49.5%) on "
                                         "testosterone cypionate 180 mg weekly.")

    def test_weight_percentages(self):
        titles = {pid: [a["title"] for a in r["alerts"] if a["ruleId"] == "INFO-WEIGHT-PROGRESS"]
                  for pid, r in self.results.items()}
        self.assertEqual(titles["SYN-001"], ["Down 14.0% body weight on GLP-1"])
        self.assertEqual(titles["SYN-004"], ["Down 13.6% body weight on GLP-1"])


class Cli(unittest.TestCase):
    def test_unknown_id_exits_2(self):
        proc = run_cli("--patient-id", "SYN-999", "--data-dir", PATIENTS)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(len(proc.stderr.strip().splitlines()), 1)
        self.assertIn("not found", proc.stderr)

    def test_path_traversal_id_exits_2(self):
        proc = run_cli("--patient-id", "../expected-alerts", "--data-dir", PATIENTS)
        self.assertEqual(proc.returncode, 2)

    def test_malformed_json_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w") as fh:
                fh.write('{"id": "SYN-X", "name": ')
            proc = run_cli("--patient", path)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not valid JSON", proc.stderr)

    def test_non_object_and_missing_fields_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, body in enumerate(['[1, 2]', '{"id": "X", "name": "Y", "sex": "male"}',
                                      '{"id": "X", "name": "Y", "sex": "male", "birthDate": "soon"}',
                                      '{"id": "X", "name": "Y", "sex": "male", "birthDate": "1980-01-01", "labs": {}}']):
                path = os.path.join(tmp, f"p{i}.json")
                with open(path, "w") as fh:
                    fh.write(body)
                with self.subTest(body=body):
                    proc = run_cli("--patient", path)
                    self.assertEqual(proc.returncode, 2)
                    self.assertTrue(proc.stderr.strip())

    def test_bad_as_of_exits_2(self):
        proc = run_cli("--patient-id", "SYN-001", "--data-dir", PATIENTS, "--as-of", "yesterday")
        self.assertEqual(proc.returncode, 2)

    def test_no_informational_drops_tier(self):
        proc = run_cli("--patient-id", "SYN-001", "--data-dir", PATIENTS, "--no-informational")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        r = json.loads(proc.stdout)
        self.assertNotIn("informational", {a["tier"] for a in r["alerts"]})
        self.assertEqual(r["counts"], {"clinical": 1, "nudge": 2, "informational": 0})
        self.assertEqual(rule_ids(r), {x for x in EXPECTED["patients"]["SYN-001"] if not x.startswith("INFO-")})

    def test_no_alerts_is_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quiet.json")
            with open(path, "w") as fh:
                json.dump({"id": "SYN-Q", "name": "Quiet", "birthDate": "1996-01-01", "sex": "female",
                           "synthetic": True}, fh)
            proc = run_cli("--patient", path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        r = json.loads(proc.stdout)
        self.assertEqual(r["alerts"], [])
        self.assertEqual(r["counts"], {"clinical": 0, "nudge": 0, "informational": 0})
        self.assertIsNone(r["memberSince"])

    def test_runs_when_copied_into_a_skill_folder(self):
        """CONTRACT §4: triage.py + rules/ + data/ copied side by side must work from any cwd."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = os.path.join(tmp, ".claude", "skills", "triage-patient")
            os.makedirs(skill)
            shutil.copy(TRIAGE, skill)
            shutil.copytree(os.path.join(ENGINE, "rules"), os.path.join(skill, "rules"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(PATIENTS, os.path.join(skill, "data"))
            proc = subprocess.run([sys.executable, ".claude/skills/triage-patient/triage.py", "--patient-id",
                                   "SYN-003", "--data-dir", ".claude/skills/triage-patient/data"],
                                  cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(rule_ids(json.loads(proc.stdout)), set(EXPECTED["patients"]["SYN-003"]))
            # --data-dir defaults to the skill's own data/ folder
            proc = subprocess.run([sys.executable, os.path.join(skill, "triage.py"), "--patient-id", "SYN-007"],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)


class Robustness(unittest.TestCase):
    def test_missing_optional_sections_do_not_crash(self):
        optional = ["membership", "conditions", "medications", "labs", "vitals", "screenings", "appointments",
                    "encounters", "mrn", "synthetic"]
        for pid in EXPECTED["patients"]:
            for key in optional:
                with self.subTest(patient=pid, dropped=key):
                    p = load(pid)
                    p.pop(key, None)
                    triage.triage(p, AS_OF)
                    p2 = load(pid)
                    p2[key] = None
                    triage.triage(p2, AS_OF)
            with self.subTest(patient=pid, dropped="all"):
                bare = {k: v for k, v in load(pid).items() if k in ("id", "name", "birthDate", "sex")}
                ids = rule_ids(triage.triage(bare, AS_OF))
                # With no history, only the age-based colorectal nudge can fire.
                self.assertTrue(ids <= {"NUDGE-COLORECTAL-SCREEN"}, ids)

    def test_bad_entries_are_skipped(self):
        p = load("SYN-001")
        p["labs"] += [{"code": "4544-3", "value": "high", "date": "2026-09-28"},
                      {"code": "4544-3", "value": 60.0},
                      {"code": "4544-3", "value": 60.0, "date": "not a date"},
                      "garbage"]
        self.assertEqual(rule_ids(triage.triage(p, AS_OF)), set(EXPECTED["patients"]["SYN-001"]))

    def test_dates_with_or_without_times(self):
        """Hardening: date-only, date-time, Z and offset timestamps give the same alerts."""
        for pid in EXPECTED["patients"]:
            p = load(pid)
            for lab in p.get("labs", []):
                lab["date"] = lab["date"] + "T08:15:00Z"
            for v in p.get("vitals", []):
                v["dateTime"] = v["dateTime"][:10]  # drop the time entirely
            for a in p.get("appointments", []):
                a["date"] = a["date"] + "T15:30:00-07:00"
            with self.subTest(patient=pid):
                self.assertEqual(rule_ids(triage.triage(p, AS_OF)), set(EXPECTED["patients"][pid]))

    def test_future_results_are_ignored(self):
        p = load("SYN-002")
        p["labs"].append({"code": "4544-3", "display": "Hematocrit", "value": 56.0, "unit": "%",
                          "date": "2026-10-15", "interpretation": "HH"})
        self.assertEqual(rule_ids(triage.triage(p, AS_OF)), set(EXPECTED["patients"]["SYN-002"]))

    def test_stopped_medication_does_not_count(self):
        p = load("SYN-001")
        for m in p["medications"]:
            if m["class"] == "androgen":
                m["status"] = "stopped"
        ids = rule_ids(triage.triage(p, AS_OF))
        self.assertFalse({"CLIN-TRT-ERYTHROCYTOSIS", "NUDGE-TRT-BP-ELEVATED"} & ids)


class Boundaries(unittest.TestCase):
    """Threshold edges from data/README.md."""

    def hct(self, values):
        p = load("SYN-002")
        dates = ["2026-03-18", "2026-06-17", "2026-09-27"]
        p["labs"] = [l for l in p["labs"] if l["code"] != "4544-3"] + [
            {"code": "4544-3", "display": "Hematocrit", "value": v, "unit": "%", "date": d, "interpretation": "N"}
            for v, d in zip(values, dates)]
        return rule_ids(triage.triage(p, AS_OF))

    def test_hematocrit_edges(self):
        self.assertIn("CLIN-TRT-ERYTHROCYTOSIS", self.hct([47, 49, 54.0]))
        self.assertNotIn("NUDGE-TRT-HCT-TREND", self.hct([47, 49, 54.0]))
        self.assertIn("NUDGE-TRT-HCT-TREND", self.hct([47, 49, 50.0]))
        self.assertNotIn("NUDGE-TRT-HCT-TREND", self.hct([47, 49, 49.9]))
        self.assertNotIn("NUDGE-TRT-HCT-TREND", self.hct([47, 51, 51]))  # not strictly increasing

    def test_bp_severe_replaces_bp_nudge(self):
        ids = rule_ids(triage.triage(load("SYN-005"), AS_OF))
        self.assertIn("CLIN-BP-SEVERE", ids)
        self.assertNotIn("NUDGE-TRT-BP-ELEVATED", ids)

    def test_diastolic_only_severe(self):
        p = load("SYN-006")
        p["vitals"] += [{"code": "8480-6", "value": 150, "unit": "mmHg", "dateTime": "2026-09-28T09:00:00"},
                        {"code": "8462-4", "value": 120, "unit": "mmHg", "dateTime": "2026-09-28T09:00:00"}]
        self.assertIn("CLIN-BP-SEVERE", rule_ids(triage.triage(p, AS_OF)))

    def test_aki_replaces_hydration_nudge(self):
        ids = rule_ids(triage.triage(load("SYN-003"), AS_OF))
        self.assertIn("CLIN-GLP1-AKI", ids)
        self.assertNotIn("NUDGE-GLP1-HYDRATION", ids)

    def test_aki_lookback_window(self):
        p = load("SYN-003")
        for lab in p["labs"]:
            if lab["code"] == "2160-0" and lab["value"] == 0.9:
                lab["date"] = "2026-03-01"  # 211 days before the latest draw
        ids = rule_ids(triage.triage(p, AS_OF))
        self.assertNotIn("CLIN-GLP1-AKI", ids)
        self.assertIn("NUDGE-GLP1-HYDRATION", ids)  # BUN 34 / creat 1.6 = 21.25

    def test_weight_under_ten_percent_is_quiet(self):
        self.assertNotIn("INFO-WEIGHT-PROGRESS", rule_ids(triage.triage(load("SYN-003"), AS_OF)))

    def test_new_result_window(self):
        p = load("SYN-006")
        for lab in p["labs"]:
            lab["date"] = "2026-09-25"  # 4 days before as-of
        self.assertNotIn("INFO-NEW-RESULT", rule_ids(triage.triage(p, AS_OF)))

    def test_colorectal_age_band(self):
        p = load("SYN-007")
        p["birthDate"] = "1981-09-30"  # 44 on as-of
        self.assertNotIn("NUDGE-COLORECTAL-SCREEN", rule_ids(triage.triage(p, AS_OF)))
        p["birthDate"] = "1981-09-29"  # 45 today
        self.assertIn("NUDGE-COLORECTAL-SCREEN", rule_ids(triage.triage(p, AS_OF)))

    def test_as_of_moves_the_window(self):
        p = copy.deepcopy(load("SYN-001"))
        ids = rule_ids(triage.triage(p, date(2026, 10, 20)))
        self.assertNotIn("INFO-UPCOMING-APPT", ids)  # appt was 2026-10-02
        self.assertNotIn("INFO-NEW-RESULT", ids)


if __name__ == "__main__":
    unittest.main()
