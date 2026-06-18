/**
 * @file test_phase_snr.cpp
 * @brief Phase-precision harness: CORDIC phase error vs additive IQ noise.
 *
 * Quantifies how the fixed-point phase estimate degrades with input SNR. For a
 * sequence of noise levels it measures the RMS phase error against the ideal
 * angle and prints an SNR table. Assertions: error is bounded and decreases as
 * SNR improves (deterministic PRNG — reproducible).
 */

#include "algorithms/PhaseCompute.h"
#include "config/arithmetic_target.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

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

// Deterministic uniform noise in [-amp, amp].
static double urand(double amp)
{
    return amp * (2.0 * (static_cast<double>(std::rand()) / RAND_MAX) - 1.0);
}

int main()
{
    std::printf("Running phase SNR harness...\n");
    std::srand(12345); // reproducible

    dsp::PhaseCompute pc;
    const double A = 0.8 * static_cast<double>(arith::Q_SCALE); // signal amplitude
    const int trials = 4000;

    // Noise amplitudes as a fraction of signal amplitude.
    const double noiseFrac[] = {0.0, 0.001, 0.01, 0.1};
    const int levels = 4;
    double rmsRad[levels] = {0};

    std::printf("  %-12s %-12s %-12s\n", "noise/sig", "SNR(dB)", "RMS err(rad)");
    for (int li = 0; li < levels; ++li)
    {
        double nAmp = noiseFrac[li] * A;
        double sumSq = 0.0;
        for (int t = 0; t < trials; ++t)
        {
            double ang = (2.0 * (static_cast<double>(t) / trials) - 1.0) *
                         3.14159265358979323846; // sweep [-π, π]
            double I = A * std::cos(ang) + urand(nAmp);
            double Q = A * std::sin(ang) + urand(nAmp);
            int32_t got = pc.computePhase(static_cast<int32_t>(std::llround(I)),
                                          static_cast<int32_t>(std::llround(Q)));
            double gotRad = static_cast<double>(got) / static_cast<double>(arith::Q_SCALE);
            // wrap difference into [-π, π]
            double e = gotRad - ang;
            while (e > 3.14159265358979323846) e -= 2.0 * 3.14159265358979323846;
            while (e < -3.14159265358979323846) e += 2.0 * 3.14159265358979323846;
            sumSq += e * e;
        }
        rmsRad[li] = std::sqrt(sumSq / trials);
        double snrDb = (noiseFrac[li] > 0.0) ? 20.0 * std::log10(1.0 / noiseFrac[li]) : 1e9;
        std::printf("  %-12.4f %-12.1f %-.3e\n", noiseFrac[li],
                    (snrDb > 1e8 ? 999.0 : snrDb), rmsRad[li]);
    }

    // Noiseless RMS is the pure fixed-point/CORDIC error floor: tiny.
    CHECK(rmsRad[0] < 1e-6); // ≈ a few LSB / 2^27
    // Error increases monotonically with noise.
    CHECK(rmsRad[0] <= rmsRad[1]);
    CHECK(rmsRad[1] < rmsRad[2]);
    CHECK(rmsRad[2] < rmsRad[3]);
    // Phase error tracks additive noise: RMS ≈ (noise/sig)/√2 rad (small-angle).
    CHECK(rmsRad[3] < 0.2);  // at 10% noise (≈20 dB SNR)
    CHECK(rmsRad[2] < 0.02); // at 1% noise (≈40 dB SNR)

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
