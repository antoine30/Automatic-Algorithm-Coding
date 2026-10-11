/**
 * @file test_solution.cpp
 * @brief Runtime checks of the four properties PROVED in ../Solution.lean.
 *
 * In Lean these are theorems (true for all inputs, machine-checked). Here they
 * are sampled/randomised sanity checks on the C++ mirror — a cross-check that
 * the executable code matches the verified specification.
 *
 *   Lean theorem              →  property checked here
 *   double_eq                 →  doubleNat(n) == n + n
 *   add_comm'                 →  a + b == b + a
 *   reverse_reverse           →  reverse(reverse(l)) == l
 *   sumList_append            →  sumList(l ++ m) == sumList(l) + sumList(m)
 */

#include "solution.hpp"
#include "lean_generated.hpp" // golden vectors computed by Lean (gen/Gen.lean)

#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do                                                                         \
    {                                                                          \
        ++g_checks;                                                            \
        if (!(cond))                                                           \
        {                                                                      \
            ++g_failures;                                                      \
            std::printf("  [FAIL] %s:%d  %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                      \
    } while (0)

int main()
{
    using namespace solution;
    std::printf("Checking C++ mirror against the proved Lean properties...\n");

    // double_eq : doubleNat(n) == n + n
    for (uint64_t n = 0; n < 1000; ++n)
    {
        CHECK(doubleNat(n) == n + n);
    }

    // add_comm' : a + b == b + a
    for (uint64_t a = 0; a < 50; ++a)
    {
        for (uint64_t b = 0; b < 50; ++b)
        {
            CHECK(a + b == b + a);
        }
    }

    // reverse_reverse : reverse(reverse(l)) == l   (+ sumList_append)
    std::mt19937_64 rng(12345);
    std::uniform_int_distribution<uint64_t> val(0, 1000);
    std::uniform_int_distribution<int> len(0, 20);
    for (int trial = 0; trial < 2000; ++trial)
    {
        std::vector<uint64_t> l(len(rng)), m(len(rng));
        for (auto &x : l) x = val(rng);
        for (auto &x : m) x = val(rng);

        CHECK(reverse(reverse(l)) == l);

        // sumList_append : sumList(l ++ m) == sumList(l) + sumList(m)
        CHECK(sumList(append(l, m)) == sumList(l) + sumList(m));
    }

    // --- Validation against Lean-generated golden vectors (the oracle) -------
    // These expected values were computed BY LEAN and emitted into
    // lean_generated.hpp; the C++ implementation must reproduce them exactly.
    for (const auto &c : lean_generated::doubleCases)
    {
        CHECK(doubleNat(c.n) == c.expected);
    }
    for (const auto &c : lean_generated::sumCases)
    {
        CHECK(sumList(c.l) == c.expected);
    }
    for (const auto &c : lean_generated::reverseCases)
    {
        CHECK(reverse(c.l) == c.expected);
    }
    for (const auto &c : lean_generated::appendSumCases)
    {
        CHECK(sumList(append(c.l, c.m)) == c.expected);
    }

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL CHECKS PASSED (consistent with the Lean proof)\n");
        return 0;
    }
    std::printf("CHECKS FAILED\n");
    return 1;
}
