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

## C++ generated from Lean (oracle)

`lean_generated.hpp` is **auto-generated from the verified Lean `Solution`** by
[`../gen/Gen.lean`](../gen/Gen.lean): Lean itself computes the expected outputs of
`double`, `sumList`, `reverse` and `sumList(l ++ m)` on sample inputs and emits
them as C++ golden vectors. The test then asserts the C++ implementation
reproduces exactly those Lean-computed values — so Lean is the single source of
truth for both the proof *and* the reference data.

```sh
make generate   # re-emit lean_generated.hpp FROM Lean (needs the toolchain)
make            # build + run the checks (uses the committed lean_generated.hpp)
```

Pipeline:
```
Solution.lean ──(proved vs Check.lean)──► gen/Gen.lean ──emits──► cpp/lean_generated.hpp
                                                                        │
                                            test_solution.cpp ──asserts C++ == Lean values
```

## Build & run
```sh
make        # g++ -std=c++17, builds and runs the checks
```

## Status vs. the proof
- The Lean file is the **proof**: the properties hold for *all* inputs,
  machine-checked (`lake env lean Check.lean` → exit 0, axioms ⊆ {propext}).
- This C++ is the **implementation**; its tests only *sample* inputs. They are a
  cross-check that the code matches the spec, not a proof.
- Caveat: Lean `Nat` is unbounded; `uint64_t` wraps, so the identities hold only
  without 64-bit overflow (test inputs are kept small).
