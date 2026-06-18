/**
 * @file BesselSpurRemoval.cpp
 * @brief LLR_ALG_002 — Implementation of the Bessel notch cascade.
 */

#include "algorithms/BesselSpurRemoval.h"

#include "config/arithmetic_target.h"

#include <cmath>

namespace dsp
{

namespace
{
/// Convert a float coefficient to int32 Q4.27 (Group 1 step 1.2/1.3, PDF eq.9).
int32_t toQ427(double c)
{
    return arith::saturate_i32(static_cast<int64_t>(std::llround(c * static_cast<double>(arith::Q_SCALE))));
}
/// Practical cascade-gain budget (PDF eq.15).
constexpr double kGainBudget = 8.0;
} // namespace

BesselSpurRemoval::BesselSpurRemoval() : m_coeffs{}, m_w1{}, m_w2{}, m_count(0)
{
}

int32_t BesselSpurRemoval::configure(const float *spurHz, std::size_t count,
                                     float sampleRateHz, float relBandwidth)
{
    if (sampleRateHz <= 0.0f)
    {
        return -1;
    }
    if (count > KMAX)
    {
        count = KMAX; // PDF §4.3 step 5: retain at most KMAX.
    }

    double gainTotal = 1.0;
    BiquadCoeffs designed[KMAX] = {};

    for (std::size_t k = 0; k < count; ++k)
    {
        // Normalized notch frequency ω0 = 2π f / fs (PDF §5.2).
        const double w0 = 2.0 * 3.14159265358979323846 *
                          static_cast<double>(spurHz[k]) / static_cast<double>(sampleRateHz);
        if (w0 <= 0.0 || w0 >= 3.14159265358979323846)
        {
            return -2; // spur outside (0, Nyquist): cannot design a notch.
        }

        const double sinw0 = std::sin(w0);
        const double cosw0 = std::cos(w0);
        // α per PDF eq.3 (written literally; sin(w0) cancels with ω0/sin(w0)).
        const double alpha =
            sinw0 * std::sinh((std::log(2.0) / 2.0) * relBandwidth) * (w0 / sinw0);
        const double norm = 1.0 / (1.0 + alpha);

        const double b0 = norm;             // eq.4
        const double b1 = -2.0 * cosw0 * norm; // eq.5
        const double b2 = norm;             // eq.6
        const double a1 = -2.0 * cosw0 * norm; // eq.7
        const double a2 = (1.0 - alpha) * norm; // eq.8

        // Cascade gain bound Gk ≤ |b0|+|b1|+|b2| (PDF eq.13).
        gainTotal *= (std::fabs(b0) + std::fabs(b1) + std::fabs(b2));

        designed[k].b0 = toQ427(b0);
        designed[k].b1 = toQ427(b1);
        designed[k].b2 = toQ427(b2);
        designed[k].a1 = toQ427(a1);
        designed[k].a2 = toQ427(a2);
    }

    // Verify gain budget once at init (PDF §8.2 eq.15) — never at runtime.
    if (gainTotal >= kGainBudget)
    {
        return -3; // design must be revised (reduce bandwidth or stages).
    }

    for (std::size_t k = 0; k < count; ++k)
    {
        m_coeffs[k] = designed[k];
    }
    m_count = count;
    // Fresh design starts from zero state.
    for (int ch = 0; ch < 2; ++ch)
    {
        for (std::size_t k = 0; k < KMAX; ++k)
        {
            m_w1[ch][k] = 0;
            m_w2[ch][k] = 0;
        }
    }
    return static_cast<int32_t>(m_count);
}

int32_t BesselSpurRemoval::detectAndConfigure(const int32_t *iBuffer,
                                              const int32_t *qBuffer, std::size_t len,
                                              float sampleRateHz, float thresholdDb,
                                              float relBandwidth)
{
    // Detection runs in float, once per buffer (PDF §4.2) — not the inner loop.
    constexpr std::size_t kMaxN = 256;
    if (iBuffer == nullptr || qBuffer == nullptr || len < 8 || len > kMaxN)
    {
        return -1;
    }

    const double TWO_PI = 2.0 * 3.14159265358979323846;
    const std::size_t N = len;

    // §4.3 step 1: magnitude spectrum of the complex signal c[n] = I + jQ.
    double powDb[kMaxN];
    for (std::size_t k = 0; k < N; ++k)
    {
        double re = 0.0, im = 0.0;
        for (std::size_t n = 0; n < N; ++n)
        {
            const double ang = -TWO_PI * static_cast<double>(k) * static_cast<double>(n) /
                               static_cast<double>(N);
            const double c = std::cos(ang);
            const double s = std::sin(ang);
            const double ire = static_cast<double>(iBuffer[n]);
            const double iim = static_cast<double>(qBuffer[n]);
            re += ire * c - iim * s;
            im += ire * s + iim * c;
        }
        powDb[k] = 10.0 * std::log10(re * re + im * im + 1.0);
    }

    // §4.3 step 2: noise-floor estimate = median of the power spectrum (robust).
    double sorted[kMaxN];
    for (std::size_t k = 0; k < N; ++k)
    {
        sorted[k] = powDb[k];
    }
    for (std::size_t a = 0; a < N; ++a) // small N: simple insertion sort
    {
        for (std::size_t b = a + 1; b < N; ++b)
        {
            if (sorted[b] < sorted[a])
            {
                double t = sorted[a];
                sorted[a] = sorted[b];
                sorted[b] = t;
            }
        }
    }
    const double floorDb = sorted[N / 2];

    // §4.3 steps 3–5: local maxima above floor + threshold; keep KMAX strongest.
    float spurHz[KMAX] = {};
    double spurPow[KMAX] = {};
    std::size_t found = 0;
    for (std::size_t k = 1; k < N - 1; ++k)
    {
        if (k == N / 2)
        {
            continue; // skip Nyquist
        }
        if (powDb[k] <= floorDb + static_cast<double>(thresholdDb))
        {
            continue;
        }
        if (powDb[k] < powDb[k - 1] || powDb[k] < powDb[k + 1])
        {
            continue; // not a local maximum
        }
        // Bin → frequency (two-sided); use magnitude for the real notch.
        double f = (k <= N / 2) ? static_cast<double>(k)
                                : static_cast<double>(k) - static_cast<double>(N);
        f = std::fabs(f) * static_cast<double>(sampleRateHz) / static_cast<double>(N);
        if (f <= 0.0)
        {
            continue;
        }
        // Insert into the strongest-KMAX table (replace weakest if full).
        if (found < KMAX)
        {
            spurHz[found] = static_cast<float>(f);
            spurPow[found] = powDb[k];
            ++found;
        }
        else
        {
            std::size_t weakest = 0;
            for (std::size_t j = 1; j < KMAX; ++j)
            {
                if (spurPow[j] < spurPow[weakest])
                {
                    weakest = j;
                }
            }
            if (powDb[k] > spurPow[weakest])
            {
                spurHz[weakest] = static_cast<float>(f);
                spurPow[weakest] = powDb[k];
            }
        }
    }

    if (found == 0)
    {
        // No spur above threshold: clear filters, become a pass-through.
        reset();
        return 0;
    }
    return configure(spurHz, found, sampleRateHz, relBandwidth);
}

void BesselSpurRemoval::processChannel(int32_t *buf, std::size_t len, int ch)
{
    for (std::size_t n = 0; n < len; ++n)
    {
        int32_t x = buf[n]; // int32 Q4.27
        for (std::size_t k = 0; k < m_count; ++k)
        {
            const BiquadCoeffs &c = m_coeffs[k];

            // Group 2: y[n] = b0·x[n] + w1   (state held as Q8.54).
            int64_t acc = static_cast<int64_t>(c.b0) * x + m_w1[ch][k]; // Q8.54
            int32_t y = arith::saturate_i32(acc >> arith::MULTIPLY_SHIFT); // Q4.27

            // Group 3: w1 = b1·x − a1·y + w2   (Q8.54, not renormalized).
            m_w1[ch][k] = static_cast<int64_t>(c.b1) * x -
                          static_cast<int64_t>(c.a1) * y + m_w2[ch][k];

            // Group 4: w2 = b2·x − a2·y   (Q8.54).
            m_w2[ch][k] = static_cast<int64_t>(c.b2) * x -
                          static_cast<int64_t>(c.a2) * y;

            // Group 5: output of biquad k feeds biquad k+1.
            x = y;
        }
        buf[n] = x;
    }
}

int32_t BesselSpurRemoval::process(int32_t *iBuffer, int32_t *qBuffer, std::size_t len)
{
    if (iBuffer == nullptr || qBuffer == nullptr)
    {
        return -1;
    }
    // I and Q processed independently with separate state machines (PDF §11.8).
    processChannel(iBuffer, len, 0);
    processChannel(qBuffer, len, 1);
    return static_cast<int32_t>(m_count);
}

void BesselSpurRemoval::reset()
{
    for (std::size_t k = 0; k < KMAX; ++k)
    {
        m_coeffs[k] = BiquadCoeffs{};
        for (int ch = 0; ch < 2; ++ch)
        {
            m_w1[ch][k] = 0;
            m_w2[ch][k] = 0;
        }
    }
    m_count = 0;
}

} // namespace dsp
