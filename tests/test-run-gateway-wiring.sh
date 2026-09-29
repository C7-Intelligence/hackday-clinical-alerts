#!/usr/bin/env bash
# Checks that run.sh / docker-compose.yml / .env.example actually wire the gateway provider in.
# Static checks only — nothing here starts the stack or touches .env.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PASS=0; FAIL=0
t()   { printf '  %s … ' "$1"; }
ok()  { echo "ok"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "run.sh gateway wiring:"

t "--help documents --model gateway and the --gateway-* flags"
H="$(./run.sh --help 2>&1)"
if grep -q -- '--model gateway' <<<"$H" && grep -q -- '--gateway-url' <<<"$H" && grep -q -- '--gateway-token' <<<"$H" && grep -q -- '--gateway-model' <<<"$H"; then ok; else bad "help text"; fi

t "every --gateway-* flag is parsed (not 'Unknown flag')"
MISS=""; for f in --gateway-url --gateway-token --gateway-model --gateway-disable-betas --gateway-max-context-tokens --gateway-compact-window; do
  grep -qE "^\s+$f\)" run.sh || MISS="$MISS $f"
done; if [ -z "$MISS" ]; then ok; else bad "not parsed:$MISS"; fi

t "menu maps 3 → gateway and 4 → bedrock-instance-role"
if grep -qE '3\) MODEL=gateway;; 4\) MODEL=bedrock-instance-role' run.sh; then ok; else bad "numeric mapping"; fi

t "run.sh sources scripts/_provider_gateway.sh and calls provider_gateway_configure"
if grep -q '_provider_gateway.sh' run.sh && grep -q 'provider_gateway_configure' run.sh; then ok; else bad "not wired"; fi

t "--reset clears the gateway keys"
if grep -q 'GATEWAY_KEYS' run.sh; then ok; else bad "GATEWAY_KEYS not in reset list"; fi

t "docker-compose passes the gateway vars to the agent"
MISS=""; for v in ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS CLAUDE_CODE_MAX_CONTEXT_TOKENS CLAUDE_CODE_AUTO_COMPACT_WINDOW; do
  grep -qE "^\s+- $v=\\$\{$v:-\}" docker-compose.yml || MISS="$MISS $v"
done; if [ -z "$MISS" ]; then ok; else bad "missing from docker-compose.yml:$MISS"; fi

t ".env.example documents gateway and has blank keys"
if grep -q '^ANTHROPIC_BASE_URL=$' .env.example && grep -q '^ANTHROPIC_AUTH_TOKEN=$' .env.example && grep -qi 'gateway' .env.example; then ok; else bad ".env.example"; fi

t "register-llm.sh label for a gateway model id"
if grep -q 'LLM Gateway' scripts/register-llm.sh; then ok; else bad "no gateway label"; fi

t "bash -n on run.sh and helper"
if bash -n run.sh && bash -n scripts/_provider_gateway.sh; then ok; else bad "syntax"; fi

echo; echo "$PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
