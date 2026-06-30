"""
CTRV (Constant Turn Rate and Velocity) model for vehicle tracking.

State: x = [px, py, v, psi, psi_dot]
    px, py   : position (m)
    v        : scalar speed (m/s)
    psi      : heading angle (rad)
    psi_dot  : turn rate (rad/s)

Measurement: z = [px, py]  (default, e.g. GPS)
"""

import numpy as np


def f_ctrv(x, dt):
    """Non-linear propagation of the CTRV state over a time step dt."""
    px, py, v, psi, psi_dot = x

    if abs(psi_dot) > 1e-5:
        px_new = px + (v / psi_dot) * (np.sin(psi + psi_dot * dt) - np.sin(psi))
        py_new = py + (v / psi_dot) * (-np.cos(psi + psi_dot * dt) + np.cos(psi))
    else:
        # near-zero turn rate -> straight-line motion
        px_new = px + v * np.cos(psi) * dt
        py_new = py + v * np.sin(psi) * dt

    v_new = v
    psi_new = psi + psi_dot * dt
    psi_dot_new = psi_dot

    return np.array([px_new, py_new, v_new, psi_new, psi_dot_new])


def F_jacobian_ctrv(x, dt):
    """Jacobian df/dx of the CTRV model, required for the EKF."""
    px, py, v, psi, psi_dot = x
    F = np.eye(5)

    if abs(psi_dot) > 1e-5:
        sin_p = np.sin(psi)
        cos_p = np.cos(psi)
        sin_pd = np.sin(psi + psi_dot * dt)
        cos_pd = np.cos(psi + psi_dot * dt)

        F[0, 2] = (sin_pd - sin_p) / psi_dot
        F[0, 3] = (v / psi_dot) * (cos_pd - cos_p)
        F[0, 4] = (v * dt * cos_pd) / psi_dot - (v * (sin_pd - sin_p)) / psi_dot**2

        F[1, 2] = (-cos_pd + cos_p) / psi_dot
        F[1, 3] = (v / psi_dot) * (sin_pd - sin_p)
        F[1, 4] = (v * dt * sin_pd) / psi_dot - (v * (-cos_pd + cos_p)) / psi_dot**2
    else:
        F[0, 2] = np.cos(psi) * dt
        F[0, 3] = -v * np.sin(psi) * dt
        F[1, 2] = np.sin(psi) * dt
        F[1, 3] = v * np.cos(psi) * dt

    F[3, 4] = dt
    return F


def h_position(x):
    """Observation model: only the position is measured (e.g. GPS)."""
    return np.array([x[0], x[1]])


def H_jacobian_position(x):
    """Jacobian dh/dx for a pure position measurement (linear here)."""
    H = np.zeros((2, 5))
    H[0, 0] = 1.0
    H[1, 1] = 1.0
    return H


def process_noise_Q(dt, std_a=2.0, std_psidd=0.3):
    """
    Process noise covariance for the CTRV model.

    std_a     : standard deviation of the longitudinal acceleration noise (m/s^2)
    std_psidd : standard deviation of the angular acceleration noise (rad/s^2)

    Simplified block-wise construction (common discrete approximation for
    CTRV, see Schubert et al.).
    """
    Q = np.zeros((5, 5))

    Q[0, 0] = 0.25 * dt**4 * std_a**2
    Q[0, 2] = 0.5 * dt**3 * std_a**2
    Q[2, 0] = Q[0, 2]
    Q[2, 2] = dt**2 * std_a**2

    Q[1, 1] = 0.25 * dt**4 * std_a**2
    Q[1, 2] = 0.5 * dt**3 * std_a**2
    Q[2, 1] = Q[1, 2]

    Q[3, 3] = 0.25 * dt**4 * std_psidd**2
    Q[3, 4] = 0.5 * dt**3 * std_psidd**2
    Q[4, 3] = Q[3, 4]
    Q[4, 4] = dt**2 * std_psidd**2

    return Q
