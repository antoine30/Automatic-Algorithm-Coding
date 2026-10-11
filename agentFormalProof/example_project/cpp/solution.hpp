#ifndef SOLUTION_HPP
#define SOLUTION_HPP

/**
 * @file solution.hpp
 * @brief C++ implementation mirroring the formally-verified Lean `Solution`.
 *
 * Each function here corresponds 1:1 to a definition in
 * ../Solution.lean, which was machine-checked against the frozen spec
 * ../Check.lean (see ../RESULTS.md). The Lean theorems PROVE the properties
 * below for all inputs; this C++ is the executable counterpart.
 *
 * Caveat: Lean `Nat` is unbounded; here it maps to `uint64_t`, so the proven
 * identities hold only while values stay within 64-bit range (no overflow).
 */

#include <cstdint>
#include <vector>

namespace solution
{

/// Lean: `def double (n : Nat) : Nat := n + n`
inline uint64_t doubleNat(uint64_t n)
{
    return n + n;
}

/// Lean: `def sumList : List Nat → Nat | [] => 0 | x :: xs => x + sumList xs`
inline uint64_t sumList(const std::vector<uint64_t> &l)
{
    uint64_t acc = 0;
    for (uint64_t x : l)
    {
        acc += x;
    }
    return acc;
}

/// Lean: `List.reverse` (as used by theorem `reverse_reverse`)
inline std::vector<uint64_t> reverse(const std::vector<uint64_t> &l)
{
    return std::vector<uint64_t>(l.rbegin(), l.rend());
}

/// Lean: list concatenation `l ++ m` (as used by theorem `sumList_append`)
inline std::vector<uint64_t> append(std::vector<uint64_t> l, const std::vector<uint64_t> &m)
{
    l.insert(l.end(), m.begin(), m.end());
    return l;
}

} // namespace solution

#endif // SOLUTION_HPP
