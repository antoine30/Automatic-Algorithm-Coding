"""
Serveur MCP "lean-verifier" : expose un projet Lean à un agent IA.

L'agent ne peut QUE :
  - lire l'exigence, la spécification figée et la solution courante (read_task)
  - écrire Solution.lean (write_solution)
  - essayer du code Lean jetable pour explorer (run_snippet)
  - demander une vérification complète (check)
Il n'a aucun outil pour modifier Check.lean : la spécification reste sous contrôle humain.

Lancement (normalement fait par le client) : python lean_verifier_server.py
Le répertoire courant doit être la racine du projet Lean.
Dépendance : pip install mcp
"""
import hashlib
import re
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path.cwd()
SPEC = ROOT / "Check.lean"
SOLUTION = ROOT / "Solution.lean"
TASK = ROOT / "task.md"
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = ("sorry", "admit", "axiom ", "native_decide", "unsafe")

# Empreinte de la spécification au démarrage : toute modification sera détectée
SPEC_HASH = hashlib.sha256(SPEC.read_bytes()).hexdigest()

mcp = FastMCP("lean-verifier")


def _run(cmd: list[str]) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


@mcp.tool()
def read_task() -> str:
    """Return the requirement (task.md), the frozen spec (Check.lean) and the current Solution.lean."""
    current = SOLUTION.read_text() if SOLUTION.exists() else "(none yet)"
    return (f"## Requirement\n{TASK.read_text()}\n\n"
            f"## Frozen spec Check.lean (read-only)\n{SPEC.read_text()}\n\n"
            f"## Current Solution.lean\n{current}")


@mcp.tool()
def write_solution(source: str) -> str:
    """Overwrite Solution.lean with the given full Lean source. Call `check` afterwards."""
    SOLUTION.write_text(source)
    return f"Solution.lean written ({len(source.splitlines())} lines)."


@mcp.tool()
def run_snippet(code: str) -> str:
    """Compile a throwaway Lean snippet without touching Solution.lean.
    Use it to see unsolved goals (shown in error messages), try tactics,
    or search lemmas with `#check`, `exact?`, `apply?`. The snippet may `import Solution`."""
    if "import Solution" in code:
        ok, out = _run(["lake", "build", "Solution"])
        if not ok:
            return "Solution.lean does not build, fix it first:\n" + out
    scratch = ROOT / "_Scratch.lean"
    scratch.write_text(code)
    try:
        _, out = _run(["lake", "env", "lean", scratch.name])
    finally:
        scratch.unlink(missing_ok=True)
    return out or "No errors, no messages."


@mcp.tool()
def check() -> str:
    """Full verification: build Solution.lean, prove the frozen spec, run anti-cheat checks.
    Returns 'PROVED' on success, otherwise 'FAILED' with the exact Lean errors."""
    if hashlib.sha256(SPEC.read_bytes()).hexdigest() != SPEC_HASH:
        return "FAILED: Check.lean has been modified. The spec is frozen."
    if not SOLUTION.exists():
        return "FAILED: Solution.lean does not exist yet."

    source = SOLUTION.read_text()
    found = [w.strip() for w in FORBIDDEN if w in source]
    if found:
        return f"FAILED: forbidden constructs in Solution.lean: {found}"

    ok, out = _run(["lake", "build", "Solution"])
    if not ok:
        return "FAILED: Solution.lean does not build:\n" + out
    ok, out = _run(["lake", "env", "lean", SPEC.name])
    if not ok:
        return "FAILED: the frozen spec does not hold:\n" + out

    for line in out.splitlines():
        if "depends on axioms" in line:
            extra = set(re.findall(r"[\w.]+", line.split(":", 1)[1])) - ALLOWED_AXIOMS
            if extra:
                return f"FAILED: non-standard axioms used: {sorted(extra)}"
    return "PROVED\n" + out


if __name__ == "__main__":
    mcp.run()  # transport stdio
