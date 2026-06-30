# -*- coding: utf-8 -*-
"""
equivariant_features.py
========================

Equivariant feature extraction from the structure tensor.

These features are derived under the Lie group symmetries T(2), SO(2)
and SE(2):

  - Anisotropy (aniso = lambda1 / lambda2) is invariant under T(2)
    translations and under SO(2) rotations.
  - Direction (theta) is covariant under SO(2): rotating the image by
    angle alpha rotates theta by the same angle.
  - Local texture variance (m2) is invariant under T(2) and SO(2).

These properties make the features robust to image orientation and
translation, which is essential for an unsupervised pipeline that must
generalize across scenes without retraining.
"""

import numpy as np
from scipy.ndimage import convolve, gaussian_filter


def compute_structure_tensor(gray, sigma):
    """
    Compute anisotropy and orientation from the local structure tensor.

    The structure tensor at scale `sigma` is:

        J_sigma = G_sigma * [[Ix^2, Ix*Iy], [Ix*Iy, Iy^2]]

    where Ix, Iy are Sobel derivatives and G_sigma is a Gaussian kernel.
    Its eigenvalues lambda1 >= lambda2 >= 0 and dominant eigenvector
    define the anisotropy and orientation features.

    Parameters
    ----------
    gray : np.ndarray (H, W), float32
        Grayscale image.
    sigma : float
        Gaussian smoothing scale for the structure tensor.

    Returns
    -------
    aniso : np.ndarray (H, W), float32
        Anisotropy map. High values indicate a strong, single dominant
        direction (e.g. a road, an edge). Low values indicate an
        isotropic local structure (e.g. uniform vegetation).
    theta : np.ndarray (H, W), float32
        Orientation map in radians, modulo pi (undirected angle).
    """
    sobel_x = np.array([[-3, 0, 3], [-10, 0, 10], [-3, 0, 3]], dtype=np.float32) / 16
    sobel_y = np.array([[-3, -10, -3], [0, 0, 0], [3, 10, 3]], dtype=np.float32) / 16

    gx = convolve(gray, sobel_x)
    gy = convolve(gray, sobel_y)

    jxx = gaussian_filter(gx * gx, sigma)
    jxy = gaussian_filter(gx * gy, sigma)
    jyy = gaussian_filter(gy * gy, sigma)

    trace = jxx + jyy
    discriminant = np.sqrt(np.maximum((jxx - jyy) ** 2 / 4 + jxy ** 2, 0))
    lambda1 = trace / 2 + discriminant
    lambda2 = np.maximum(trace / 2 - discriminant, 0)

    aniso = (lambda1 / (lambda2 + 1e-8)).astype(np.float32)
    theta = (0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2).astype(np.float32)

    return aniso, theta


def compute_local_texture(gray, window_size):
    """
    Compute the local second central moment (variance) m2 in a sliding
    window of size `window_size`.

    Smooth surfaces (clean asphalt) have low m2. Textured surfaces
    (rooftops, vegetation) have higher m2. This feature is independent
    of the structure tensor and helps discriminate surface type beyond
    pure geometry.

    Parameters
    ----------
    gray : np.ndarray (H, W), float32
        Grayscale image.
    window_size : int
        Side length of the square sliding window (odd number recommended).

    Returns
    -------
    m2 : np.ndarray (H, W), float32
        Local variance map.
    """
    pad = window_size // 2
    padded = np.pad(gray, pad, mode='reflect')
    windows = np.lib.stride_tricks.sliding_window_view(
        padded, (window_size, window_size)
    )
    windows = windows.reshape(gray.shape[0], gray.shape[1], window_size * window_size)

    mean = windows.mean(axis=2)
    centered = windows - mean[:, :, None]
    m2 = (centered ** 2).mean(axis=2)

    return m2.astype(np.float32)


def circular_mean_theta(theta_patch):
    """
    Compute the circular mean of an orientation patch, accounting for
    the fact that theta and theta + pi represent the same undirected
    line direction.

    Parameters
    ----------
    theta_patch : np.ndarray
        Patch of orientation values in radians (modulo pi).

    Returns
    -------
    float
        Circular mean orientation in radians (modulo pi).
    """
    sin_sum = np.sin(2 * theta_patch).mean()
    cos_sum = np.cos(2 * theta_patch).mean()
    return float(0.5 * np.arctan2(sin_sum, cos_sum))


def angular_difference(angle_a, angle_b):
    """
    Smallest difference between two undirected angles (modulo pi).

    Parameters
    ----------
    angle_a, angle_b : float
        Angles in radians, modulo pi.

    Returns
    -------
    float
        Absolute angular difference in [0, pi/2].
    """
    diff = abs(angle_a - angle_b) % np.pi
    return min(diff, np.pi - diff)
