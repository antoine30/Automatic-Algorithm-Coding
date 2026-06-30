"""
Loosely-coupled IMU + GPS fusion.

Idea
----
The IMU (accelerometer + gyroscope) runs at high frequency and drives the
*prediction* step: linear acceleration and yaw rate are treated as control
inputs that directly propagate speed and heading (classic strapdown
dead-reckoning). The GPS runs at a lower frequency and only corrects the
position in the *update* step, recalibrating the drift accumulated by the
IMU integration.

State: x = [px, py, v, psi]
    px, py : position (m)
    v      : scalar speed (m/s)
    psi    : heading angle (rad)

Control input (from the IMU): u = [a, omega]
    a     : longitudinal acceleration (m/s^2), e.g. from the accelerometer
    omega : yaw rate (rad/s), e.g. from the gyroscope

Measurement (from the GPS): z = [px, py]
"""

import numpy as np


def f_imu(x, u, dt):
    """IMU-driven dead-reckoning prediction."""
    px, py, v, psi = x
    a, omega = u

    v_new = v + a * dt
    psi_new = psi + omega * dt

    # Use the midpoint heading for a slightly more accurate integration
    psi_mid = psi + 0.5 * omega * dt
    px_new = px + v * np.cos(psi_mid) * dt
    py_new = py + v * np.sin(psi_mid) * dt

    return np.array([px_new, py_new, v_new, psi_new])


def F_jacobian_imu(x, u, dt):
    """Jacobian df/dx of the IMU-driven model."""
    px, py, v, psi = x
    a, omega = u
    psi_mid = psi + 0.5 * omega * dt

    F = np.eye(4)
    F[0, 2] = np.cos(psi_mid) * dt
    F[0, 3] = -v * np.sin(psi_mid) * dt
    F[1, 2] = np.sin(psi_mid) * dt
    F[1, 3] = v * np.cos(psi_mid) * dt
    return F


def h_gps(x):
    """GPS observation model: position only."""
    return np.array([x[0], x[1]])


def H_jacobian_gps(x):
    H = np.zeros((2, 4))
    H[0, 0] = 1.0
    H[1, 1] = 1.0
    return H


def process_noise_Q_imu(dt, std_a=0.5, std_omega=0.05):
    """
    Process noise covariance reflecting IMU sensor noise propagated through
    the dead-reckoning model.

    std_a     : accelerometer noise std (m/s^2)
    std_omega : gyroscope noise std (rad/s)
    """
    Q = np.zeros((4, 4))
    Q[2, 2] = (std_a * dt) ** 2
    Q[3, 3] = (std_omega * dt) ** 2
    # small leakage of speed/heading noise into position, conservative bound
    Q[0, 0] = 0.25 * (std_a * dt**2) ** 2
    Q[1, 1] = 0.25 * (std_a * dt**2) ** 2
    return Q


class ImuGpsEKF:
    """
    Thin wrapper around the generic EKF mechanics, specialised for the
    loosely-coupled IMU + GPS scheme:
        - call predict(dt, accel, gyro) at the IMU rate (e.g. 100 Hz)
        - call update(z_gps) whenever a new GPS fix is available (e.g. 1-10 Hz)
    """

    def __init__(self, x0, P0, R_gps, std_a=0.5, std_omega=0.05):
        self.x = np.array(x0, dtype=float)
        self.P = np.array(P0, dtype=float)
        self.R_gps = R_gps
        self.std_a = std_a
        self.std_omega = std_omega

    def predict(self, dt, accel, gyro):
        u = np.array([accel, gyro])
        Q = process_noise_Q_imu(dt, self.std_a, self.std_omega)
        F = F_jacobian_imu(self.x, u, dt)
        self.x = f_imu(self.x, u, dt)
        self.P = F @ self.P @ F.T + Q
        return self.x, self.P

    def update(self, z_gps):
        H = H_jacobian_gps(self.x)
        y = z_gps - h_gps(self.x)
        S = H @ self.P @ H.T + self.R_gps
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I = np.eye(self.P.shape[0])
        self.P = (I - K @ H) @ self.P @ (I - K @ H).T + K @ self.R_gps @ K.T
        return self.x, self.P
