#ifndef PHASE_COMPUTE_H
#define PHASE_COMPUTE_H

/**
 * @file PhaseCompute.h
 * @brief LLR_ALG_003 — Instantaneous phase via 27-iteration CORDIC (atan2).
 *
 * Computes phase = atan2(Q, I) in Q4.27, range [-π, +π]. The rotation table and
 * gain-compensation constant are precomputed in float at init (Groups 1, 2);
 * the per-sample CORDIC vectoring (Group 3) and final saturation (Group 4) are
 * integer-only — no float in the inner loop.
 */

#include <cstddef>
#include <cstdint>

#include "config/arithmetic_target.h"

namespace dsp
{

class PhaseCompute
{
public:
    PhaseCompute();

    /// Build the CORDIC angle table and gain-compensation constant (init only).
    void init();

    /// @return atan2(Q, I) in int32 Q4.27, range [-π, +π]. (Groups 3, 4)
    int32_t computePhase(int32_t I, int32_t Q) const;

    /// Compute unwrapped-input phase for a whole buffer.
    void process(const int32_t *iBuffer, const int32_t *qBuffer,
                 int32_t *phaseBuffer, std::size_t len) const;

    /**
     * @brief Apply CORDIC gain compensation to an amplitude sample (Group 5).
     * Note: scaling I and Q equally does not change atan2, so this is NOT
     * applied inside computePhase(); it is provided for callers that need
     * gain-corrected amplitudes.
     */
    int32_t compensateAmplitude(int32_t v) const { return arith::q427_mul(v, m_comp); }

    int32_t cordicComp() const { return m_comp; }
    const int32_t *angleTable() const { return m_angle; }

private:
    int32_t m_angle[arith::CORDIC_ITERS]; ///< angle[i] = atan(2^-i) in Q4.27.
    int32_t m_comp;                       ///< CORDIC_COMP = 1/K27 in Q4.27.
    bool m_initialized;
};

} // namespace dsp

#endif // PHASE_COMPUTE_H
