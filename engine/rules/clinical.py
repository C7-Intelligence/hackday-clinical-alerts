"""Clinical-tier rules (priority 1): act today."""

from __future__ import annotations

from datetime import date

from .common import (CLASS_GLP1, CLASS_TRT, BUN, CREATININE, HEMATOCRIT, active_meds, alert, bp_readings,
                     days_between, ev_lab, ev_med, ev_vital, fmt, iso, labs, med_short, with_unit)

HCT_CLINICAL = 54.0          # %
BP_SEVERE_SYSTOLIC = 180     # mmHg
BP_SEVERE_DIASTOLIC = 120    # mmHg
AKI_RATIO = 1.5              # latest creatinine / previous creatinine
AKI_LOOKBACK_DAYS = 180


# --------------------------------------------------------------------------- CLIN-TRT-ERYTHROCYTOSIS


def trt_erythrocytosis(patient: dict, as_of: date) -> list:
    trt = active_meds(patient, CLASS_TRT, as_of)
    hct = labs(patient, HEMATOCRIT, as_of)
    if not trt or not hct:
        return []
    latest = hct[-1]
    if latest["_value"] < HCT_CLINICAL:
        return []
    history = list(reversed(hct))  # newest first
    prior = [f"{fmt(h['_value'])}%" for h in history[1:3]]
    trend = f" (up from {' and '.join(prior)})" if prior and all(
        h["_value"] < latest["_value"] for h in history[1:3]) else (f" (previously {' and '.join(prior)})" if prior else "")
    med = trt[0]
    return [alert(
        patient, "CLIN-TRT-ERYTHROCYTOSIS", "clinical",
        f"Hematocrit {fmt(latest['_value'])}% on testosterone therapy",
        f"Hematocrit {fmt(latest['_value'])}% on {iso(latest['_when'])}{trend} on {med_short(med)}.",
        "Care team review today: consider holding or reducing TRT dose and repeat CBC.",
        [ev_lab(h) for h in history] + [ev_med(m) for m in trt],
    )]


# --------------------------------------------------------------------------- CLIN-BP-SEVERE


def _is_severe(reading: dict) -> bool:
    s, d = reading["systolic"], reading["diastolic"]
    return (s is not None and s >= BP_SEVERE_SYSTOLIC) or (d is not None and d >= BP_SEVERE_DIASTOLIC)


def bp_severe_fires(patient: dict, as_of: date) -> bool:
    readings = bp_readings(patient, as_of)
    return bool(readings) and _is_severe(readings[-1])


def bp_severe(patient: dict, as_of: date) -> list:
    readings = bp_readings(patient, as_of)
    if not readings or not _is_severe(readings[-1]):
        return []
    r = readings[-1]
    s = fmt(r["systolic"]) if r["systolic"] is not None else "?"
    d = fmt(r["diastolic"]) if r["diastolic"] is not None else "?"
    on_trt = bool(active_meds(patient, CLASS_TRT, as_of))
    evidence = [ev_vital(e) for e in (r["sys_entry"], r["dia_entry"]) if e is not None]
    return [alert(
        patient, "CLIN-BP-SEVERE", "clinical",
        f"Blood pressure {s}/{d} mmHg" + (" on TRT" if on_trt else ""),
        f"Blood pressure {s}/{d} mmHg on {iso(r['when'])}, at or above the severe threshold "
        f"({BP_SEVERE_SYSTOLIC} systolic or {BP_SEVERE_DIASTOLIC} diastolic).",
        "Contact the member today: repeat the reading, screen for symptoms, and escalate to urgent care if "
        "headache, chest pain, vision change or confusion.",
        evidence,
    )]


# --------------------------------------------------------------------------- CLIN-GLP1-AKI


def _aki_pair(patient: dict, as_of: date):
    """Return (latest, previous) creatinine if the AKI rule fires, else None."""
    if not active_meds(patient, CLASS_GLP1, as_of):
        return None
    creat = labs(patient, CREATININE, as_of)
    if len(creat) < 2:
        return None
    latest = creat[-1]
    # The previous creatinine (the one drawn immediately before the latest, on an earlier day),
    # provided it was drawn within the 180 days before the latest.
    earlier = [c for c in creat[:-1] if c["_when"].date() < latest["_when"].date()]
    if not earlier:
        return None
    prev = earlier[-1]
    if days_between(prev["_when"].date(), latest["_when"].date()) > AKI_LOOKBACK_DAYS:
        return None
    if prev["_value"] <= 0 or latest["_value"] < AKI_RATIO * prev["_value"]:
        return None
    return latest, prev


def glp1_aki_fires(patient: dict, as_of: date) -> bool:
    return _aki_pair(patient, as_of) is not None


def glp1_aki(patient: dict, as_of: date) -> list:
    pair = _aki_pair(patient, as_of)
    if pair is None:
        return []
    latest, prev = pair
    ratio = latest["_value"] / prev["_value"]
    glp1 = active_meds(patient, CLASS_GLP1, as_of)
    bun = [b for b in labs(patient, BUN, as_of) if b["_when"].date() == latest["_when"].date()]
    bun_text = f", BUN {with_unit(bun[-1]['_value'], bun[-1].get('unit'))}" if bun else ""
    return [alert(
        patient, "CLIN-GLP1-AKI", "clinical",
        f"Creatinine {fmt(prev['_value'])} → {fmt(latest['_value'])} on GLP-1 therapy",
        f"Creatinine {fmt(latest['_value'])} mg/dL on {iso(latest['_when'])}, {ratio:.1f}× the previous "
        f"{fmt(prev['_value'])} mg/dL on {iso(prev['_when'])}{bun_text}, on {med_short(glp1[0])}.",
        "Care team review today: assess volume status, consider holding the GLP-1, and repeat renal panel "
        "within 48 hours.",
        [ev_lab(latest), ev_lab(prev)] + [ev_lab(b) for b in bun[-1:]] + [ev_med(m) for m in glp1],
    )]
