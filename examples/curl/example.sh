#!/usr/bin/env bash
# Simple example using curl: call the API, and if the JWT is expired, get a new
# one and retry.
#
# Usage:
#   ACCESS_KEY=YOUR_KEY ./example.sh
#
# Requires curl and jq.
#
# Point it at a running Dataspot Facade API (defaults to http://localhost:8000).

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ACCESS_KEY="${ACCESS_KEY:?Set your ACCESS_KEY}"

get_token() {
    curl -sS -X POST "${BASE_URL}/v1/auth" \
        -H "Content-Type: application/json" \
        -d "{\"access_key\": \"${ACCESS_KEY}\"}" \
        | jq -r '.access_token'
}

run_query() {
    curl -sS -w '\n%{http_code}' -X POST "${BASE_URL}/v1/queries/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d '{"sql": "SELECT * FROM example_table LIMIT 5"}'
}

# 1. Exchange the access key for a facade JWT.
echo "== Obtaining JWT =="
token="$(get_token)"
echo "   (got fresh JWT)"

# 2. Execute a query, capturing the HTTP status code.
echo "== Executing query =="
result="$(run_query)"
http_code="${result##*$'\n'}"
body="${result%$'\n'*}"

# 3. If the JWT was rejected (401), refresh and retry once.
if [ "$http_code" = "401" ]; then
    echo "   JWT rejected, refreshing..."
    token="$(get_token)"
    result="$(run_query)"
    http_code="${result##*$'\n'}"
    body="${result%$'\n'*}"
fi

echo "== Response (HTTP ${http_code}) =="
printf '%s\n' "$body"
