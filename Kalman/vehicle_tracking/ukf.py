"""
Generic Unscented Kalman Filter (UKF), for comparison with the EKF on the
CTRV model (no need to compute Jacobians).
"""

import numpy as np


class UnscentedKalmanFilter:
    def __init__(self, f, h, Q, R, x0, P0, alpha=1e-3, beta=2.0, kappa=0.0):
        self.f = f
        self.h = h
        self.Q = Q
        self.R = R
        self.x = np.array(x0, dtype=float)
        self.P = np.array(P0, dtype=float)
        self.n = len(x0)

        n = self.n
        self.lam = alpha**2 * (n + kappa) - n
        self.Wm = np.full(2 * n + 1, 1.0 / (2 * (n + self.lam)))
        self.Wc = self.Wm.copy()
        self.Wm[0] = self.lam / (n + self.lam)
        self.Wc[0] = self.lam / (n + self.lam) + (1 - alpha**2 + beta)

    def _sigma_points(self, x, P):
        n, lam = self.n, self.lam
        P = (P + P.T) / 2.0  # enforce symmetry before Cholesky
        S = np.linalg.cholesky((n + lam) * P)
        pts = [x.copy()]
        for i in range(n):
            pts.append(x + S[:, i])
        for i in range(n):
            pts.append(x - S[:, i])
        return np.array(pts)

    def predict(self, dt, Q=None):
        Q = self.Q(dt) if callable(self.Q) else (Q if Q is not None else self.Q)
        pts = self._sigma_points(self.x, self.P)
        pts_pred = np.array([self.f(p, dt) for p in pts])

        x_pred = self.Wm @ pts_pred
        # proper handling of angles (psi is index 3 in the CTRV model)
        P_pred = Q.copy()
        for i in range(len(pts_pred)):
            d = pts_pred[i] - x_pred
            if d.shape[0] > 3:
                d[3] = _normalize_angle(d[3])
            P_pred += self.Wc[i] * np.outer(d, d)

        self.x, self.P = x_pred, P_pred
        self._pts_pred = pts_pred
        return self.x, self.P

    def update(self, z):
        pts_pred = self._pts_pred
        Z = np.array([self.h(p) for p in pts_pred])
        z_pred = self.Wm @ Z

        m = len(z)
        Pzz = self.R.copy()
        Pxz = np.zeros((self.n, m))
        for i in range(len(pts_pred)):
            dz = Z[i] - z_pred
            dx = pts_pred[i] - self.x
            if dx.shape[0] > 3:
                dx[3] = _normalize_angle(dx[3])
            Pzz += self.Wc[i] * np.outer(dz, dz)
            Pxz += self.Wc[i] * np.outer(dx, dz)

        K = Pxz @ np.linalg.inv(Pzz)
        innovation = z - z_pred
        self.x = self.x + K @ innovation
        self.P = self.P - K @ Pzz @ K.T
        return self.x, self.P


def _normalize_angle(angle):
    """Wraps an angle into the [-pi, pi] interval."""
    return (angle + np.pi) % (2 * np.pi) - np.pi
