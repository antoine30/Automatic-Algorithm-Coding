#ifndef ARITHMETIC_TARGET_H
#define ARITHMETIC_TARGET_H

/**
 * @file arithmetic_target.h
 * @brief LLR_ALG_000 — Arithmetic Target Specification (single source of truth).
 *
 * Every shift, iteration count, accumulator width and saturation width in the
 * pipeline is DERIVED from the parameters below. No algorithm defines a format
 * parameter independently.
 *
 * NOTE on radian constants (spec deviation, intentional):
 *   LLR_ALG_000 §5 lists PI/TWOPI/HALF_PI with hex values that are actually
 *   scaled by 2^29 (Q2.29), not 2^27 — e.g. 0x6487ED51 = round(pi * 2^29).
 *   That is inconsistent with the Q4.27 format mandated in §3.2 (and is also why
 *   §5 claims "TWOPI overflows int32": only true at 2^29). Following the project
 *   derivation-chain rule ("all parameters derived from frac_bits"), the radian
 *   constants here are derived as round(value * 2^frac_bits) in Q4.27. In Q4.27,
 *   2*pi = 843,314,857 fits comfortably in int32, so no split subtraction is
 *   needed.
 */

#include <cstdint>
#include <climits>
#include <cmath>

namespace arith
{

// --- 3.1 Primary parameters (chosen) ---------------------------------------
constexpr int WORD_SIZE = 32; ///< CPU native register width.
constexpr int SIGN_BIT = 1;   ///< two's complement, all signals bipolar.
constexpr int INT_BITS = 4;   ///< covers max signal 8.0 with margin.

// --- 3.2 Derived parameters -------------------------------------------------
constexpr int FRAC_BITS = WORD_SIZE - SIGN_BIT - INT_BITS; ///< = 27 (Q4.27).
constexpr int64_t Q_SCALE = static_cast<int64_t>(1) << FRAC_BITS; ///< 2^27.

constexpr int MULTIPLY_SHIFT = FRAC_BITS;   ///< >> 27 after a multiply.
constexpr int CORDIC_ITERS = FRAC_BITS;     ///< 27 CORDIC iterations.
constexpr int ACC_WIDTH = 2 * WORD_SIZE;    ///< 64-bit accumulator.
constexpr int SAT_WIDTH = WORD_SIZE;        ///< saturate to 32 bits.

constexpr int ADC_FRAC_BITS = 15;                       ///< 16-bit left-aligned ADC.
constexpr int PROMOTE_SHIFT = FRAC_BITS - ADC_FRAC_BITS; ///< = 12.

// Q-format consistency (Initialization check §7).
static_assert(FRAC_BITS + INT_BITS + SIGN_BIT == WORD_SIZE,
              "Q format inconsistent: frac + int + sign must equal word size");
static_assert(FRAC_BITS == 27, "frac_bits must be 27 for Q4.27");

// --- 5. Precomputed radian constants (Q4.27, derived from frac_bits) --------
// Computed once at static-init using double (permitted: initialization only).
inline const int32_t SCALE_Q427 = static_cast<int32_t>(Q_SCALE); // 0x08000000
inline const int32_t PI_Q427 =
    static_cast<int32_t>(std::llround(3.14159265358979323846 * static_cast<double>(Q_SCALE)));
inline const int32_t TWOPI_Q427 =
    static_cast<int32_t>(std::llround(2.0 * 3.14159265358979323846 * static_cast<double>(Q_SCALE)));
inline const int32_t HALF_PI_Q427 =
    static_cast<int32_t>(std::llround(0.5 * 3.14159265358979323846 * static_cast<double>(Q_SCALE)));

// --- 3. Saturation (clamp) — Group: store to int32 -------------------------
/// Saturate an int64 value to word_size (32 bits) and store as int32 (Q4.27).
inline int32_t saturate_i32(int64_t v)
{
    if (v > INT32_MAX)
    {
        return INT32_MAX;
    }
    if (v < INT32_MIN)
    {
        return INT32_MIN;
    }
    return static_cast<int32_t>(v);
}

/// Q4.27 × Q4.27 multiply with renormalization and saturation (Group B).
/// widen → multiply (Q8.54) → >> frac_bits (Q4.27) → saturate to int32.
inline int32_t q427_mul(int32_t a, int32_t b)
{
    int64_t prod = static_cast<int64_t>(a) * static_cast<int64_t>(b); // Q8.54
    return saturate_i32(prod >> MULTIPLY_SHIFT);                      // Q4.27
}

} // namespace arith

#endif // ARITHMETIC_TARGET_H
