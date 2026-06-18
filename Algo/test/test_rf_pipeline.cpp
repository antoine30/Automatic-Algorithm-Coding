/**
 * @file test_rf_pipeline.cpp
 * @brief LLR_ALG_007 verification — end-to-end RF pipeline (host).
 */

#include "algorithms/RfPipeline.h"
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

// Build an interleaved int16 Q1.15 IQ buffer: a phasor rotating by dPhase/sample.
static void makePhasor(std::vector<int16_t> &dma, std::size_t len, double dPhase,
                       double amp = 0.4)
{
    dma.resize(2 * len);
    double ph = 0.0;
    for (std::size_t n = 0; n < len; ++n)
    {
        dma[2 * n] = static_cast<int16_t>(std::lround(amp * std::cos(ph) * 32767.0));
        dma[2 * n + 1] = static_cast<int16_t>(std::lround(amp * std::sin(ph) * 32767.0));
        ph += dPhase;
    }
}

int main()
{
    std::printf("Running RfPipeline end-to-end tests...\n");

    dsp::RfPipeline pipe;
    pipe.init();

    const std::size_t len = 256;
    const double dPhase = 0.05; // rad/sample, well below π → no aliasing of wrap
    std::vector<int16_t> dma;
    makePhasor(dma, len, dPhase, 0.9); // near full-scale → minimal ADC quantization

    std::vector<int32_t> phaseOut(len, 0);

    // T001 — full pipeline runs and returns OK.
    CHECK(pipe.process(dma.data(), phaseOut.data(), len) == TaskStatus::OK);

    // T005 — first output sample starts near 0 (fresh state).
    CHECK(std::labs(phaseOut[0]) < 8);

    // T003/T006 — unwrapped output is monotone rising with steps ≈ dPhase and
    // never jumps by more than π.
    const int32_t expStep =
        static_cast<int32_t>(std::llround(dPhase * static_cast<double>(arith::Q_SCALE)));
    bool monotone = true;
    long maxStepErr = 0;
    for (std::size_t n = 1; n < len; ++n)
    {
        long d = static_cast<long>(phaseOut[n]) - static_cast<long>(phaseOut[n - 1]);
        if (d < 0)
        {
            monotone = false;
        }
        if (d > static_cast<long>(arith::PI_Q427))
        {
            CHECK(false); // jump > π forbidden
        }
        long e = std::labs(d - static_cast<long>(expStep));
        if (e > maxStepErr)
        {
            maxStepErr = e;
        }
    }
    std::printf("  per-sample step error vs ideal: max %ld LSB\n", maxStepErr);
    CHECK(monotone);
    // Per-sample phase precision is bounded by ADC quantization, not the
    // fixed-point algorithm: ~1/(amp·32767) rad ≈ 4500 LSB at amp 0.9. The
    // CORDIC core itself is ≤ ~5 LSB (see test_phase_compute). Bound generously.
    CHECK(maxStepErr < 16000); // ≈ 1.2e-4 rad, ≪ one step (6.7e6 LSB)

    // Bad arguments.
    CHECK(pipe.process(nullptr, phaseOut.data(), len) == TaskStatus::BAD_ARGUMENT);
    CHECK(pipe.process(dma.data(), phaseOut.data(), dsp::MAX_BUF_SIZE + 1) ==
          TaskStatus::BAD_ARGUMENT);

    // T004 — two half-buffers == one full buffer (cross-buffer state continuity).
    {
        dsp::RfPipeline a;
        a.init();
        std::vector<int32_t> full(len);
        a.process(dma.data(), full.data(), len);

        dsp::RfPipeline b;
        b.init();
        std::vector<int32_t> split(len);
        b.process(dma.data(), split.data(), len / 2);
        b.process(dma.data() + len, split.data() + len / 2, len / 2);

        bool same = true;
        for (std::size_t n = 0; n < len; ++n)
        {
            if (full[n] != split[n])
            {
                same = false;
            }
        }
        CHECK(same);
    }

    // T005 — reset() then process: output again starts from ~0.
    pipe.reset();
    pipe.process(dma.data(), phaseOut.data(), len);
    CHECK(std::labs(phaseOut[0]) < 8);

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
