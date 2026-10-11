# Lean Formal-Proof MCP Agent

An AI agent that writes and evolves **machine-checked Lean 4 proofs**. The agent
can only edit `Solution.lean`; the specification `Check.lean` is frozen and under
human control. A proof is accepted only if Lean itself verifies it — the agent is
never trusted on its word.

## Components

| File | Role |
|------|------|
| `lean_verifier_server.py` | MCP server exposing a Lean project: `read_task`, `write_solution`, `run_snippet`, `check`. No tool can modify `Check.lean`. |
| `lean_mcp_agent.py` | Agent loop: connects to the MCP server, lets Claude call the tools until the frozen spec is proved, then **re-verifies itself** and commits `Solution.lean`. |
| `run.sh` | Convenience launcher (uses the local venv). |
| `requirements.txt` | Pinned Python deps (`mcp` kept < 2, see note below). |

## Install (already done in this folder)

A Python 3.11 virtualenv lives in `.venv` with the dependencies installed:

```bash
# recreate from scratch if needed (needs Python >= 3.10):
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> **mcp version note.** The code targets the MCP **v1** API
> (`from mcp.server.fastmcp import FastMCP`). `mcp` 2.x renamed `FastMCP` to
> `MCPServer` and would break it, so `requirements.txt` pins `mcp>=1,<2`.
>
> **Model id.** The original snippet referenced `claude-sonnet-5-5`, which is not
> a valid model id; it was corrected to `claude-sonnet-5` in `lean_mcp_agent.py`.
> Change `MODEL` there if you want a different model.

## Prerequisites to actually run

1. **ANTHROPIC_API_KEY** in the environment.
2. A **Lean 4 toolchain** (`lake` on PATH). **Installed** via elan on this
   machine (Lean `v4.34.1`, under `~/.elan`). `run.sh` adds `~/.elan/bin` to PATH.
   To reinstall elsewhere:
   ```bash
   curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
   ```
3. A **Lean project** that is a git repo and contains `task.md`, `Check.lean`
   (frozen spec), a `lakefile`, and the `Solution.lean` convention.

## Bundled example project

`example_project/` is a ready-to-solve task (its own git repo, Lean pinned to
v4.34.1). It asks the agent to define `Solution.double` and prove three theorems
so that `Check.lean` type-checks. `Solution.lean` is intentionally absent — the
agent must write it. An answer key is in `example_project/reference_solution.txt`.

Verified end-to-end: with the reference solution in place, `lake build Solution`
and `lake env lean Check.lean` succeed and the verifier's `check()` returns
`PROVED`.

## Usage

```bash
export ANTHROPIC_API_KEY=sk-ant-...
./run.sh                       # runs against the bundled example_project
./run.sh /path/to/lean_project # or any other Lean project
# equivalently:
PATH="$HOME/.elan/bin:$PATH" .venv/bin/python lean_mcp_agent.py example_project
```

The agent runs up to `MAX_STEPS` (40) tool-calling turns. On success it commits
`Solution.lean` ("Agent: spec proved"); on failure it restores the last proved
version via `git checkout` and prints the Lean errors for human review.

## Safety model (why this is trustworthy)

- The spec is **frozen**: `check` recomputes the SHA-256 of `Check.lean` and
  refuses if it changed since startup.
- **Anti-cheat**: `sorry`, `admit`, `axiom`, `native_decide`, `unsafe` are
  rejected, and any proof depending on axioms outside
  `{propext, Classical.choice, Quot.sound}` fails.
- The final verdict is produced by the server's `check`, not by the agent.
