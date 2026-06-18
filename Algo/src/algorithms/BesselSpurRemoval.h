#ifndef BESSEL_SPUR_REMOVAL_H
#define BESSEL_SPUR_REMOVAL_H

/**
 * @file BesselSpurRemoval.h
 * @brief LLR_ALG_002 — Bessel notch spur removal (cascade of biquads).
 *
 * Removes narrowband RF spurs from Q4.27 IQ samples using a cascade of
 * second-order notch biquads (Direct Form II Transposed). Coefficients are
 * designed in float at init (Group 1); the inner loop is integer-only.
 * State w1/w2 are int64 Q8.54 and persist across buffers (never truncated).
 *
 * Spec gap: full frequency-domain spur DETECTION (PDF §4) depends on facilities
 * from LLR_ALG_001/006 (absent). This module implements the normative FILTER
 * path and exposes configure() to design notches at given spur frequencies.
 */

#include <cstddef>
#include <cstdint>

namespace dsp
{

/// Maximum simultaneous notch sections (static allocation, PDF §6.3).
constexpr std::size_t KMAX = 4;

/// Biquad coefficients in int32 Q4.27 (a0 = 1 implicit). PDF §5.4.
struct BiquadCoeffs
{
    int32_t b0;
    int32_t b1;
    int32_t b2;
    int32_t a1;
    int32_t a2;
};

class BesselSpurRemoval
{
public:
    BesselSpurRemoval();

    /**
     * @brief Design notch filters at the given spur frequencies (Group 1, float,
     *        init only). Verifies cascade gain < 8.0 (PDF §8.2 / eq.15).
     * @param spurHz       Array of spur centre frequencies in Hz.
     * @param count        Number of spurs (clamped to KMAX).
     * @param sampleRateHz ADC sample rate fs in Hz.
     * @param relBandwidth Notch bandwidth ratio Δω/ω0 (default 0.1).
     * @return number of notches configured, or < 0 on error (e.g. gain budget).
     */
    int32_t configure(const float *spurHz, std::size_t count, float sampleRateHz,
                       float relBandwidth = 0.1f);

    /**
     * @brief Detect spurs in a buffer and design notches for them (PDF §4).
     *
     * Frequency-domain detection (float, once per buffer — NOT the inner loop):
     * compute the magnitude spectrum of the complex signal I+jQ, estimate the
     * noise floor, and keep spectral peaks exceeding floor + thresholdDb, up to
     * KMAX strongest. Detected frequencies are then passed to configure().
     *
     * @return number of notches configured, or < 0 on error.
     */
    int32_t detectAndConfigure(const int32_t *iBuffer, const int32_t *qBuffer,
                               std::size_t len, float sampleRateHz,
                               float thresholdDb = 20.0f, float relBandwidth = 0.1f);

    /**
     * @brief Filter I and Q buffers in place (inner loop, integer only).
     * @return number of spurs removed (active notches), or < 0 on error.
     */
    int32_t process(int32_t *iBuffer, int32_t *qBuffer, std::size_t len);

    /// Clear all state: coefficients, w1/w2, and active spur count (reset()).
    void reset();

    /// @return number of active notch sections.
    std::size_t activeSpurs() const { return m_count; }

private:
    /// Run the biquad cascade over one channel (ch: 0 = I, 1 = Q).
    void processChannel(int32_t *buf, std::size_t len, int ch);

    BiquadCoeffs m_coeffs[KMAX];
    int64_t m_w1[2][KMAX]; ///< [channel][biquad], Q8.54, persists across buffers.
    int64_t m_w2[2][KMAX];
    std::size_t m_count;
};

} // namespace dsp

#endif // BESSEL_SPUR_REMOVAL_H
