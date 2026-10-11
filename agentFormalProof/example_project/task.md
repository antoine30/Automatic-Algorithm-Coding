# Task — prove the frozen spec

Write `Solution.lean` (everything inside `namespace Solution`) so that the frozen
specification in `Check.lean` type-checks via `lake env lean Check.lean`.

`Solution` must provide terms of exactly the types required by `Check.lean`:

1. `double (n : Nat) : Nat` — n doubled.
2. `double_eq  : ∀ n : Nat, double n = n + n`
3. `add_comm'  : ∀ a b : Nat, a + b = b + a`
4. `reverse_reverse : ∀ l : List Nat, l.reverse.reverse = l`
5. `sumList : List Nat → Nat` (sum of the elements) and
   `sumList_append : ∀ l m : List Nat, sumList (l ++ m) = sumList l + sumList m`
   (this one needs an induction proof; only core Lean is available, no Mathlib).

Rules:
- Only the standard axioms `{propext, Classical.choice, Quot.sound}` are allowed.
- Forbidden: `sorry`, `admit`, `axiom`, `native_decide`, `unsafe`.
- Do not modify `Check.lean` (it is frozen and hash-checked).
