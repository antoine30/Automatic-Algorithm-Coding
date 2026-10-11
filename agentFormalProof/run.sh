#!/usr/bin/env bash
# Launch the Lean MCP agent against a Lean project.
#
#   ./run.sh /path/to/lean_project
#
# The project must contain task.md, Check.lean (frozen spec), be a git repo,
# and have a working Lean toolchain (`lake` on PATH).
# ANTHROPIC_API_KEY must be set in the environment.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="${1:-$HERE/example_project}"   # defaults to the bundled example project

# Make the Lean toolchain (lake/lean) visible to the agent and its MCP server.
export PATH="$HOME/.elan/bin:$PATH"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "error: ANTHROPIC_API_KEY is not set." >&2
    exit 1
fi
if ! command -v lake >/dev/null 2>&1; then
    echo "warning: 'lake' (Lean toolchain) not found on PATH — check/run_snippet will fail." >&2
fi

exec "$HERE/.venv/bin/python" "$HERE/lean_mcp_agent.py" "$PROJECT"
