"""Shared helpers for the alert rules.

Everything here is pure: no I/O, no clock, no network. Every date comparison is relative to the
``as_of`` date passed in by the caller, which keeps the engine deterministic.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

# LOINC codes (see data/README.md)
HEMATOCRIT = "4544-3"
TESTOSTERONE = "2986-8"
PSA = "2857-1"
BUN = "3094-0"
CREATININE = "2160-0"
POTASSIUM = "2823-3"
HBA1C = "4548-4"
SYSTOLIC = "8480-6"
DIASTOLIC = "8462-4"
WEIGHT = "29463-7"

CLASS_TRT = "androgen"
CLASS_GLP1 = "GLP-1 receptor agonist"

PRIORITY = {"clinical": 1, "nudge": 2, "informational": 3}


class PatientDataError(ValueError):
    """The patient record is malformed in a way the engine can't safely evaluate."""


# --------------------------------------------------------------------------- dates


def parse_when(value) -> datetime | None:
    """Parse a date or date-time string into a naive ``datetime``.

    Accepts ``2026-09-26``, ``2026-09-26T09:05:00``, ``2026-09-26 09:05``, and ISO strings with ``Z``
    or a UTC offset (converted to UTC, then made naive). Returns ``None`` for missing/unparseable input
    so a single bad entry is skipped rather than crashing the triage.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
        except ValueError:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def parse_day(value) -> date | None:
    dt = parse_when(value)
    return dt.date() if dt else None


def days_between(earlier: date, later: date) -> int:
    return (later - earlier).days


def years_before(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 Feb -> 28 Feb
        return d.replace(year=d.year - years, day=28)


def age_on(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def iso(d: date | datetime) -> str:
    return (d.date() if isinstance(d, datetime) else d).isoformat()


# --------------------------------------------------------------------------- record access


def section(patient: dict, key: str) -> list:
    """Return a list section, treating a missing or null section as empty."""
    value = patient.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise PatientDataError(f"'{key}' must be a list")
    return [item for item in value if isinstance(item, dict)]


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def observations(patient: dict, key: str, code: str, as_of: date) -> list[dict]:
    """Labs or vitals with a LOINC ``code``, dated on/before ``as_of``, oldest first.

    Each returned item is the original entry plus ``_when`` (datetime) and ``_value`` (number).
    Entries without a usable date or numeric value are skipped.
    """
    out = []
    for entry in section(patient, key):
        if entry.get("code") != code:
            continue
        when = parse_when(entry.get("dateTime") or entry.get("date"))
        value = _number(entry.get("value"))
        if when is None or value is None or when.date() > as_of:
            continue
        out.append({**entry, "_when": when, "_value": value})
    out.sort(key=lambda e: e["_when"])
    return out


def labs(patient: dict, code: str, as_of: date) -> list[dict]:
    return observations(patient, "labs", code, as_of)


def vitals(patient: dict, code: str, as_of: date) -> list[dict]:
    return observations(patient, "vitals", code, as_of)


def bp_readings(patient: dict, as_of: date) -> list[dict]:
    """Blood-pressure readings, pairing systolic and diastolic taken at the same date-time.

    Returns oldest first: ``{"when", "systolic", "diastolic", "sys_entry", "dia_entry"}``. Either
    side may be ``None`` if only one half was recorded.
    """
    readings: dict[datetime, dict] = {}
    for entry in vitals(patient, SYSTOLIC, as_of):
        r = readings.setdefault(entry["_when"], {"when": entry["_when"], "systolic": None, "diastolic": None,
                                                 "sys_entry": None, "dia_entry": None})
        r["systolic"], r["sys_entry"] = entry["_value"], entry
    for entry in vitals(patient, DIASTOLIC, as_of):
        r = readings.setdefault(entry["_when"], {"when": entry["_when"], "systolic": None, "diastolic": None,
                                                 "sys_entry": None, "dia_entry": None})
        r["diastolic"], r["dia_entry"] = entry["_value"], entry
    return [readings[k] for k in sorted(readings)]


def active_meds(patient: dict, med_class: str, as_of: date) -> list[dict]:
    """Active medications of a class that had started on/before ``as_of`` (earliest start first)."""
    out = []
    for med in section(patient, "medications"):
        if med.get("class") != med_class or med.get("status", "active") != "active":
            continue
        start = parse_day(med.get("start"))
        if start is not None and start > as_of:
            continue
        out.append(med)
    out.sort(key=lambda m: parse_day(m.get("start")) or date.min)
    return out


def patient_age(patient: dict, as_of: date) -> int:
    birth = parse_day(patient.get("birthDate"))
    if birth is None:
        raise PatientDataError("'birthDate' is missing or not a date")
    return age_on(birth, as_of)


def fmt(value) -> str:
    """Format a number without a pointless trailing .0 (54.8 -> '54.8', 26.0 -> '26')."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def with_unit(value, unit) -> str:
    """'54.8%' for percentages, '26 mg/dL' otherwise."""
    if not unit:
        return fmt(value)
    return f"{fmt(value)}{unit}" if unit == "%" else f"{fmt(value)} {unit}"


def med_label(med: dict) -> str:
    parts = [med.get("name"), med.get("dose"), med.get("route"), med.get("frequency")]
    return " ".join(str(p) for p in parts if p)


def med_short(med: dict) -> str:
    """Inline form for prose: 'testosterone cypionate 180 mg weekly' (only the first letter lowered)."""
    parts = [med.get("name"), med.get("dose"), med.get("frequency")]
    text = " ".join(str(p) for p in parts if p)
    return text[:1].lower() + text[1:]


# --------------------------------------------------------------------------- evidence


def ev_obs(entry: dict, kind: str) -> dict:
    return {
        "kind": kind,
        "code": entry.get("code"),
        "display": entry.get("display"),
        "value": entry["_value"],
        "unit": entry.get("unit"),
        "date": iso(entry["_when"]),
    }


def ev_lab(entry: dict) -> dict:
    return ev_obs(entry, "lab")


def ev_vital(entry: dict) -> dict:
    return ev_obs(entry, "vital")


def ev_med(med: dict) -> dict:
    start = parse_day(med.get("start"))
    return {"kind": "medication", "display": med_label(med), "date": iso(start) if start else None}


def alert(patient: dict, rule_id: str, tier: str, title: str, detail: str, action: str, evidence: list) -> dict:
    return {
        "id": f"{patient.get('id')}:{rule_id}",
        "ruleId": rule_id,
        "tier": tier,
        "priority": PRIORITY[tier],
        "title": title,
        "detail": detail,
        "recommendedAction": action,
        "evidence": evidence,
        "rationale": None,
    }
