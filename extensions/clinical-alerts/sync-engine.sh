#!/usr/bin/env bash
# Copy Stephen's engine + data into the triage-patient skill folder (CONTRACT §4), so the ticket workdir
# has everything the skill runs. Run before EVERY build:
#
#   ./extensions/clinical-alerts/sync-engine.sh && ./scripts/build-extension.sh extensions/clinical-alerts
#
# The copies are build inputs, not sources: they're gitignored here. engine/ and data/ stay the source of truth.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ in the shipped skill
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKILL="$ROOT/extensions/clinical-alerts/skills/triage-patient"

[ -f "$ROOT/engine/triage.py" ] || { echo "sync-engine: $ROOT/engine/triage.py not found (merge stephen/engine?)" >&2; exit 1; }

rm -rf "$SKILL/triage.py" "$SKILL/rules" "$SKILL/data" "$SKILL/write-triage.cypher"
cp "$ROOT/engine/triage.py" "$SKILL/triage.py"
cp -r "$ROOT/engine/rules" "$SKILL/rules"
find "$SKILL/rules" -name '__pycache__' -type d -prune -exec rm -rf {} +
mkdir -p "$SKILL/data"
cp "$ROOT"/data/synthetic-patients/SYN-*.json "$SKILL/data/"

# The graph write statement, extracted by name from Stephen's queries.cypher (the same text seed.py runs).
awk '/^\/\/ @name write-triage$/{on=1; next} on && /^\/\/ @name /{exit} on{print} on && /;[[:space:]]*$/{exit}' \
  "$ROOT/engine/graph/queries.cypher" | sed -e 's/;[[:space:]]*$//' > "$SKILL/write-triage.cypher"
grep -q 'MERGE (m:Member' "$SKILL/write-triage.cypher" \
  || { echo "sync-engine: couldn't extract '@name write-triage' from engine/graph/queries.cypher" >&2; exit 1; }

# Smoke test the copied layout: the engine must run from the skill folder with its default ./data.
python3 "$SKILL/triage.py" --patient-id SYN-001 --data-dir "$SKILL/data" >/dev/null \
  || { echo "sync-engine: copied engine failed its SYN-001 smoke run" >&2; exit 1; }

echo "sync-engine: engine $(python3 "$SKILL/triage.py" --patient-id SYN-001 --data-dir "$SKILL/data" | python3 -c 'import sys,json;print(json.load(sys.stdin)["engineVersion"])'), $(ls "$SKILL/data" | wc -l) members, write-triage.cypher ($(wc -l < "$SKILL/write-triage.cypher") lines) → $SKILL"
