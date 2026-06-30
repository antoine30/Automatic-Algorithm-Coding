"""
Generic Extended Kalman Filter (EKF).

Reusable for any differentiable pair (f, h), given the propagation
functions and their Jacobians.
"""

import numpy as np


class ExtendedKalmanFilter:
    def __init__(self, f, F_jac, h, H_jac, Q, R, x0, P0):
        """
        f      : state transition function x_k = f(x_{k-1}, dt)
        F_jac  : Jacobian of f, F = F_jac(x, dt)
        h      : observation function z = h(x)
        H_jac  : Jacobian of h, H = H_jac(x)
        Q      : process noise covariance (can depend on dt, see process_noise_Q)
        R      : measurement noise covariance
        x0, P0 : initial state and covariance
        """
        self.f = f
        self.F_jac = F_jac
        self.h = h
        self.H_jac = H_jac
        self.Q = Q
        self.R = R
        self.x = np.array(x0, dtype=float)
        self.P = np.array(P0, dtype=float)

    def predict(self, dt, Q=None):
        Q = self.Q(dt) if callable(self.Q) else (Q if Q is not None else self.Q)
        F = self.F_jac(self.x, dt)
        self.x = self.f(self.x, dt)
        self.P = F @ self.P @ F.T + Q
        return self.x, self.P

    def update(self, z, H_jac=None, h=None, R=None):
        """
        Standard update step. H_jac/h/R can be overridden per call, which is
        useful when fusing measurements of different types (e.g. GPS vs IMU)
        through the same filter instance.
        """
        H_jac = H_jac or self.H_jac
        h = h or self.h
        R = R if R is not None else self.R

        H = H_jac(self.x)
        y = z - h(self.x)
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I = np.eye(self.P.shape[0])
        # Joseph form: more numerically stable than (I-KH)P
        self.P = (I - K @ H) @ self.P @ (I - K @ H).T + K @ R @ K.T
        return self.x, self.P
