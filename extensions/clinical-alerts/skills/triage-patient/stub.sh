#!/usr/bin/env bash
# STUB triage (milestone 1): walks the CONTRACT §5 sub-steps, then posts the hard-coded SYN-001 sample
# TriageResult (sample-result.json) and Complete. Replaced by the real engine → graph → explain flow later.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC_FILE="shared/alert-triage.json"

BASE="${DUPLO_BASE:-$DUPLO_HOST}"
auth=(-H "Authorization: Bearer $DUPLO_TOKEN" -H "Content-Type: application/json")

WORKSPACE_ID=$(jq -r '.ownerWorkspaceId' "$SPEC_FILE")
ID=$(jq -r '.id' "$SPEC_FILE")
PATIENT_ID=$(jq -r '.spec.patientId // ""' "$SPEC_FILE")
RES="$BASE/v1/aiservicedesk/user/data/workspaces/$WORKSPACE_ID/environment/extensions/alerttriages/$ID"

status() {  # status <Status> <subStatus>
  curl -fsS -X POST "$RES/status" "${auth[@]}" \
    -d "$(jq -nc --arg s "$1" --arg ss "$2" '{status:$s, subStatus:$ss}')" >/dev/null
}
fail() {
  curl -fsS -X POST "$RES/status" "${auth[@]}" \
    -d "$(jq -nc --arg f "$1" '{status:"Failed", faults:[$f]}')" >/dev/null
  echo "Failed: $1" >&2
  exit 1
}

[ -n "$PATIENT_ID" ] || fail "No patientId in the triage spec."

for step in "Loading patient" "Running alert rules" "Updating knowledge graph" "Writing clinical rationale"; do
  status Processing "$step"
  sleep 1.5
done

status Processing "Saving results"
curl -fsS -X POST "$RES/results" "${auth[@]}" --data-binary @"$HERE/sample-result.json" >/dev/null \
  || fail "Could not save results."

status Complete "Triage complete (stub result)"
echo "Done: stub TriageResult posted for $ID (requested $PATIENT_ID)"
