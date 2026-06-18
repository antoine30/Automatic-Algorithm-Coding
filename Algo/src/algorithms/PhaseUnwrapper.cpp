/**
 * @file PhaseUnwrapper.cpp
 * @brief LLR_ALG_004 — Phase unwrapper implementation.
 */

#include "algorithms/PhaseUnwrapper.h"

#include "config/arithmetic_target.h"

namespace dsp
{

PhaseUnwrapper::PhaseUnwrapper() : m_prevPhase(0), m_accumulator(0), m_initialized(false)
{
}

void PhaseUnwrapper::process(const int32_t *phaseIn, int32_t *phaseOut, std::size_t len)
{
    for (std::size_t n = 0; n < len; ++n)
    {
        const int32_t phase = phaseIn[n];

        // Group 5: first sample after reset initializes state.
        if (!m_initialized)
        {
            m_accumulator = static_cast<int64_t>(phase);
            m_prevPhase = phase;
            m_initialized = true;
            phaseOut[n] = arith::saturate_i32(m_accumulator);
            continue;
        }

        // Group 1: delta = phase[n] − prev (Q4.27 − Q4.27 = Q4.27, no shift).
        int64_t delta = static_cast<int64_t>(phase) - static_cast<int64_t>(m_prevPhase);
        int32_t d = arith::saturate_i32(delta);

        // Group 2: wrap to (−π, +π]. Only one branch executes per sample.
        if (d > arith::PI_Q427)
        {
            d = arith::saturate_i32(static_cast<int64_t>(d) - arith::TWOPI_Q427);
        }
        else if (d < -arith::PI_Q427)
        {
            d = arith::saturate_i32(static_cast<int64_t>(d) + arith::TWOPI_Q427);
        }

        // Group 3: accumulate (int64, no truncation), saturate on write only.
        m_accumulator += static_cast<int64_t>(d);
        phaseOut[n] = arith::saturate_i32(m_accumulator);

        // Group 4: state update.
        m_prevPhase = phase;
    }
}

void PhaseUnwrapper::reset()
{
    m_prevPhase = 0;
    m_accumulator = 0;
    m_initialized = false;
}

} // namespace dsp
