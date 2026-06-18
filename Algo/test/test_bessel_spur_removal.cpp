/**
 * @file test_bessel_spur_removal.cpp
 * @brief LLR_ALG_002 verification — Bessel notch cascade (host).
 */

#include "algorithms/BesselSpurRemoval.h"
#include "config/arithmetic_target.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
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

static int32_t q427(double v) { return static_cast<int32_t>(std::llround(v * static_cast<double>(arith::Q_SCALE))); }

int main()
{
    std::printf("Running BesselSpurRemoval tests...\n");

    const double fs = 48000.0;
    const double f0 = 6000.0;
    const std::size_t N = 2048;

    // Build a tone at f0, amplitude 0.5, on the I channel; Q channel = 0.
    std::vector<int32_t> iBuf(N), qBuf(N, 0), iRef(N);
    for (std::size_t n = 0; n < N; ++n)
    {
        iBuf[n] = q427(0.5 * std::sin(2.0 * 3.14159265358979323846 * f0 * n / fs));
        iRef[n] = iBuf[n];
    }

    // T006 — Kmax = 0 (no notch configured) → exact passthrough.
    {
        dsp::BesselSpurRemoval bsr;
        std::vector<int32_t> i2 = iBuf, q2 = qBuf;
        CHECK(bsr.process(i2.data(), q2.data(), N) == 0);
        bool identical = true;
        for (std::size_t n = 0; n < N; ++n)
        {
            if (i2[n] != iRef[n] || q2[n] != 0)
            {
                identical = false;
            }
        }
        CHECK(identical); // no-op preserves the buffer exactly
    }

    // T002 — notch at f0 attenuates the tone (steady-state tail).
    {
        dsp::BesselSpurRemoval bsr;
        float spur = static_cast<float>(f0);
        int32_t cfg = bsr.configure(&spur, 1, static_cast<float>(fs));
        CHECK(cfg == 1);

        std::vector<int32_t> i2 = iBuf, q2 = qBuf;
        CHECK(bsr.process(i2.data(), q2.data(), N) == 1);

        // RMS of input vs output tail (last quarter, after settling).
        double inSq = 0.0, outSq = 0.0;
        std::size_t start = 3 * N / 4;
        for (std::size_t n = start; n < N; ++n)
        {
            double in = static_cast<double>(iRef[n]);
            double out = static_cast<double>(i2[n]);
            inSq += in * in;
            outSq += out * out;
        }
        double atten_dB = 10.0 * std::log10(inSq / (outSq + 1.0));
        std::printf("  notch attenuation at f0 = %.1f dB\n", atten_dB);
        CHECK(atten_dB > 20.0); // strong attenuation of the on-frequency tone

        // T012 — I/Q independent: Q was all zeros → stays all zeros.
        bool qZero = true;
        for (std::size_t n = 0; n < N; ++n)
        {
            if (q2[n] != 0)
            {
                qZero = false;
            }
        }
        CHECK(qZero);
    }

    // T011 — reset() clears state: after reset, zeros in → zeros out.
    {
        dsp::BesselSpurRemoval bsr;
        float spur = static_cast<float>(f0);
        bsr.configure(&spur, 1, static_cast<float>(fs));
        std::vector<int32_t> i2 = iBuf, q2 = qBuf;
        bsr.process(i2.data(), q2.data(), N); // build up state
        bsr.reset();
        CHECK(bsr.activeSpurs() == 0);
        std::vector<int32_t> z(16, 0), zq(16, 0);
        bsr.process(z.data(), zq.data(), 16);
        bool allZero = true;
        for (int k = 0; k < 16; ++k)
        {
            if (z[k] != 0)
            {
                allZero = false;
            }
        }
        CHECK(allZero);
    }

    // Gain-budget rejection: many wide notches should exceed G_total < 8.0.
    {
        dsp::BesselSpurRemoval bsr;
        float spurs[4] = {1000.0f, 2000.0f, 3000.0f, 4000.0f};
        int32_t cfg = bsr.configure(spurs, 4, static_cast<float>(fs), 5.0f); // very wide
        CHECK(cfg < 0); // rejected by the gain budget check
    }

    // Spur DETECTION (PDF §4): auto-detect the spur frequency, then attenuate.
    {
        dsp::BesselSpurRemoval bsr;
        // Detection buffer: strong complex spur at f0 (lands exactly on bin 32).
        const std::size_t Nd = 256;
        std::vector<int32_t> di(Nd), dq(Nd);
        std::srand(2024); // deterministic noise floor (PDF §4.1: spur above floor)
        for (std::size_t n = 0; n < Nd; ++n)
        {
            double ph = 2.0 * 3.14159265358979323846 * f0 * n / fs;
            // Strong spur at f0 + a realistic broadband noise floor.
            double noiseI = 0.01 * (2.0 * std::rand() / RAND_MAX - 1.0);
            double noiseQ = 0.01 * (2.0 * std::rand() / RAND_MAX - 1.0);
            di[n] = q427(0.5 * std::cos(ph) + noiseI);
            dq[n] = q427(0.5 * std::sin(ph) + noiseQ);
        }
        int32_t count = bsr.detectAndConfigure(di.data(), dq.data(), Nd,
                                               static_cast<float>(fs), 20.0f);
        std::printf("  spurs detected = %d\n", count);
        CHECK(count >= 1);

        // Process a fresh long tone at f0 with the auto-designed notch.
        std::vector<int32_t> i2 = iBuf, q2(N, 0);
        bsr.process(i2.data(), q2.data(), N);
        double inSq = 0.0, outSq = 0.0;
        for (std::size_t n = 3 * N / 4; n < N; ++n)
        {
            inSq += static_cast<double>(iRef[n]) * iRef[n];
            outSq += static_cast<double>(i2[n]) * i2[n];
        }
        double atten_dB = 10.0 * std::log10(inSq / (outSq + 1.0));
        std::printf("  auto-notch attenuation = %.1f dB\n", atten_dB);
        CHECK(atten_dB > 20.0);
    }

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
