/**
 * @file PhaseCompute.cpp
 * @brief LLR_ALG_003 — CORDIC atan2 implementation.
 */

#include "algorithms/PhaseCompute.h"

#include <cmath>

namespace dsp
{

PhaseCompute::PhaseCompute() : m_angle{}, m_comp(0), m_initialized(false)
{
    init();
}

void PhaseCompute::init()
{
    // Group 1: angle[i] = round(atan(2^-i) × 2^27). Float, init only.
    double k = 1.0;
    for (int i = 0; i < arith::CORDIC_ITERS; ++i)
    {
        const double a = std::atan(std::ldexp(1.0, -i)); // atan(2^-i)
        m_angle[i] = static_cast<int32_t>(
            std::llround(a * static_cast<double>(arith::Q_SCALE)));
        // Group 2: accumulate CORDIC gain K = ∏ sqrt(1 + 2^-2i).
        k *= std::sqrt(1.0 + std::ldexp(1.0, -2 * i));
    }
    // CORDIC_COMP = (1/K) × 2^27 in Q4.27.
    m_comp = static_cast<int32_t>(
        std::llround((1.0 / k) * static_cast<double>(arith::Q_SCALE)));
    m_initialized = true;
}

int32_t PhaseCompute::computePhase(int32_t I, int32_t Q) const
{
    // Edge case: no signal → phase 0 (no crash).
    if (I == 0 && Q == 0)
    {
        return 0;
    }

    int32_t x = I;
    int32_t y = Q;
    int32_t z = 0;

    // Quadrant pre-rotation so that x >= 0 (CORDIC converges for |angle| ≤ π/2).
    if (x < 0)
    {
        const int32_t ox = x;
        const int32_t oy = y;
        if (y >= 0)
        {
            // Quadrant II: rotate vector by -90°, add +π/2 back into z.
            x = oy;
            y = -ox;
            z = arith::HALF_PI_Q427;
        }
        else
        {
            // Quadrant III: rotate vector by +90°, add -π/2 back into z.
            x = -oy;
            y = ox;
            z = -arith::HALF_PI_Q427;
        }
    }

    // Group 3: 27 CORDIC vectoring iterations, driving y → 0. No saturation
    // between iterations.
    for (int i = 0; i < arith::CORDIC_ITERS; ++i)
    {
        const int32_t xi = x;
        const int32_t yi = y;
        if (yi >= 0)
        {
            x = xi + (yi >> i);
            y = yi - (xi >> i);
            z = z + m_angle[i];
        }
        else
        {
            x = xi - (yi >> i);
            y = yi + (xi >> i);
            z = z - m_angle[i];
        }
    }

    // Group 4: single saturation after all iterations.
    return arith::saturate_i32(z);
}

void PhaseCompute::process(const int32_t *iBuffer, const int32_t *qBuffer,
                           int32_t *phaseBuffer, std::size_t len) const
{
    for (std::size_t n = 0; n < len; ++n)
    {
        phaseBuffer[n] = computePhase(iBuffer[n], qBuffer[n]);
    }
}

} // namespace dsp
