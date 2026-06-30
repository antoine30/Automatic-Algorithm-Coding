# -*- coding: utf-8 -*-
"""
masks.py
=========

Tile aggregation and candidate/seed mask construction.

This module aggregates pixel-level features into a tile grid, then
builds two masks used by the region growing stage:

  - The candidate mask: a permissive mask of tiles that COULD belong
    to a road, based on geometric and photometric criteria.
  - The seed mask: a strict mask of tiles that are road with very
    high confidence (clean, well-illuminated asphalt). These seeds
    anchor the region growing process.
"""

import numpy as np


def aggregate_to_tiles(rgb_array, aniso_map, theta_map, m2_map, tile_size):
    """
    Aggregate pixel-level features into a grid of tiles.

    Parameters
    ----------
    rgb_array : np.ndarray (H, W, 3)
        Original RGB image array.
    aniso_map : np.ndarray (H, W)
        Pixel-level anisotropy map.
    theta_map : np.ndarray (H, W)
        Pixel-level orientation map (radians, modulo pi).
    m2_map : np.ndarray (H, W)
        Pixel-level local texture variance map.
    tile_size : int
        Tile side length in pixels.

    Returns
    -------
    dict
        Dictionary of per-tile feature maps, each of shape (n_rows, n_cols):
        'aniso', 'theta', 'm2', 'R', 'G', 'B', 'saturation'.
        Also includes 'shape' = (n_rows, n_cols) and 'tile_size'.
    """
    height, width = rgb_array.shape[:2]
    t = tile_size
    n_rows = (height + t - 1) // t
    n_cols = (width + t - 1) // t

    tile_aniso = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_theta = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_m2 = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_r = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_g = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_b = np.zeros((n_rows, n_cols), dtype=np.float32)
    tile_sat = np.zeros((n_rows, n_cols), dtype=np.float32)

    for row in range(n_rows):
        for col in range(n_cols):
            y0, y1 = row * t, min(row * t + t, height)
            x0, x1 = col * t, min(col * t + t, width)

            tile_aniso[row, col] = float(aniso_map[y0:y1, x0:x1].mean())

            theta_patch = theta_map[y0:y1, x0:x1]
            sin_sum = np.sin(2 * theta_patch).mean()
            cos_sum = np.cos(2 * theta_patch).mean()
            tile_theta[row, col] = float(0.5 * np.arctan2(sin_sum, cos_sum))

            tile_m2[row, col] = float(m2_map[y0:y1, x0:x1].mean())

            patch = rgb_array[y0:y1, x0:x1].astype(np.float64)
            tile_r[row, col] = patch[:, :, 0].mean()
            tile_g[row, col] = patch[:, :, 1].mean()
            tile_b[row, col] = patch[:, :, 2].mean()
            tile_sat[row, col] = float(
                patch.max(axis=2).mean() - patch.min(axis=2).mean()
            )

    return {
        'aniso': tile_aniso,
        'theta': tile_theta,
        'm2': tile_m2,
        'R': tile_r,
        'G': tile_g,
        'B': tile_b,
        'saturation': tile_sat,
        'shape': (n_rows, n_cols),
        'tile_size': tile_size,
    }


def build_candidate_mask(tiles, aniso_min, m2_max, saturation_max,
                          r_min, r_max):
    """
    Build the permissive candidate mask: tiles that could plausibly be
    road surface, based on loose thresholds on anisotropy, texture,
    saturation and luminosity.

    Parameters
    ----------
    tiles : dict
        Output of `aggregate_to_tiles`.
    aniso_min : float
        Minimum anisotropy for a candidate tile (linear structure present).
    m2_max : float
        Maximum local texture variance (smooth surface).
    saturation_max : float
        Maximum chromatic saturation (neutral color).
    r_min, r_max : float
        Acceptable range for the red channel mean (excludes very dark
        shadows and very bright surfaces).

    Returns
    -------
    np.ndarray (bool)
        Candidate mask, same shape as the tile grid.
    """
    return (
        (tiles['aniso'] >= aniso_min) &
        (tiles['m2'] < m2_max) &
        (tiles['saturation'] < saturation_max) &
        (tiles['R'] > r_min) & (tiles['R'] < r_max)
    )


def build_seed_mask(tiles, m2_max, saturation_max, rg_max, rb_max,
                     r_min, r_max, aniso_min):
    """
    Build the strict seed mask: tiles classified as road with very
    high confidence (clean, well-illuminated asphalt). These seeds
    anchor the region growing process in `iterative_growing.py`.

    Parameters
    ----------
    tiles : dict
        Output of `aggregate_to_tiles`.
    m2_max : float
        Maximum local texture variance (strict — very smooth only).
    saturation_max : float
        Maximum chromatic saturation (strict — neutral only).
    rg_max : float
        Maximum |R - G| difference (color neutrality).
    rb_max : float
        Maximum |R - B| difference (color neutrality).
    r_min, r_max : float
        Acceptable range for the red channel mean.
    aniso_min : float
        Minimum anisotropy.

    Returns
    -------
    np.ndarray (bool)
        Seed mask, same shape as the tile grid.
    """
    return (
        (tiles['m2'] < m2_max) &
        (tiles['saturation'] < saturation_max) &
        (np.abs(tiles['R'] - tiles['G']) < rg_max) &
        (np.abs(tiles['R'] - tiles['B']) < rb_max) &
        (tiles['R'] > r_min) & (tiles['R'] < r_max) &
        (tiles['aniso'] >= aniso_min)
    )
