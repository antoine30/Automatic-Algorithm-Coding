/**
 * @file test_phase_compute.cpp
 * @brief LLR_ALG_003 verification — CORDIC atan2 (host).
 */

#include "algorithms/PhaseCompute.h"
#include "config/arithmetic_target.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

static int g_failures = 0;
static int g_checks = 0;
static long g_maxErr = 0;

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

// Check |got - want| <= tol (in LSB); track worst-case error.
static void checkNear(int32_t got, int32_t want, long tol, const char *what)
{
    long err = std::labs(static_cast<long>(got) - static_cast<long>(want));
    if (err > g_maxErr)
    {
        g_maxErr = err;
    }
    ++g_checks;
    if (err > tol)
    {
        ++g_failures;
        std::printf("  [FAIL] %s: got %d want %d (err %ld LSB > tol %ld)\n",
                    what, got, want, err, tol);
    }
}

int main()
{
    std::printf("Running PhaseCompute (CORDIC atan2) tests...\n");

    dsp::PhaseCompute pc;
    const int32_t A = arith::SCALE_Q427; // 1.0 in Q4.27

    const long tol = 4; // ~4 LSB out of 2^27 (≈ 3e-8 rad)

    // T001 — pure +I → 0
    checkNear(pc.computePhase(A, 0), 0, tol, "atan2(0,+A)=0");
    // T002 — pure +Q → +π/2
    checkNear(pc.computePhase(0, A), arith::HALF_PI_Q427, tol, "atan2(+A,0)=+pi/2");
    // T003 — pure −I → +π (atan2(0,−A))
    checkNear(pc.computePhase(-A, 0), arith::PI_Q427, tol, "atan2(0,-A)=+pi");
    // pure −Q → −π/2
    checkNear(pc.computePhase(0, -A), -arith::HALF_PI_Q427, tol, "atan2(-A,0)=-pi/2");
    // 45° → +π/4
    checkNear(pc.computePhase(A, A), arith::PI_Q427 / 4, tol, "atan2(A,A)=+pi/4");
    // 135° → +3π/4
    checkNear(pc.computePhase(-A, A), 3 * (arith::PI_Q427 / 4), tol, "atan2(A,-A)=+3pi/4");
    // −135° → −3π/4
    checkNear(pc.computePhase(-A, -A), -3 * (arith::PI_Q427 / 4), tol, "atan2(-A,-A)=-3pi/4");

    // Edge: no signal → 0 (no crash)
    CHECK(pc.computePhase(0, 0) == 0);

    // Sweep against std::atan2 reference over many angles.
    long sweepMax = 0;
    for (int deg = -179; deg <= 180; ++deg)
    {
        double rad = deg * 3.14159265358979323846 / 180.0;
        int32_t I = static_cast<int32_t>(std::llround(std::cos(rad) * A));
        int32_t Q = static_cast<int32_t>(std::llround(std::sin(rad) * A));
        int32_t got = pc.computePhase(I, Q);
        int32_t want = static_cast<int32_t>(std::llround(rad * static_cast<double>(arith::Q_SCALE)));
        long err = std::labs(static_cast<long>(got) - static_cast<long>(want));
        if (err > sweepMax)
        {
            sweepMax = err;
        }
    }
    std::printf("  angle sweep (-179..180 deg): max error = %ld LSB\n", sweepMax);
    CHECK(sweepMax <= 8); // ≤ 8 LSB ≈ 6e-8 rad across the full circle

    std::printf("\n%d checks, %d failure(s) | worst axis error = %ld LSB\n",
                g_checks, g_failures, g_maxErr);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
