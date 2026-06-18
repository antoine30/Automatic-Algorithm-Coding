/**
 * @file RfPipeline.cpp
 * @brief LLR_ALG_007 — Pipeline assembly implementation.
 */

#include "algorithms/RfPipeline.h"

#include "algorithms/AdcPromote.h"
#include "config/arithmetic_target.h"

namespace dsp
{

RfPipeline::RfPipeline() : m_bessel(), m_phase(), m_unwrap(), m_iBuf{}, m_qBuf{}, m_phaseBuf{}
{
}

void RfPipeline::init()
{
    // §6 init checks. Q-format/frac-bits are compile-time invariants in
    // arithmetic_target.h (static_assert). Promote shift consistency:
    static_assert(arith::PROMOTE_SHIFT == arith::FRAC_BITS - arith::ADC_FRAC_BITS,
                  "promote shift must equal frac_bits - adc_frac_bits");
    m_phase.init();
    reset();
}

TaskStatus RfPipeline::process(const int16_t *dmaBuffer, int32_t *phaseOut, std::size_t len)
{
    if (dmaBuffer == nullptr || phaseOut == nullptr)
    {
        return TaskStatus::BAD_ARGUMENT;
    }
    if (len > MAX_BUF_SIZE)
    {
        return TaskStatus::BAD_ARGUMENT;
    }

    // Group 0: promote + de-interleave (LLR_ALG_001).
    adcPromote(dmaBuffer, m_iBuf, m_qBuf, len);

    // Group 1: Bessel spur removal (in-place on iBuf/qBuf).
    if (m_bessel.process(m_iBuf, m_qBuf, len) < 0)
    {
        return TaskStatus::STAGE_BESSEL;
    }

    // Group 2: instantaneous phase (CORDIC atan2).
    m_phase.process(m_iBuf, m_qBuf, m_phaseBuf, len);

    // Group 3: phase unwrap → output.
    m_unwrap.process(m_phaseBuf, phaseOut, len);

    return TaskStatus::OK;
}

void RfPipeline::reset()
{
    m_bessel.reset();
    m_unwrap.reset();
}

} // namespace dsp
