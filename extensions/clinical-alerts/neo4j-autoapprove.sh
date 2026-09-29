#!/usr/bin/env bash
# Pre-approve the Neo4j MCP tools on the `neo4j-mcp` MCP server, so a triage's graph write never waits for a
# human approval click (which would stall the run on stage).
#
# This is a STANDING setting on the MCP server record (AutoApprovedTools), read by the agent for every ticket
# whose scope uses that server (claude-code-agent: core/agent_setup/scopes/mcp.py). It is not the per-ticket
# "Command Execution Permissions" (requestApproval), which only covers shell commands.
#
# Usage (repo root, after registering the neo4j-mcp MCP server in the portal):
#   ./extensions/clinical-alerts/neo4j-autoapprove.sh
# Idempotent. Targets the platform in .env (DUPLO_TARGET), like the other scripts.
set -euo pipefail
cd "$(dirname "$0")/../.."
# shellcheck source=../../scripts/_target.sh
source scripts/_target.sh     # → BASE_URL + TOKEN (admin) from .env
BASE_URL="${BASE_URL%/}"
NAME="${1:-neo4j-mcp}"
TOOLS='["write_neo4j_cypher","read_neo4j_cypher","get_neo4j_schema"]'

python3 - "$BASE_URL" "$TOKEN" "$NAME" "$TOOLS" <<'PY'
import json, sys, urllib.request
base, tok, name, tools = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
url = f"{base}/v1/aiservicedesk/admin/data/mcpservers"

def call(method, u, body=None):
    req = urllib.request.Request(u, method=method, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    d = json.load(urllib.request.urlopen(req, timeout=20))
    d = d.get("data", d)
    return d.get("items", d) if isinstance(d, dict) and "items" in d else d

servers = [s for s in call("GET", url) if s.get("name") == name]
if not servers:
    sys.exit(f"neo4j-autoapprove: no MCP server named '{name}'. Register it first (DEPLOY.md §3.1).")
s = call("GET", f"{url}/{servers[0]['id']}")
if sorted(s.get("autoApprovedTools") or []) == sorted(tools):
    print(f"neo4j-autoapprove: '{name}' already auto-approves {tools}")
    sys.exit(0)
s["autoApprovedTools"] = tools
call("PUT", f"{url}/{s['id']}", s)
after = call("GET", f"{url}/{s['id']}").get("autoApprovedTools")
if sorted(after or []) != sorted(tools):
    sys.exit(f"neo4j-autoapprove: update didn't stick (autoApprovedTools={after})")
print(f"neo4j-autoapprove: '{name}' now auto-approves {after}")
PY
