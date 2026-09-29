#!/usr/bin/env bash
# Deterministic half of the triage-patient skill: status beats, the engine run, the explain guard and the
# write-back. The agent does only the two non-deterministic steps between these calls: the Neo4j write
# (via MCP) and the plain-language rationale/summary (EXPLAIN.md).
#
#   bash .claude/skills/triage-patient/triage.sh start              # Loading patient → Running alert rules → engine
#   bash .claude/skills/triage-patient/triage.sh status "<subStatus>"
#   bash .claude/skills/triage-patient/triage.sh check-explain      # validate result.json vs result.engine.json
#   bash .claude/skills/triage-patient/triage.sh finish <written|skipped>
#   bash .claude/skills/triage-patient/triage.sh deprovision
#
# Working files (ticket workdir): result.engine.json (untouched engine output), result.json (what gets
# posted), graph-params.json (write-triage params), .explain-skipped (marker).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC_FILE="shared/alert-triage.json"
BASE="${DUPLO_BASE:-$DUPLO_HOST}"
auth=(-H "Authorization: Bearer $DUPLO_TOKEN" -H "Content-Type: application/json")

WORKSPACE_ID=$(jq -r '.ownerWorkspaceId' "$SPEC_FILE")
ID=$(jq -r '.id' "$SPEC_FILE")
RES="$BASE/v1/aiservicedesk/user/data/workspaces/$WORKSPACE_ID/environment/extensions/alerttriages/$ID"

post_status() {  # post_status <json>
  curl -fsS -X POST "$RES/status" "${auth[@]}" -d "$1" >/dev/null
}
beat() {
  post_status "$(jq -nc --arg ss "$1" '{status:"Processing", subStatus:$ss}')"
  echo "status: Processing / $1"
}
fail() {
  post_status "$(jq -nc --arg f "$1" '{status:"Failed", faults:[$f]}')"
  echo "FAILED: $1" >&2
  exit 1
}

cmd="${1:-}"
case "$cmd" in
  start)
    rm -f result.json result.engine.json graph-params.json .explain-skipped engine.err
    beat "Loading patient"
    PATIENT_ID=$(jq -r '.spec.patientId // ""' "$SPEC_FILE")
    [ -n "$PATIENT_ID" ] || fail "No member selected: the triage spec has no patientId."
    FLAGS=()
    [ "$(jq -r '.spec.includeInformational' "$SPEC_FILE")" = "false" ] && FLAGS+=(--no-informational)

    beat "Running alert rules"
    set +e
    python3 "$HERE/triage.py" --patient-id "$PATIENT_ID" --data-dir "$HERE/data" "${FLAGS[@]}" \
      > result.engine.json 2> engine.err
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
      # Keep the reason readable: drop the "triage: " prefix and any workdir path, keep the file name.
      reason=$(head -n1 engine.err | sed -e 's/^triage: //' -e 's#/[^ :]*/##g')
      fail "${reason:-Rules engine exited with code $rc}"
    fi
    cp result.engine.json result.json
    jq '{member: {id: .patientId, name: .patientName, age, sex, memberSince},
         asOf,
         alerts: [.alerts[] | {id, ruleId, tier, priority, title}]}' result.json > graph-params.json

    echo "engine: $(jq -c '{patientId, patientName, counts}' result.json)"
    echo "GRAPH_SCOPE_SELECTED=$([ "$(jq '.spec.scopeIds // [] | length' "$SPEC_FILE")" -gt 0 ] && echo yes || echo no)"
    echo "EXPLAIN=$(jq -r 'if .spec.explain == false then "false" else "true" end' "$SPEC_FILE")"
    ;;

  status)
    beat "${2:?usage: triage.sh status <subStatus>}"
    ;;

  check-explain)
    # EXPLAIN.md's guard: text filled in, and nothing but rationale/summary changed.
    ok=1
    jq -e '(.alerts | all(.rationale | type == "string" and length > 0)) and (.summary | type == "string" and length > 0)' \
      result.json >/dev/null 2>&1 || ok=0
    if [ "$ok" = 1 ] && ! diff <(jq -S '[.alerts[] | del(.rationale)], .counts, (del(.alerts, .summary))' result.engine.json) \
                             <(jq -S '[.alerts[] | del(.rationale)], .counts, (del(.alerts, .summary))' result.json) >/dev/null; then
      ok=0
    fi
    if [ "$ok" = 1 ]; then
      echo "EXPLAIN_CHECK=OK"
    else
      cp result.engine.json result.json
      touch .explain-skipped
      echo "EXPLAIN_CHECK=FAILED: restored the engine result (rationale/summary left null)"
    fi
    ;;

  finish)
    graph="${2:?usage: triage.sh finish <written|skipped>}"
    case "$graph" in written|skipped) ;; *) fail "triage.sh finish: graph status must be written or skipped";; esac
    beat "Saving results"
    jq --arg g "$graph" '.graphStatus = $g' result.json > result.post.json
    curl -fsS -X POST "$RES/results" "${auth[@]}" --data-binary @result.post.json >/dev/null \
      || fail "Could not save the triage results."
    if [ -f .explain-skipped ]; then
      post_status '{"status":"Complete","subStatus":"Triage complete (explanation skipped)","faults":["Explanation skipped"]}'
    else
      post_status '{"status":"Complete","subStatus":"Triage complete"}'
    fi
    echo "Done: $(jq -c '{patientId, counts, graphStatus}' result.post.json)"
    ;;

  deprovision)
    post_status '{"status":"DeProvisioned"}'
    echo "Done: DeProvisioned"
    ;;

  *)
    echo "usage: triage.sh start|status <sub>|check-explain|finish <written|skipped>|deprovision" >&2
    exit 2
    ;;
esac
