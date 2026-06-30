"""
Demonstrates loosely-coupled IMU + GPS fusion: the IMU runs at high
frequency (e.g. 100 Hz) and drives the prediction step, while a low-rate,
noisy GPS (e.g. 1 Hz) corrects the accumulated drift in the update step.

Also compares against:
    - GPS-only EKF running at the GPS rate (no IMU)
to show how much the IMU improves the estimate between GPS fixes.

Usage:
    python -m vehicle_tracking.simulate_imu_gps
"""

import numpy as np
import matplotlib.pyplot as plt

from vehicle_tracking.imu_gps_fusion import ImuGpsEKF, f_imu


def simulate_true_trajectory(n_steps, dt):
    """Ground truth: straight line, then a turn, then straight again."""
    x = np.array([0.0, 0.0, 15.0, 0.0])  # px, py, v, psi
    traj = [x.copy()]
    for k in range(n_steps):
        a = 0.0
        omega = 0.25 if 600 <= k < 1200 else 0.0  # turn in the middle
        x = f_imu(x, np.array([a, omega]), dt)
        traj.append(x.copy())
    return np.array(traj)


def simulate_imu_measurements(traj, dt, std_a=0.5, std_omega=0.05, seed=1):
    """Derives noisy IMU readings (acceleration, yaw rate) from the truth."""
    rng = np.random.default_rng(seed)
    v = traj[:, 2]
    psi = traj[:, 3]
    a_true = np.gradient(v, dt)
    omega_true = np.gradient(psi, dt)
    a_meas = a_true + rng.normal(0, std_a, size=a_true.shape)
    omega_meas = omega_true + rng.normal(0, std_omega, size=omega_true.shape)
    return a_meas, omega_meas


def run_demo():
    dt_imu = 0.01          # 100 Hz IMU
    gps_period = 1.0       # 1 Hz GPS
    n_steps = 1800          # 18 s simulation
    sigma_gps = 3.0

    traj = simulate_true_trajectory(n_steps, dt_imu)
    a_meas, omega_meas = simulate_imu_measurements(traj, dt_imu)

    rng = np.random.default_rng(7)
    gps_steps = int(round(gps_period / dt_imu))

    x0 = traj[0].copy()
    P0 = np.diag([5.0, 5.0, 4.0, 0.5])
    R_gps = np.diag([sigma_gps**2, sigma_gps**2])

    fused = ImuGpsEKF(x0, P0, R_gps, std_a=0.5, std_omega=0.05)

    estimates = [fused.x.copy()]
    gps_fixes = []  # for plotting only

    for k in range(1, len(traj)):
        fused.predict(dt_imu, a_meas[k - 1], omega_meas[k - 1])

        if k % gps_steps == 0:
            z_gps = traj[k, :2] + rng.normal(0, sigma_gps, size=2)
            fused.update(z_gps)
            gps_fixes.append((k, z_gps))

        estimates.append(fused.x.copy())

    estimates = np.array(estimates)
    rmse_fused = np.sqrt(np.mean(np.sum((estimates[:, :2] - traj[:, :2])**2, axis=1)))

    gps_idx = [k for k, _ in gps_fixes]
    gps_xy = np.array([z for _, z in gps_fixes])
    rmse_gps_only = np.sqrt(np.mean(np.sum((gps_xy - traj[gps_idx, :2])**2, axis=1)))

    print(f"Position RMSE - GPS fixes only (raw)      : {rmse_gps_only:.3f} m")
    print(f"Position RMSE - IMU+GPS fused (100Hz/1Hz) : {rmse_fused:.3f} m")
    print(f"Number of IMU prediction steps: {len(traj)-1}, "
          f"number of GPS updates: {len(gps_fixes)}")

    return traj, estimates, gps_idx, gps_xy


def plot_results(traj, estimates, gps_idx, gps_xy, out_path="imu_gps_fusion.png"):
    plt.figure(figsize=(8, 6))
    plt.plot(traj[:, 0], traj[:, 1], 'k-', linewidth=2, label="Ground-truth trajectory")
    plt.scatter(gps_xy[:, 0], gps_xy[:, 1], s=20, c='gray', alpha=0.6,
                label="GPS fixes (1 Hz, noisy)")
    plt.plot(estimates[:, 0], estimates[:, 1], 'g--', linewidth=1.2,
              label="Fused IMU+GPS estimate (100 Hz)")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Loosely-coupled IMU + GPS fusion (EKF)")
    plt.legend()
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Plot saved to {out_path}")


if __name__ == "__main__":
    traj, estimates, gps_idx, gps_xy = run_demo()
    plot_results(traj, estimates, gps_idx, gps_xy)
