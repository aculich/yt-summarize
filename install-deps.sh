#!/usr/bin/env bash
# Install yt-dlp and llm for yt-summarize. Prefers uv, else pip.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v uv &>/dev/null; then
  echo "Using uv to install yt-dlp and llm..."
  if [[ ! -d .venv ]]; then
    uv venv .venv
  fi
  uv pip install yt-dlp llm
  echo "Done. Activate with: source $SCRIPT_DIR/.venv/bin/activate"
  echo "Or run: $SCRIPT_DIR/.venv/bin/yt-summarize <url>"
else
  echo "Using pip to install yt-dlp and llm..."
  if [[ -d .venv ]]; then
    .venv/bin/pip install -U yt-dlp llm
  else
    python3 -m pip install --user -U yt-dlp llm
  fi
  echo "Done."
fi
echo "Ensure OPENAI_API_KEY is set for llm (e.g. in .env or export)."
