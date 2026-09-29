#!/usr/bin/env bash
# One-shot setup for a fresh clone of StudyAgent-DBT.
# Creates the MCP server venv, installs deps, bootstraps the skeleton, and builds the
# topic index. Safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV="mcp-server/.venv"
PY="${PYTHON:-python3}"

# 1. Python version check (need >= 3.10 for `dict | None` syntax and match-free walrus use).
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "ERROR: Python >= 3.10 required. Found: $("$PY" --version 2>&1)" >&2
  echo "Override interpreter with:  PYTHON=/path/to/python3.11 ./scripts/setup.sh" >&2
  exit 1
fi

# 2. Create venv if missing.
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "==> Creating venv at $VENV"
  "$PY" -m venv "$VENV"
else
  echo "==> Reusing existing venv at $VENV"
fi

# 3. Install / upgrade dependencies.
echo "==> Installing dependencies from mcp-server/requirements.txt"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r mcp-server/requirements.txt

# 4. Create the directory skeleton and progress artifacts from exam_config.
echo "==> Bootstrapping repo skeleton"
"$VENV/bin/python" scripts/bootstrap_repo.py

# 5. Build topic + tag + concept indexes so knowledge/ lookups work out of the box.
echo "==> Building topic index"
"$VENV/bin/python" scripts/build_topic_index.py

# 6. Smoke test (best-effort; setup still succeeds if it reports failures).
if [[ -f mcp-server/tests/smoke.py ]]; then
  echo "==> Running smoke test"
  "$VENV/bin/python" mcp-server/tests/smoke.py || \
    echo "WARN: smoke test reported failures — inspect output above."
fi

cat <<'EOF'

Setup complete.

Next steps:
  1. Reload your editor window so the MCP client re-reads .vscode/mcp.json.
  2. Confirm the `study-agent` MCP server is listed and started.
  3. Seed the cache:   /author  (or call cache_fetch_batch on docs.getdbt.com pages)
  4. Write your first knowledge note, then author your first questions.

The question bank starts EMPTY on purpose. See question-bank/README.md.
EOF
