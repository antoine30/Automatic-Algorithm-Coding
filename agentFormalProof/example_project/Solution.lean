namespace Solution

def double (n : Nat) : Nat := n + n

theorem double_eq : ∀ n : Nat, double n = n + n := fun _ => rfl

theorem add_comm' : ∀ a b : Nat, a + b = b + a := Nat.add_comm

theorem reverse_reverse : ∀ l : List Nat, l.reverse.reverse = l := List.reverse_reverse

def sumList : List Nat → Nat
  | [] => 0
  | x :: xs => x + sumList xs

theorem sumList_append : ∀ l m : List Nat, sumList (l ++ m) = sumList l + sumList m
  | [], m => by simp [sumList]
  | x :: xs, m => by
      simp [sumList, sumList_append xs m, Nat.add_assoc]

end Solution
