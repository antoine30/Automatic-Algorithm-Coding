# C++ mirror of the verified Lean `Solution`

Executable C++ counterpart of the formally-verified Lean definitions in
[`../Solution.lean`](../Solution.lean), proved against the frozen spec
[`../Check.lean`](../Check.lean) (results in [`../RESULTS.md`](../RESULTS.md)).

## Correspondence

| Lean (`Solution.lean`) | C++ (`solution.hpp`) |
|------------------------|----------------------|
| `double (n : Nat) : Nat := n + n` | `uint64_t doubleNat(uint64_t n)` |
| `sumList : List Nat → Nat` | `uint64_t sumList(const std::vector<uint64_t>&)` |
| `List.reverse` | `std::vector<uint64_t> reverse(...)` |
| `l ++ m` | `std::vector<uint64_t> append(l, m)` |

| Lean theorem (proved ∀ inputs) | C++ runtime check |
|--------------------------------|-------------------|
| `double_eq` | `doubleNat(n) == n + n` |
| `add_comm'` | `a + b == b + a` |
| `reverse_reverse` | `reverse(reverse(l)) == l` |
| `sumList_append` | `sumList(l ++ m) == sumList(l) + sumList(m)` |

## C++ generated from Lean

Both headers are **auto-generated from the verified Lean `Solution`** by
[`../gen/Gen.lean`](../gen/Gen.lean) — nothing in them is hand-written:

- `solution.hpp` — the C++ **implementation** (bodies mirror each Lean `def`).
- `lean_generated.hpp` — C++ **golden vectors**: Lean itself computes the expected
  outputs of `double`, `sumList`, `reverse`, `sumList(l ++ m)` (Lean = oracle).

The test then asserts the implementation reproduces exactly those Lean-computed
values, so Lean is the single source of truth for the proof *and* the code *and*
the reference data. If the implementation ever drifts from `Solution.lean`, the
oracle vectors no longer match and the test fails.

```sh
make generate   # re-emit solution.hpp + lean_generated.hpp FROM Lean (needs toolchain)
make            # build + run the checks (uses the committed generated headers)
```

Pipeline:
```
Solution.lean ─(proved vs Check.lean)─► gen/Gen.lean ─emits─► cpp/solution.hpp      (implementation)
                                                     └─emits─► cpp/lean_generated.hpp (oracle vectors)
                                                                      │
                                            test_solution.cpp ─asserts─ C++ == Lean values
```

## Status vs. the proof
- The Lean file is the **proof**: the properties hold for *all* inputs,
  machine-checked (`lake env lean Check.lean` → exit 0, axioms ⊆ {propext}).
- This C++ is the **implementation**; its tests only *sample* inputs. They are a
  cross-check that the code matches the spec, not a proof.
- Caveat: Lean `Nat` is unbounded; `uint64_t` wraps, so the identities hold only
  without 64-bit overflow (test inputs are kept small).
