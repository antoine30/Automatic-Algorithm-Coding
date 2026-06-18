/**
 * @file AdcPromote.cpp
 * @brief LLR_ALG_001 — Implementation of ADC promote and de-interleave.
 */

#include "algorithms/AdcPromote.h"

#include "config/arithmetic_target.h"

namespace dsp
{

void adcPromote(const int16_t *dmaBuffer, int32_t *iBuffer, int32_t *qBuffer,
                std::size_t len)
{
    // Promotion factor 2^12. Multiply (not <<) so negative samples are
    // well-defined (left-shift of a negative value is UB before C++20).
    constexpr int32_t kPromote = static_cast<int32_t>(1) << arith::PROMOTE_SHIFT;
    for (std::size_t n = 0; n < len; ++n)
    {
        // Group 0: int16 Q1.15 → int32 Q4.27 (promotion, no saturation).
        iBuffer[n] = static_cast<int32_t>(dmaBuffer[2 * n]) * kPromote;
        qBuffer[n] = static_cast<int32_t>(dmaBuffer[2 * n + 1]) * kPromote;
    }
}

} // namespace dsp
