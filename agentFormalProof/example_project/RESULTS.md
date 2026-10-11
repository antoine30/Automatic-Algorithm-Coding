# Results — agent runs on this example project

Machine-checked outcomes produced by `lean_mcp_agent.py` driving the
`lean-verifier` MCP server, on Lean v4.34.1 (core only, no Mathlib).

## Run 1 — initial spec (4 obligations)
- Spec `Check.lean`: `double`, `double_eq`, `add_comm'`, `reverse_reverse`.
- Agent trace: `read_task → write_solution → check` → **PROVED**.
- Committed as `Solution.lean`.

## Run 2 — evolved spec (+ induction obligation)
- `Check.lean` hardened to additionally require `sumList` and
  `sumList_append : ∀ l m, sumList (l ++ m) = sumList l + sumList m`
  (a genuine induction proof).
- Before the run, the project failed: `Unknown identifier Solution.sumList`.
- Agent adapted the existing `Solution.lean` → **PROVED** again. It chose a
  structural-recursion proof (equation lemmas), not a copy of any reference.

## Independent re-verification (not trusting the agent)
```
$ lake env lean Check.lean      # exit 0  (frozen spec holds)
```

## Axiom audit (anti-cheat)
```
'Solution.double_eq'        does not depend on any axioms
'Solution.add_comm''        does not depend on any axioms
'Solution.reverse_reverse'  depends on axioms: [propext]
'Solution.sumList_append'   depends on axioms: [propext]
```
Only `propext` is used — inside the allowed set `{propext, Classical.choice,
Quot.sound}`. No `sorry`/`admit`/`axiom`/`native_decide`/`unsafe`.

## Agent commit history (local, before flattening for publication)
```
5bd41a3 Agent: spec proved                 # run 2
d8ef736 Evolve frozen spec: require sumList + sumList_append (induction)
b09f45c Agent: spec proved                 # run 1
ce5533c Example Lean task: frozen spec Check.lean (Solution.lean to be written by the agent)
```

The final proof is in `Solution.lean`; the frozen specification is `Check.lean`.
