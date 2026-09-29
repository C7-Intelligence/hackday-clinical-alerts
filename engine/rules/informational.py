"""Informational-tier rules (priority 3): keep the member and care team in the loop."""

from __future__ import annotations

from datetime import date

from .common import (CLASS_GLP1, WEIGHT, active_meds, alert, days_between, ev_lab, ev_med, ev_vital, fmt,
                     iso, med_short, parse_day, parse_when, section, vitals, with_unit)

WEIGHT_PROGRESS_RATIO = 0.90   # latest ≤ 90% of pre-GLP-1 baseline
UPCOMING_APPT_DAYS = 14
NEW_RESULT_DAYS = 3


# --------------------------------------------------------------------------- INFO-WEIGHT-PROGRESS


def weight_progress(patient: dict, as_of: date) -> list:
    glp1 = active_meds(patient, CLASS_GLP1, as_of)
    if not glp1:
        return []
    start = parse_day(glp1[0].get("start"))
    weights = vitals(patient, WEIGHT, as_of)
    if start is None or not weights:
        return []
    baseline_candidates = [w for w in weights if w["_when"].date() <= start]
    if not baseline_candidates:
        return []
    baseline, latest = baseline_candidates[-1], weights[-1]
    if baseline["_value"] <= 0 or latest["_value"] > WEIGHT_PROGRESS_RATIO * baseline["_value"]:
        return []
    pct = (1 - latest["_value"] / baseline["_value"]) * 100
    unit = latest.get("unit", "")
    return [alert(
        patient, "INFO-WEIGHT-PROGRESS", "informational",
        f"Down {pct:.1f}% body weight on GLP-1",
        f"Weight {fmt(latest['_value'])} {unit} on {iso(latest['_when'])}, down from {fmt(baseline['_value'])} "
        f"{unit} on {iso(baseline['_when'])} before starting {med_short(glp1[0])} ({pct:.1f}% lost).",
        "Celebrate the progress with the member; check protein intake and strength training to preserve muscle.",
        [ev_vital(latest), ev_vital(baseline)] + [ev_med(m) for m in glp1],
    )]


# --------------------------------------------------------------------------- INFO-UPCOMING-APPT


def upcoming_appt(patient: dict, as_of: date) -> list:
    upcoming = []
    for appt in section(patient, "appointments"):
        when = parse_when(appt.get("date") or appt.get("dateTime"))
        if when is not None and 0 <= days_between(as_of, when.date()) <= UPCOMING_APPT_DAYS:
            upcoming.append((when, appt))
    if not upcoming:
        return []
    upcoming.sort(key=lambda x: x[0])
    when, appt = upcoming[0]
    days = days_between(as_of, when.date())
    in_days = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
    service = appt.get("service")
    reason = appt.get("reason") or "Appointment"
    more = f" ({len(upcoming) - 1} more in the next {UPCOMING_APPT_DAYS} days)" if len(upcoming) > 1 else ""
    return [alert(
        patient, "INFO-UPCOMING-APPT", "informational",
        f"Upcoming: {reason} {in_days}",
        f"{reason}" + (f" ({service})" if service else "") + f" on {iso(when)}, {in_days}{more}.",
        "Confirm the appointment and make sure any pending labs are drawn beforehand.",
        [{"kind": "appointment", "display": f"{reason}" + (f" — {service}" if service else ""), "date": iso(w)}
         for w, a in upcoming],
    )]


# --------------------------------------------------------------------------- INFO-NEW-RESULT


def new_result(patient: dict, as_of: date) -> list:
    recent = []
    for lab in section(patient, "labs"):
        if lab.get("interpretation") != "N":
            continue
        when = parse_when(lab.get("date") or lab.get("dateTime"))
        if when is None or not (0 <= days_between(when.date(), as_of) <= NEW_RESULT_DAYS):
            continue
        recent.append({**lab, "_when": when, "_value": lab.get("value")})
    if not recent:
        return []
    recent.sort(key=lambda e: (e["_when"], e.get("display") or ""))
    names = ", ".join(f"{r.get('display')} {with_unit(r['_value'], r.get('unit'))}" for r in recent)
    n = len(recent)
    return [alert(
        patient, "INFO-NEW-RESULT", "informational",
        f"{n} new normal result{'s' if n != 1 else ''}",
        f"New result{'s' if n != 1 else ''} in the last {NEW_RESULT_DAYS} days within normal range: {names}.",
        "Share the results with the member in the portal.",
        [ev_lab(r) for r in recent],
    )]
