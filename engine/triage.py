#!/usr/bin/env python3
"""Clinical Alert Triage engine (J-Harmony x Cyber7Group hack day).

Rules decide, the graph connects, the LLM explains. This file is the "rules decide" part:
deterministic, pure Python 3.11 stdlib, no network and no LLM calls.

    python3 triage.py --patient data/synthetic-patients/SYN-001.json [--as-of 2026-09-29] [--no-informational]
    python3 triage.py --patient-id SYN-001 --data-dir data/synthetic-patients

Prints one TriageResult JSON object (CONTRACT §3) to stdout. Exit 0 on success (including no alerts),
exit 2 with a one-line reason on stderr if the patient file is missing or invalid.

SYNTHETIC DATA ONLY. Thresholds are illustrative for a demo, not clinical guidance.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

# Imports resolve relative to this file, so triage.py + rules/ can be copied into a skill folder as-is.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from rules import RULES, PatientDataError  # noqa: E402
from rules.common import patient_age, parse_day  # noqa: E402

ENGINE_VERSION = "0.1.0"
DEFAULT_AS_OF = "2026-09-29"
EXIT_BAD_INPUT = 2
_PATIENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_TIERS = ("clinical", "nudge", "informational")


class TriageError(Exception):
    """A problem with the input that should end in exit code 2."""


def default_data_dir() -> str:
    for candidate in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "data", "synthetic-patients")):
        if os.path.isdir(candidate):
            return os.path.normpath(candidate)
    return os.path.join(_HERE, "data")


def resolve_path(args) -> str:
    if args.patient:
        return args.patient
    if not _PATIENT_ID.match(args.patient_id):
        raise TriageError(f"invalid patient id '{args.patient_id}'")
    return os.path.join(args.data_dir or default_data_dir(), f"{args.patient_id}.json")


def load_patient(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            patient = json.load(fh)
    except FileNotFoundError:
        raise TriageError(f"patient file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise TriageError(f"patient file is not valid JSON: {path} (line {exc.lineno}: {exc.msg})") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise TriageError(f"cannot read patient file: {path} ({exc})") from None
    validate(patient)
    return patient


def validate(patient) -> None:
    if not isinstance(patient, dict):
        raise TriageError("patient record must be a JSON object")
    for key in ("id", "name", "birthDate", "sex"):
        if not isinstance(patient.get(key), str) or not patient[key].strip():
            raise TriageError(f"patient record is missing required field '{key}'")
    if parse_day(patient["birthDate"]) is None:
        raise TriageError(f"patient record has an invalid birthDate '{patient['birthDate']}'")
    for key in ("conditions", "medications", "labs", "vitals", "screenings", "appointments", "encounters"):
        if patient.get(key) is not None and not isinstance(patient[key], list):
            raise TriageError(f"patient record field '{key}' must be a list")


def triage(patient: dict, as_of: date, include_informational: bool = True) -> dict:
    """Run every rule and assemble the TriageResult (without rationale/summary)."""
    alerts = []
    for rule_id, rule in RULES.items():
        try:
            alerts.extend(rule(patient, as_of))
        except PatientDataError as exc:
            raise TriageError(f"patient record is invalid: {exc}") from None
    if not include_informational:
        alerts = [a for a in alerts if a["tier"] != "informational"]
    alerts.sort(key=lambda a: (a["priority"], a["ruleId"]))

    counts = {tier: 0 for tier in _TIERS}
    for a in alerts:
        counts[a["tier"]] += 1

    membership = patient.get("membership") if isinstance(patient.get("membership"), dict) else {}
    return {
        "patientId": patient["id"],
        "patientName": patient["name"],
        "age": patient_age(patient, as_of),
        "sex": patient["sex"],
        "memberSince": membership.get("since"),
        "asOf": as_of.isoformat(),
        "engineVersion": ENGINE_VERSION,
        "synthetic": bool(patient.get("synthetic", False)),
        "counts": counts,
        "alerts": alerts,
        "summary": None,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic clinical alert triage (synthetic data only).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--patient", help="path to a patient JSON file")
    src.add_argument("--patient-id", help="patient id, resolved as <data-dir>/<id>.json")
    p.add_argument("--data-dir", help="directory of patient files (used with --patient-id)")
    p.add_argument("--as-of", default=DEFAULT_AS_OF, help=f"evaluation date, YYYY-MM-DD (default {DEFAULT_AS_OF})")
    p.add_argument("--no-informational", action="store_true", help="drop informational-tier alerts")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)  # argparse exits 2 on bad usage
    try:
        try:
            as_of = date.fromisoformat(args.as_of)
        except ValueError:
            raise TriageError(f"invalid --as-of date '{args.as_of}' (expected YYYY-MM-DD)") from None
        patient = load_patient(resolve_path(args))
        result = triage(patient, as_of, include_informational=not args.no_informational)
    except TriageError as exc:
        print(f"triage: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
