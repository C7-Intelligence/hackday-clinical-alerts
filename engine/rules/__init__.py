"""Alert rule registry.

One small, pure function per rule ID in data/README.md. Each takes ``(patient, as_of)`` and returns a
list of zero or more alerts in the CONTRACT §3 shape.
"""

from .clinical import bp_severe, glp1_aki, trt_erythrocytosis
from .common import PatientDataError
from .informational import new_result, upcoming_appt, weight_progress
from .nudge import a1c_overdue, colorectal_screen, glp1_hydration, trt_bp_elevated, trt_hct_trend, trt_psa_overdue

RULES = {
    # Clinical (priority 1)
    "CLIN-TRT-ERYTHROCYTOSIS": trt_erythrocytosis,
    "CLIN-BP-SEVERE": bp_severe,
    "CLIN-GLP1-AKI": glp1_aki,
    # Nudge (priority 2)
    "NUDGE-TRT-HCT-TREND": trt_hct_trend,
    "NUDGE-TRT-BP-ELEVATED": trt_bp_elevated,
    "NUDGE-TRT-PSA-OVERDUE": trt_psa_overdue,
    "NUDGE-GLP1-HYDRATION": glp1_hydration,
    "NUDGE-A1C-OVERDUE": a1c_overdue,
    "NUDGE-COLORECTAL-SCREEN": colorectal_screen,
    # Informational (priority 3)
    "INFO-WEIGHT-PROGRESS": weight_progress,
    "INFO-UPCOMING-APPT": upcoming_appt,
    "INFO-NEW-RESULT": new_result,
}

__all__ = ["RULES", "PatientDataError"]
