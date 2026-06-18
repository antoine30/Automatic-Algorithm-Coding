/**
 * @file test_phase_unwrapper.cpp
 * @brief LLR_ALG_004 verification — phase unwrapper (host).
 */

#include "algorithms/PhaseUnwrapper.h"
#include "config/arithmetic_target.h"

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

int main()
{
    std::printf("Running PhaseUnwrapper tests...\n");

    const int32_t PI = arith::PI_Q427;
    const int32_t TWOPI = arith::TWOPI_Q427;

    // T005 — first sample initializes: output[0] == input[0].
    {
        dsp::PhaseUnwrapper uw;
        int32_t in[3] = {12345, 12345 + 1000, 12345 + 2000};
        int32_t out[3];
        uw.process(in, out, 3);
        CHECK(out[0] == in[0]);
        CHECK(out[1] == in[0] + 1000);
        CHECK(out[2] == in[0] + 2000);
    }

    // T002 — wrap across +π discontinuity stays continuous (no 2π jump).
    {
        dsp::PhaseUnwrapper uw;
        // raw phase steps just past +π then wraps to near −π
        int32_t in[4] = {PI - 1000, PI - 500, -PI + 500, -PI + 1000};
        int32_t out[4];
        uw.process(in, out, 4);
        // Every unwrapped step must be small (≤ π), no ~2π jump.
        for (int n = 1; n < 4; ++n)
        {
            long d = std::labs(static_cast<long>(out[n]) - static_cast<long>(out[n - 1]));
            CHECK(d <= static_cast<long>(PI));
        }
        // Net motion over the wrap is ~ +2000 LSB (monotone rising), not −2π.
        CHECK(out[3] > out[0]);
    }

    // T004 — two-buffer continuity == single buffer.
    {
        int32_t in[6] = {0, 1000, 2000, 3000, 4000, 5000};
        int32_t single[6];
        dsp::PhaseUnwrapper a;
        a.process(in, single, 6);

        int32_t split[6];
        dsp::PhaseUnwrapper b;
        b.process(in, split, 3);          // buffer 1
        b.process(in + 3, split + 3, 3);  // buffer 2 — state carries over
        bool same = true;
        for (int n = 0; n < 6; ++n)
        {
            if (single[n] != split[n])
            {
                same = false;
            }
        }
        CHECK(same);
    }

    // T006 — accumulator is int64: a rising wrapped phase accumulates past
    // INT32_MAX. With an int32 accumulator the sum would wrap negative; with
    // int64 the output stays monotone and saturates to INT32_MAX on write.
    {
        dsp::PhaseUnwrapper uw;
        const std::size_t M = 64;
        std::vector<int32_t> in(M), out(M);
        const int32_t step = arith::HALF_PI_Q427; // < π, so each delta is +step
        int32_t raw = 0;
        int32_t prevOut = 0;
        bool first = true;
        bool monotone = true;
        // 50 buffers × 64 × (π/2) ≫ INT32_MAX → forces saturation on write.
        for (int rep = 0; rep < 50; ++rep)
        {
            for (std::size_t n = 0; n < M; ++n)
            {
                raw += step;                 // rising phase
                while (raw > PI) raw -= TWOPI; // wrapped into [-π, π]
                while (raw < -PI) raw += TWOPI;
                in[n] = raw;
            }
            uw.process(in.data(), out.data(), M);
            for (std::size_t n = 0; n < M; ++n)
            {
                if (!first && out[n] < prevOut)
                {
                    monotone = false; // an int32 accumulator would wrap negative
                }
                prevOut = out[n];
                first = false;
            }
        }
        CHECK(monotone);             // never wrapped negative → int64 accumulator
        CHECK(prevOut == INT32_MAX); // saturates on write once out of int32 range
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
