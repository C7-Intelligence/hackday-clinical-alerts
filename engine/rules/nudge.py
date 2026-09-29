"""Nudge-tier rules (priority 2): get ahead of it."""

from __future__ import annotations

from datetime import date

from .clinical import HCT_CLINICAL, bp_severe_fires, glp1_aki_fires
from .common import (BUN, CLASS_GLP1, CLASS_TRT, CREATININE, HBA1C, HEMATOCRIT, PSA, active_meds, alert,
                     bp_readings, days_between, ev_lab, ev_med, ev_vital, fmt, iso, labs, med_short,
                     parse_day, patient_age, section, with_unit, years_before)

HCT_NUDGE = 50.0              # % (and below HCT_CLINICAL)
BP_ELEVATED_SYSTOLIC = 140    # mmHg
BP_ELEVATED_DIASTOLIC = 90    # mmHg
PSA_MIN_AGE = 40
PSA_INTERVAL_DAYS = 365
BUN_MAX = 20                  # mg/dL
BUN_CREAT_RATIO_MAX = 20
A1C_INTERVAL_DAYS = 180
COLORECTAL_AGE = (45, 75)
COLONOSCOPY_YEARS = 10
FIT_INTERVAL_DAYS = 365


def _within(d: date | None, as_of: date, days: int) -> bool:
    return d is not None and 0 <= days_between(d, as_of) <= days


# --------------------------------------------------------------------------- NUDGE-TRT-HCT-TREND


def trt_hct_trend(patient: dict, as_of: date) -> list:
    trt = active_meds(patient, CLASS_TRT, as_of)
    hct = labs(patient, HEMATOCRIT, as_of)
    if not trt or len(hct) < 3:
        return []
    last3 = hct[-3:]
    latest = last3[-1]["_value"]
    if not (HCT_NUDGE <= latest < HCT_CLINICAL):
        return []
    if not (last3[0]["_value"] < last3[1]["_value"] < last3[2]["_value"]):
        return []
    series = " → ".join(f"{fmt(h['_value'])}%" for h in last3)
    return [alert(
        patient, "NUDGE-TRT-HCT-TREND", "nudge",
        f"Hematocrit trending up on TRT ({fmt(latest)}%)",
        f"Hematocrit has risen at each of the last 3 draws ({series}, latest {iso(last3[-1]['_when'])}) on "
        f"{med_short(trt[0])}. Not yet at the {fmt(HCT_CLINICAL)}% clinical threshold.",
        "Reach out this week: encourage hydration, review TRT dose and injection interval, repeat CBC in 6–8 weeks.",
        [ev_lab(h) for h in reversed(last3)] + [ev_med(m) for m in trt],
    )]


# --------------------------------------------------------------------------- NUDGE-TRT-BP-ELEVATED


def trt_bp_elevated(patient: dict, as_of: date) -> list:
    trt = active_meds(patient, CLASS_TRT, as_of)
    readings = bp_readings(patient, as_of)
    if not trt or len(readings) < 2 or bp_severe_fires(patient, as_of):
        return []
    last2 = readings[-2:]
    sys_high = all(r["systolic"] is not None and r["systolic"] >= BP_ELEVATED_SYSTOLIC for r in last2)
    dia_high = all(r["diastolic"] is not None and r["diastolic"] >= BP_ELEVATED_DIASTOLIC for r in last2)
    if not (sys_high or dia_high):
        return []

    def show(r):
        s = fmt(r["systolic"]) if r["systolic"] is not None else "?"
        d = fmt(r["diastolic"]) if r["diastolic"] is not None else "?"
        return f"{s}/{d} on {iso(r['when'])}"

    evidence = []
    for r in reversed(last2):
        evidence += [ev_vital(e) for e in (r["sys_entry"], r["dia_entry"]) if e is not None]
    return [alert(
        patient, "NUDGE-TRT-BP-ELEVATED", "nudge",
        f"Blood pressure elevated on TRT ({fmt(last2[-1]['systolic'])}/{fmt(last2[-1]['diastolic'])} mmHg)",
        f"The 2 most recent blood pressure readings are elevated ({show(last2[-1])}; {show(last2[0])}) on "
        f"{med_short(trt[0])}.",
        "Schedule a BP recheck within 2 weeks with home readings; review TRT dose, sodium, alcohol and sleep.",
        evidence + [ev_med(m) for m in trt],
    )]


# --------------------------------------------------------------------------- NUDGE-TRT-PSA-OVERDUE


def trt_psa_overdue(patient: dict, as_of: date) -> list:
    trt = active_meds(patient, CLASS_TRT, as_of)
    if not trt or patient.get("sex") != "male":
        return []
    age = patient_age(patient, as_of)
    if age < PSA_MIN_AGE:
        return []
    psa = labs(patient, PSA, as_of)
    if any(_within(p["_when"].date(), as_of, PSA_INTERVAL_DAYS) for p in psa):
        return []
    if psa:
        last = psa[-1]
        detail = (f"Last PSA was {with_unit(last['_value'], last.get('unit'))} on {iso(last['_when'])}, "
                  f"{days_between(last['_when'].date(), as_of)} days ago")
    else:
        detail = "No PSA on record"
    return [alert(
        patient, "NUDGE-TRT-PSA-OVERDUE", "nudge",
        "PSA overdue on TRT",
        f"{detail}. Men {PSA_MIN_AGE}+ on {med_short(trt[0])} need a PSA at least every "
        f"{PSA_INTERVAL_DAYS} days.",
        "Add PSA to the next lab draw.",
        [ev_lab(p) for p in psa[-1:]] + [ev_med(m) for m in trt]
        + [{"kind": "demographic", "display": f"Male, age {age}", "date": None}],
    )]


# --------------------------------------------------------------------------- NUDGE-GLP1-HYDRATION


def glp1_hydration(patient: dict, as_of: date) -> list:
    glp1 = active_meds(patient, CLASS_GLP1, as_of)
    bun = labs(patient, BUN, as_of)
    if not glp1 or not bun or glp1_aki_fires(patient, as_of):
        return []
    latest = bun[-1]
    if latest["_value"] <= BUN_MAX:
        return []
    same_draw = [c for c in labs(patient, CREATININE, as_of)
                 if c["_when"].date() == latest["_when"].date() and c["_value"] > 0]
    if not same_draw:
        return []
    creat = same_draw[-1]
    ratio = latest["_value"] / creat["_value"]
    if ratio <= BUN_CREAT_RATIO_MAX:
        return []
    return [alert(
        patient, "NUDGE-GLP1-HYDRATION", "nudge",
        f"BUN {fmt(latest['_value'])} on GLP-1: hydrate",
        f"BUN {fmt(latest['_value'])} mg/dL with creatinine {fmt(creat['_value'])} mg/dL on "
        f"{iso(latest['_when'])} (BUN/creatinine ratio {ratio:.1f}, above {BUN_CREAT_RATIO_MAX}) on "
        f"{med_short(glp1[0])}. This pattern suggests dehydration.",
        "Reach out this week: coach on fluids and managing nausea, and repeat BUN/creatinine in 2–4 weeks.",
        [ev_lab(latest), ev_lab(creat)] + [ev_med(m) for m in glp1],
    )]


# --------------------------------------------------------------------------- NUDGE-A1C-OVERDUE


def a1c_overdue(patient: dict, as_of: date) -> list:
    diabetes = [c for c in section(patient, "conditions")
                if c.get("status", "active") == "active" and "diabetes" in (c.get("tags") or [])]
    if not diabetes:
        return []
    a1c = labs(patient, HBA1C, as_of)
    if any(_within(a["_when"].date(), as_of, A1C_INTERVAL_DAYS) for a in a1c):
        return []
    if a1c:
        last = a1c[-1]
        detail = (f"Last HbA1c was {with_unit(last['_value'], last.get('unit'))} on {iso(last['_when'])}, "
                  f"{days_between(last['_when'].date(), as_of)} days ago")
    else:
        detail = "No HbA1c on record"
    cond = diabetes[0]
    return [alert(
        patient, "NUDGE-A1C-OVERDUE", "nudge",
        "HbA1c overdue",
        f"{detail}. Members with {cond.get('display', 'diabetes')} need an HbA1c at least every "
        f"{A1C_INTERVAL_DAYS} days.",
        "Add HbA1c to the next lab draw.",
        [ev_lab(a) for a in a1c[-1:]]
        + [{"kind": "condition", "code": c.get("code"), "display": c.get("display"), "date": c.get("onset")}
           for c in diabetes],
    )]


# --------------------------------------------------------------------------- NUDGE-COLORECTAL-SCREEN


def colorectal_screen(patient: dict, as_of: date) -> list:
    age = patient_age(patient, as_of)
    lo, hi = COLORECTAL_AGE
    if not (lo <= age <= hi):
        return []
    screens = []
    for s in section(patient, "screenings"):
        d = parse_day(s.get("date"))
        if d is not None and d <= as_of:
            screens.append((d, s))
    screens.sort(key=lambda x: x[0])
    ten_years_ago = years_before(as_of, COLONOSCOPY_YEARS)
    if any(s.get("type") == "colonoscopy" and d >= ten_years_ago for d, s in screens):
        return []
    if any(s.get("type") == "fit" and _within(d, as_of, FIT_INTERVAL_DAYS) for d, s in screens):
        return []
    colorectal = [(d, s) for d, s in screens if s.get("type") in ("colonoscopy", "fit")]
    if colorectal:
        d, s = colorectal[-1]
        detail = f"Last colorectal screening was a {s.get('type')} on {iso(d)}"
    else:
        detail = "No colorectal screening on record"
    return [alert(
        patient, "NUDGE-COLORECTAL-SCREEN", "nudge",
        "Colorectal cancer screening due",
        f"{detail}. Members aged {lo}–{hi} need a colonoscopy every {COLONOSCOPY_YEARS} years or a FIT every year.",
        "Offer a FIT kit by mail or a colonoscopy referral.",
        [{"kind": "screening", "display": f"{s.get('type')}" + (f" ({s.get('result')})" if s.get("result") else ""),
          "date": iso(d)}
         for d, s in colorectal[-1:]]
        + [{"kind": "demographic", "display": f"Age {age}", "date": None}],
    )]
