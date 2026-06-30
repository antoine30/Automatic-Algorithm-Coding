"""
Simulates a vehicle trajectory following a CTRV model (straight line then a
turn), generates noisy GPS measurements, and estimates the trajectory with
an EKF and a UKF. Produces a comparison plot (trajectory.png) and prints the
RMSE of each filter.

Usage:
    python -m vehicle_tracking.simulate
"""

import numpy as np
import matplotlib.pyplot as plt

from vehicle_tracking.models import (
    f_ctrv, F_jacobian_ctrv, h_position, H_jacobian_position, process_noise_Q,
)
from vehicle_tracking.ekf import ExtendedKalmanFilter
from vehicle_tracking.ukf import UnscentedKalmanFilter


def simulate_true_trajectory(n_steps=200, dt=0.1):
    """Generates a ground-truth trajectory: straight line then a constant turn."""
    x = np.array([0.0, 0.0, 15.0, 0.0, 0.0])  # px,py,v,psi,psi_dot
    traj = [x.copy()]
    for k in range(n_steps):
        if 60 <= k < 120:
            x[4] = 0.25  # start turning
        else:
            x[4] = 0.0
        x = f_ctrv(x, dt)
        traj.append(x.copy())
    return np.array(traj)


def generate_measurements(traj, sigma_gps=3.0, seed=42):
    rng = np.random.default_rng(seed)
    z = traj[:, :2] + rng.normal(0, sigma_gps, size=(traj.shape[0], 2))
    return z


def run_filters():
    dt = 0.1
    sigma_gps = 3.0

    traj = simulate_true_trajectory(n_steps=200, dt=dt)
    measurements = generate_measurements(traj, sigma_gps=sigma_gps)

    R = np.diag([sigma_gps**2, sigma_gps**2])
    x0 = np.array([0.0, 0.0, 15.0, 0.0, 0.0])
    P0 = np.diag([5.0, 5.0, 4.0, 0.5, 0.2])

    Qfun = lambda dt_: process_noise_Q(dt_, std_a=2.0, std_psidd=0.3)

    ekf = ExtendedKalmanFilter(f_ctrv, F_jacobian_ctrv, h_position,
                                H_jacobian_position, Qfun, R, x0, P0)
    ukf = UnscentedKalmanFilter(f_ctrv, h_position, Qfun, R, x0, P0)

    ekf_estimates = [ekf.x.copy()]
    ukf_estimates = [ukf.x.copy()]

    for k in range(1, len(traj)):
        ekf.predict(dt)
        ekf.update(measurements[k])
        ekf_estimates.append(ekf.x.copy())

        ukf.predict(dt)
        ukf.update(measurements[k])
        ukf_estimates.append(ukf.x.copy())

    ekf_estimates = np.array(ekf_estimates)
    ukf_estimates = np.array(ukf_estimates)

    rmse_ekf = np.sqrt(np.mean(np.sum((ekf_estimates[:, :2] - traj[:, :2])**2, axis=1)))
    rmse_ukf = np.sqrt(np.mean(np.sum((ukf_estimates[:, :2] - traj[:, :2])**2, axis=1)))
    rmse_mes = np.sqrt(np.mean(np.sum((measurements - traj[:, :2])**2, axis=1)))

    print(f"Position RMSE - Raw measurements : {rmse_mes:.3f} m")
    print(f"Position RMSE - EKF              : {rmse_ekf:.3f} m")
    print(f"Position RMSE - UKF              : {rmse_ukf:.3f} m")

    return traj, measurements, ekf_estimates, ukf_estimates


def plot_results(traj, measurements, ekf_estimates, ukf_estimates, out_path="trajectory.png"):
    plt.figure(figsize=(8, 6))
    plt.plot(traj[:, 0], traj[:, 1], 'k-', linewidth=2, label="Ground-truth trajectory")
    plt.scatter(measurements[:, 0], measurements[:, 1], s=8, c='gray',
                alpha=0.5, label="Noisy GPS measurements")
    plt.plot(ekf_estimates[:, 0], ekf_estimates[:, 1], 'b--', label="EKF estimate")
    plt.plot(ukf_estimates[:, 0], ukf_estimates[:, 1], 'r--', label="UKF estimate")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Vehicle trajectory estimation (CTRV model)")
    plt.legend()
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Plot saved to {out_path}")


if __name__ == "__main__":
    traj, measurements, ekf_estimates, ukf_estimates = run_filters()
    plot_results(traj, measurements, ekf_estimates, ukf_estimates)
