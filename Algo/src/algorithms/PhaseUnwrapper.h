#ifndef PHASE_UNWRAPPER_H
#define PHASE_UNWRAPPER_H

/**
 * @file PhaseUnwrapper.h
 * @brief LLR_ALG_004 — Phase unwrapper (removes 2π discontinuities).
 *
 * Per sample: Δ = phase[n] − phase[n−1]; Δ = wrap(Δ, −π, +π); Φ += Δ.
 * The accumulator is int64 Q4.27 and persists across buffers (DMA callbacks),
 * never truncated between samples. No float, no shift (add/sub preserve Q4.27).
 */

#include <cstddef>
#include <cstdint>

namespace dsp
{

class PhaseUnwrapper
{
public:
    PhaseUnwrapper();

    /// Unwrap a phase buffer into @p phaseOut. State carries across calls.
    void process(const int32_t *phaseIn, int32_t *phaseOut, std::size_t len);

    /// Clear cross-buffer state (reset()): prev_phase, accumulator, initialized.
    void reset();

private:
    int32_t m_prevPhase;  ///< Q4.27, persists.
    int64_t m_accumulator; ///< Q4.27, persists (int64, never truncated).
    bool m_initialized;
};

} // namespace dsp

#endif // PHASE_UNWRAPPER_H
