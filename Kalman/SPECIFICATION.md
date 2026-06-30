# Technical Specification — Implemented Kalman Filters and IMU/GPS Fusion

This document specifies, precisely and exhaustively, the mathematical models,
state definitions, equations and tuning parameters used by every filter
implemented in this repository. It is meant as a reference for anyone
extending, auditing, or re-implementing this code in another language or
framework.

---

## 1. Notation

| Symbol | Meaning |
|---|---|
| `x_k` | state vector at time step `k` |
| `x_k^-` | a priori (predicted) state, before measurement update |
| `P_k` | state error covariance matrix |
| `P_k^-` | a priori covariance |
| `F_k` | state transition Jacobian |
| `H_k` | observation Jacobian |
| `Q_k` | process noise covariance |
| `R_k` | measurement noise covariance |
| `K_k` | Kalman gain |
| `z_k` | measurement vector |
| `y_k` | innovation, `y_k = z_k - h(x_k^-)` |
| `dt` | time step (s) |

All filters follow the standard two-step recursive scheme:

```
Predict :  x_k^- = f(x_{k-1}, u_{k-1}, dt)         P_k^- = F_k P_{k-1} F_k^T + Q_k
Update  :  K_k = P_k^- H_k^T (H_k P_k^- H_k^T + R_k)^-1
           x_k = x_k^- + K_k (z_k - h(x_k^-))
           P_k = (I - K_k H_k) P_k^- (I - K_k H_k)^T + K_k R_k K_k^T   (Joseph form)
```

---

## 2. CTRV motion model (`vehicle_tracking/models.py`)

### 2.1 State definition

```
x = [px, py, v, psi, psi_dot]^T   ∈ R^5
```

| Component | Unit | Description |
|---|---|---|
| `px, py` | m | 2D Cartesian position |
| `v` | m/s | scalar (longitudinal) speed |
| `psi` | rad | heading angle |
| `psi_dot` | rad/s | yaw rate (turn rate), assumed constant between steps |

### 2.2 Process model `f(x, dt)`

For `|psi_dot| > 1e-5` (turning):

```
px_{k} = px_{k-1} + (v/psi_dot) * [sin(psi_{k-1} + psi_dot*dt) - sin(psi_{k-1})]
py_{k} = py_{k-1} + (v/psi_dot) * [-cos(psi_{k-1} + psi_dot*dt) + cos(psi_{k-1})]
v_k       = v_{k-1}
psi_k     = psi_{k-1} + psi_dot*dt
psi_dot_k = psi_dot_{k-1}
```

For `|psi_dot| <= 1e-5` (straight line, singularity-free fallback):

```
px_k = px_{k-1} + v*cos(psi_{k-1})*dt
py_k = py_{k-1} + v*sin(psi_{k-1})*dt
```

This is an **exact, closed-form integration** of the constant turn-rate
kinematics over `dt` — not a first-order Euler approximation — which is why
CTRV remains accurate even at low update rates (e.g. 10 Hz GPS).

### 2.3 Jacobian `F = df/dx`

Computed in closed form in `F_jacobian_ctrv`, with the same case split
(turning / straight) used to avoid the `1/psi_dot` singularity. Required by
the EKF only; the UKF does not use it.

### 2.4 Observation model

Position-only (GPS):

```
h(x) = [px, py]^T          H = [[1,0,0,0,0],
                                 [0,1,0,0,0]]
```

`H` is linear (constant), so its Jacobian is trivial regardless of the
filter used.

### 2.5 Process noise `Q(dt)`

Parametrised by two physical noise sources: longitudinal acceleration noise
`std_a` (m/s²) and angular acceleration noise `std_psidd` (rad/s²), injected
through a standard discretised white-noise-acceleration block structure:

```
Q[px,px] = Q[py,py] = 0.25 * dt^4 * std_a^2
Q[px,v]  = Q[py,v]  = 0.5  * dt^3 * std_a^2     (symmetric)
Q[v,v]              = dt^2 * std_a^2
Q[psi,psi]          = 0.25 * dt^4 * std_psidd^2
Q[psi,psi_dot]      = 0.5  * dt^3 * std_psidd^2  (symmetric)
Q[psi_dot,psi_dot]  = dt^2 * std_psidd^2
```

Default tuning used in `simulate.py`: `std_a = 2.0 m/s²`, `std_psidd = 0.3 rad/s²`.

---

## 3. Extended Kalman Filter (`vehicle_tracking/ekf.py`)

Generic implementation, parametrised by `(f, F_jac, h, H_jac, Q, R)`.

- **Predict**: propagates the mean through the *exact* non-linear `f`, and
  the covariance through the *linearised* `F_jac` evaluated at the current
  estimate (first-order Taylor expansion).
- **Update**: linearises `h` via `H_jac` at the predicted state, computes
  the innovation `y_k = z_k - h(x_k^-)` using the *exact* `h` (not its
  linearisation), and applies the standard gain.
- **Covariance update**: implemented in **Joseph form**
  `P_k = (I-K_kH_k)P_k^-(I-K_kH_k)^T + K_kR_kK_k^T` rather than the simpler
  `(I-K_kH_k)P_k^-`, for better numerical robustness (guarantees positive
  semi-definiteness even under floating-point rounding errors).
- The `update()` method accepts optional per-call overrides of `H_jac`,
  `h`, and `R`, allowing a single filter instance to fuse heterogeneous
  measurement types (e.g. GPS position update vs. a future heading-only
  update from a compass) without re-instantiation.

**Complexity**: `O(n^3)` per step (matrix inversion of size `m x m`,
`m` = measurement dimension), `n` = state dimension.

---

## 4. Unscented Kalman Filter (`vehicle_tracking/ukf.py`)

Generic implementation, parametrised by `(f, h, Q, R)` — no Jacobians
required.

### 4.1 Sigma points

For state dimension `n`, `2n+1` sigma points are generated:

```
X^(0) = x
X^(i) = x + [sqrt((n+lambda) P)]_i        i = 1..n
X^(i) = x - [sqrt((n+lambda) P)]_{i-n}    i = n+1..2n
```

`sqrt(.)` is the Cholesky factor. `P` is symmetrised
(`P = (P + P^T)/2`) before the Cholesky decomposition to guard against
floating-point asymmetry accumulated over iterations.

### 4.2 Scaling and weights

```
lambda = alpha^2 (n + kappa) - n
Wm[0]  = lambda / (n + lambda)
Wc[0]  = lambda / (n + lambda) + (1 - alpha^2 + beta)
Wm[i]  = Wc[i] = 1 / (2(n+lambda))     for i = 1..2n
```

Default parameters: `alpha = 1e-3`, `beta = 2.0` (optimal for Gaussian
priors), `kappa = 0.0`.

### 4.3 Angle handling

Since the CTRV state includes a heading angle `psi` at index 3, all
sigma-point residuals `(X^(i) - x_mean)` used in covariance computations
have their 4th component wrapped into `[-pi, pi]` via `_normalize_angle`
before being used in outer products. This prevents covariance corruption
when the heading crosses the `±pi` discontinuity (e.g. a vehicle making a
U-turn).

### 4.4 Predict / Update

- **Predict**: propagate all `2n+1` sigma points through the *exact*
  non-linear `f`, recombine with weights `Wm`/`Wc` to obtain `x_k^-`,
  `P_k^-`. No Jacobian is computed anywhere.
- **Update**: propagate the *predicted* sigma points (not re-drawn) through
  `h`, recombine to get the predicted measurement `z_pred`, the innovation
  covariance `Pzz`, and the cross-covariance `Pxz`. Gain
  `K = Pxz Pzz^-1`, standard linear-form update of mean and covariance.

**Complexity**: `O(n^3)` per step (Cholesky decomposition + `2n+1`
propagations), comparable to the EKF, with no need to derive or implement
Jacobians.

---

## 5. Loosely-coupled IMU + GPS fusion (`vehicle_tracking/imu_gps_fusion.py`)

### 5.1 Architecture

```
IMU (accel, gyro)  --100 Hz-->  predict()  --\
                                              >--  fused state estimate (100 Hz)
GPS (px, py)       ---1 Hz--->  update()   --/
```

This is a **loosely-coupled** scheme: the GPS receiver internally computes
a position fix (via its own navigation solution) before that fix is fed
into the filter as a measurement. (A *tightly-coupled* scheme would instead
feed raw pseudorange/Doppler measurements directly into `update()`; this is
not implemented here but the same EKF machinery applies — see Section 7.)

### 5.2 State definition

```
x = [px, py, v, psi]^T   ∈ R^4
```

Note: unlike the CTRV model (Section 2), `psi_dot` is **not** part of the
state here — it is supplied externally as a control input from the
gyroscope at every prediction step, since the IMU measures it directly.

### 5.3 Control input (from the IMU)

```
u = [a, omega]^T
```

| Component | Unit | Source |
|---|---|---|
| `a` | m/s² | accelerometer (longitudinal acceleration) |
| `omega` | rad/s | gyroscope (yaw rate) |

### 5.4 Process model `f_imu(x, u, dt)`

```
v_k       = v_{k-1} + a*dt
psi_k     = psi_{k-1} + omega*dt
psi_mid   = psi_{k-1} + 0.5*omega*dt          (midpoint heading)
px_k      = px_{k-1} + v_{k-1}*cos(psi_mid)*dt
py_k      = py_{k-1} + v_{k-1}*sin(psi_mid)*dt
```

The midpoint heading `psi_mid` is used (instead of `psi_{k-1}` or `psi_k`)
for position integration, which is a second-order-accurate approximation of
the true curved path within a single IMU step — important since `dt` for
the IMU is typically small (10 ms) but accumulates over many steps between
GPS corrections.

### 5.5 Jacobian `F = df/dx` (`F_jacobian_imu`)

```
F = | 1  0  cos(psi_mid)*dt   -v*sin(psi_mid)*dt |
    | 0  1  sin(psi_mid)*dt    v*cos(psi_mid)*dt |
    | 0  0  1                  0                 |
    | 0  0  0                  1                 |
```

Note that `u = [a, omega]` are treated as known, noise-free deterministic
inputs for the purpose of linearisation (their uncertainty is instead
folded directly into `Q`, see 5.7) — this is the standard simplification
used in strapdown INS error models.

### 5.6 Observation model (GPS)

Identical structure to Section 2.4:

```
h_gps(x) = [px, py]^T      H_jacobian_gps = [[1,0,0,0],[0,1,0,0]]
```

### 5.7 Process noise `process_noise_Q_imu(dt, std_a, std_omega)`

```
Q[v,v]             = (std_a * dt)^2
Q[psi,psi]         = (std_omega * dt)^2
Q[px,px] = Q[py,py] = 0.25 * (std_a * dt^2)^2     (conservative leakage bound)
```

Default tuning used in `simulate_imu_gps.py`: `std_a = 0.5 m/s²`,
`std_omega = 0.05 rad/s` — representative of a low-cost MEMS IMU.

`std_a` and `std_omega` should, in practice, be set from the IMU
datasheet's noise density figures (converted to the discrete-time
equivalent at the IMU's `dt`), not tuned empirically — unlike `Q` in the
GPS-only CTRV model, where some empirical tuning is generally unavoidable.

### 5.8 `ImuGpsEKF` class — call pattern

```python
fused = ImuGpsEKF(x0, P0, R_gps, std_a, std_omega)

# at the IMU rate (e.g. every 10 ms):
fused.predict(dt_imu, accel_reading, gyro_reading)

# at the GPS rate (e.g. every 1 s), whenever a fix is available:
fused.update(gps_position)
```

`predict()` and `update()` are decoupled on purpose: the caller is
responsible for invoking `predict()` at every IMU sample and `update()`
only when a GPS fix arrives, which is what makes the filter run
continuously at IMU rate while only being corrected intermittently.

### 5.9 Demonstrated performance (`simulate_imu_gps.py`)

Simulation setup: 18 s trajectory (straight line, 10 s turn, straight
line), IMU at 100 Hz (`dt = 0.01 s`), GPS at 1 Hz, `sigma_gps = 3.0 m`.

| Estimate | Position RMSE |
|---|---|
| Raw GPS fixes (1 Hz) | ≈ 3.96 m |
| Fused IMU+GPS (100 Hz) | ≈ 3.19 m |

Beyond the RMSE improvement, the key practical benefit is that the fused
estimate is available at **100 Hz** (every IMU sample) rather than only at
**1 Hz** (GPS rate) — essential for any downstream control loop (e.g.
path-following, collision avoidance) that cannot wait for the next GPS fix.

---

## 6. Summary comparison

| | CTRV + EKF | CTRV + UKF | IMU+GPS (`ImuGpsEKF`) |
|---|---|---|---|
| State dimension | 5 | 5 | 4 |
| Jacobians required | yes (`F`, `H`) | no | yes (`F`; `H` is linear) |
| Update rate | measurement rate | measurement rate | IMU rate (predict), GPS rate (update) |
| Typical use case | GPS-only tracking | GPS-only tracking, stronger non-linearity | dead-reckoning between GPS fixes |
| Handles `psi` wrap-around | not explicitly | yes (`_normalize_angle`) | not explicitly (small-turn assumption per step) |

---

## 7. Known limitations and possible extensions

- **No constraint handling**: estimated speed `v` can in principle become
  negative under heavy measurement noise; no projection onto physically
  admissible states is implemented (see the *constrained Kalman filter*
  discussion in the accompanying theoretical document).
- **No outlier rejection**: a single corrupted GPS fix is fused as-is. A
  Normalized Innovation Squared (NIS) test (chi-squared gate) should be
  added before `update()` in safety-relevant deployments.
- **Loosely-coupled only**: `imu_gps_fusion.py` consumes an already
  GPS-computed position. A tightly-coupled extension would instead model
  `h` as a function of raw pseudoranges/Doppler shifts to each visible
  satellite, with the EKF/UKF state augmented with the receiver clock bias
  and drift.
- **No manoeuvre detection**: a single, fixed-noise CTRV/IMU model is
  assumed throughout. An Interacting Multiple Model (IMM) filter combining
  several motion hypotheses (straight, turning, braking) would better
  handle abrupt behavioural changes.
