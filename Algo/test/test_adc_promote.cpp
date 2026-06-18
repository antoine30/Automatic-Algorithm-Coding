/**
 * @file test_adc_promote.cpp
 * @brief LLR_ALG_001 verification — ADC promote / de-interleave (host).
 */

#include "algorithms/AdcPromote.h"
#include "config/arithmetic_target.h"

#include <cstdio>

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
    std::printf("Running AdcPromote tests...\n");

    // T003 — interleaved IQ de-interleaved; T001/T002 — exact << 12 promotion.
    const std::size_t len = 5;
    int16_t dma[2 * len] = {1, -1, 100, -100, 32767, -32768, 0, 12345, -5, 5};
    int32_t iBuf[len] = {0};
    int32_t qBuf[len] = {0};

    dsp::adcPromote(dma, iBuf, qBuf, len);

    const int32_t scale = 1 << arith::PROMOTE_SHIFT; // 2^12
    for (std::size_t n = 0; n < len; ++n)
    {
        CHECK(iBuf[n] == static_cast<int32_t>(dma[2 * n]) * scale);
        CHECK(qBuf[n] == static_cast<int32_t>(dma[2 * n + 1]) * scale);
    }

    // T002 — full-scale int16 promotes without overflow (fits int32 Q4.27).
    CHECK(iBuf[2] == 32767 * scale); // 134,213,632 < INT32_MAX
    CHECK(qBuf[2] == -32768 * scale);

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
