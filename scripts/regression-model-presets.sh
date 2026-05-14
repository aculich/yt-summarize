#!/usr/bin/env bash
# Smoke-test llm with top cheap / deep model IDs (tiny transcript). Saves timestamped outputs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${ROOT}/regression-samples/${STAMP}"
TEMPLATE="${ROOT}/prompts/whole.yaml"
TRANSCRIPT=$'This is a tiny regression transcript.\nIt has two lines so the summarizer has minimal context.'

mkdir -p "${OUT}"

if command -v timeout >/dev/null 2>&1; then
  TIMEOUT=(timeout 120)
else
  TIMEOUT=()
fi

if ! command -v llm >/dev/null 2>&1; then
  echo "llm not found on PATH" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is unset in the shell; runs may still succeed if llm has stored credentials." >&2
fi

summary="${OUT}/summary.txt"
echo "UTC timestamp: ${STAMP}" >"${summary}"
echo "llm version: $(llm --version 2>&1)" >>"${summary}"
echo >>"${summary}"

run_one() {
  local label="$1"
  local model="$2"
  local safe
  safe="$(echo "${model}" | tr '/' '_')"
  local stdout="${OUT}/${label}-${safe}.out.txt"
  local stderr="${OUT}/${label}-${safe}.err.txt"
  echo "--- ${label}: ${model} ---" >>"${summary}"
  if printf '%s' "${TRANSCRIPT}" | "${TIMEOUT[@]}" llm -t "${TEMPLATE}" -m "${model}" >"${stdout}" 2>"${stderr}"; then
    echo "OK ${model}" >>"${summary}"
  else
    echo "FAIL ${model} (see ${stderr})" >>"${summary}"
  fi
  echo >>"${summary}"
}

# Top-3 cheap (IDs that typically appear in `llm models`; replace when OpenAI registers newer slugs)
CHEAP_MODELS=(gpt-5-nano gpt-4.1-nano gpt-5-mini)
for m in "${CHEAP_MODELS[@]}"; do
  run_one "cheap" "${m}"
done

# Top-3 deep (OpenAI IDs from typical llm catalogs; add gpt-5.5 when `llm models` lists it)
DEEP_MODELS=(gpt-5.2 gpt-5 gpt-5.1)
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  DEEP_MODELS+=(anthropic/claude-opus-4-5-20251101)
fi

for m in "${DEEP_MODELS[@]}"; do
  run_one "deep" "${m}"
done

echo "Wrote ${OUT}"
cat "${summary}"
