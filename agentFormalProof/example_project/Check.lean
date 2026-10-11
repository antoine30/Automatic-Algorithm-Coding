import Solution

/-!
Frozen specification (read-only, hash-checked by the verifier).

`lake env lean Check.lean` must succeed: `Solution` must provide terms of EXACTLY
these types. The proofs live in `Solution.lean`, which the agent writes.
-/

example : Nat → Nat := Solution.double
example : ∀ n : Nat, Solution.double n = n + n := Solution.double_eq
example : ∀ a b : Nat, a + b = b + a := Solution.add_comm'
example : ∀ l : List Nat, l.reverse.reverse = l := Solution.reverse_reverse

-- Evolution (v2): a theorem that requires a genuine induction proof.
example : List Nat → Nat := Solution.sumList
example : ∀ l m : List Nat,
    Solution.sumList (l ++ m) = Solution.sumList l + Solution.sumList m :=
  Solution.sumList_append
