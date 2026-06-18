#ifndef ADC_PROMOTE_H
#define ADC_PROMOTE_H

/**
 * @file AdcPromote.h
 * @brief LLR_ALG_001 — ADC promote and de-interleave (Group A).
 *
 * Converts the interleaved left-aligned ADC DMA buffer (int16 Q1.15) into two
 * separate int32 Q4.27 channels by the promotion shift (<< 12, derived from
 * LLR_ALG_000). Pure format shaping: no arithmetic, no saturation, no float.
 */

#include <cstddef>
#include <cstdint>

namespace dsp
{

/**
 * @brief Promote and de-interleave one DMA buffer.
 * @param dmaBuffer Interleaved IQ, int16 Q1.15, length = 2 × len.
 * @param iBuffer   Output I channel, int32 Q4.27, length = len.
 * @param qBuffer   Output Q channel, int32 Q4.27, length = len.
 * @param len       Number of IQ pairs.
 */
void adcPromote(const int16_t *dmaBuffer, int32_t *iBuffer, int32_t *qBuffer,
                std::size_t len);

} // namespace dsp

#endif // ADC_PROMOTE_H
