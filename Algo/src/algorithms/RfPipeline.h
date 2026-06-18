#ifndef RF_PIPELINE_H
#define RF_PIPELINE_H

/**
 * @file RfPipeline.h
 * @brief LLR_ALG_007 — RF processing pipeline assembly.
 *
 * Chains: promote/de-interleave → Bessel spur removal → CORDIC phase → phase
 * unwrap. Format is int32 Q4.27 at every internal stage boundary (§2). Buffers
 * are static (no dynamic allocation).
 */

#include <cstddef>
#include <cstdint>

#include "algorithms/BesselSpurRemoval.h"
#include "algorithms/PhaseCompute.h"
#include "algorithms/PhaseUnwrapper.h"
#include "common/types.h"

namespace dsp
{

/// Maximum samples (IQ pairs) per buffer (§4).
constexpr std::size_t MAX_BUF_SIZE = 256;

class RfPipeline
{
public:
    RfPipeline();

    /// Verify arithmetic invariants and initialize all stages (§6).
    void init();

    /**
     * @brief Run the full pipeline on one DMA buffer.
     * @param dmaBuffer Interleaved IQ, int16 Q1.15, length = 2 × len.
     * @param phaseOut  Unwrapped phase output, int32 Q4.27, length = len.
     * @param len       Number of IQ pairs (≤ MAX_BUF_SIZE).
     * @return TaskStatus::OK, or the first failing stage.
     */
    TaskStatus process(const int16_t *dmaBuffer, int32_t *phaseOut, std::size_t len);

    /// Reset cross-buffer state of all stages (stream restart).
    void reset();

    /// Access the spur-removal stage to configure notches before processing.
    BesselSpurRemoval &bessel() { return m_bessel; }

private:
    BesselSpurRemoval m_bessel;
    PhaseCompute m_phase;
    PhaseUnwrapper m_unwrap;

    int32_t m_iBuf[MAX_BUF_SIZE];     ///< Q4.27
    int32_t m_qBuf[MAX_BUF_SIZE];     ///< Q4.27
    int32_t m_phaseBuf[MAX_BUF_SIZE]; ///< Q4.27
};

} // namespace dsp

#endif // RF_PIPELINE_H
