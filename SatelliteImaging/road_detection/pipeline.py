# -*- coding: utf-8 -*-
"""
pipeline.py
============

Full unsupervised road detection pipeline.

Orchestrates the five stages:
  1. Equivariant feature extraction (structure tensor, local texture)
  2. Tile aggregation
  3. Candidate and seed mask construction
  4. Iterative region growing
  5. Final size filtering and rendering

No manual annotation is required at any stage.
"""

import numpy as np
from PIL import Image
from skimage import color as skimage_color

from . import config
from .equivariant_features import compute_structure_tensor, compute_local_texture
from .masks import aggregate_to_tiles, build_candidate_mask, build_seed_mask
from .iterative_growing import iterative_region_growing, filter_by_component_size
from .rendering import render_filled_overlay, render_contours


def detect_roads(image_path, output_prefix=None, tile_size=None,
                  sigma=None, texture_window=None,
                  aniso_min_candidate=None, m2_max=None, saturation_max=None,
                  r_min=None, r_max=None,
                  seed_m2_max=None, seed_saturation_max=None,
                  seed_rg_max=None, seed_rb_max=None,
                  seed_r_min=None, seed_r_max=None, seed_aniso_min=None,
                  min_isolated_component=None, max_iterations=None,
                  min_final_component=None,
                  save_outputs=True, verbose=True):
    """
    Run the full unsupervised road detection pipeline on a satellite image.

    Parameters
    ----------
    image_path : str
        Path to the input RGB satellite image.
    output_prefix : str, optional
        Prefix for output files. Defaults to the input path without
        its extension.
    tile_size : int, optional
        Tile side length in pixels. Defaults to `config.TILE_SIZE`.
        Use a smaller value (e.g. 5) for narrow or inclined roads.
    sigma, texture_window : float, int, optional
        Structure tensor scale and texture window size.
        Default to `config` values.
    aniso_min_candidate, m2_max, saturation_max, r_min, r_max : float, optional
        Candidate mask thresholds. Default to `config` values.
    seed_m2_max, seed_saturation_max, seed_rg_max, seed_rb_max,
    seed_r_min, seed_r_max, seed_aniso_min : float, optional
        Seed mask thresholds. Default to `config` values.
    min_isolated_component, max_iterations, min_final_component : int, optional
        Region growing parameters. Default to `config` values.
    save_outputs : bool
        If True, save the overlay and contour visualizations to disk.
    verbose : bool
        If True, print progress information.

    Returns
    -------
    np.ndarray (bool)
        Final tile-level road mask, shape (n_rows, n_cols).
    """
    tile_size = tile_size or config.TILE_SIZE
    sigma = sigma or config.SIGMA
    texture_window = texture_window or config.TEXTURE_WINDOW

    aniso_min_candidate = aniso_min_candidate or config.ANISO_MIN_CANDIDATE
    m2_max = m2_max or config.M2_MAX
    saturation_max = saturation_max or config.SATURATION_MAX
    r_min = r_min or config.R_MIN
    r_max = r_max or config.R_MAX

    seed_m2_max = seed_m2_max or config.SEED_M2_MAX
    seed_saturation_max = seed_saturation_max or config.SEED_SATURATION_MAX
    seed_rg_max = seed_rg_max or config.SEED_RG_MAX
    seed_rb_max = seed_rb_max or config.SEED_RB_MAX
    seed_r_min = seed_r_min or config.SEED_R_MIN
    seed_r_max = seed_r_max or config.SEED_R_MAX
    seed_aniso_min = seed_aniso_min or config.SEED_ANISO_MIN

    min_isolated_component = min_isolated_component or config.MIN_ISOLATED_COMPONENT
    max_iterations = max_iterations or config.MAX_ITERATIONS
    min_final_component = min_final_component or config.MIN_FINAL_COMPONENT

    if output_prefix is None:
        output_prefix = image_path.rsplit('.', 1)[0]

    if verbose:
        print(f"Loading {image_path}...")
    image = Image.open(image_path).convert('RGB')
    rgb_array = np.array(image)
    gray = skimage_color.rgb2gray(rgb_array).astype(np.float32)
    height, width = rgb_array.shape[:2]
    if verbose:
        print(f"  Image size: {width}x{height} px")

    if verbose:
        print("Computing structure tensor (anisotropy, orientation)...")
    aniso_map, theta_map = compute_structure_tensor(gray, sigma)

    if verbose:
        print("Computing local texture...")
    m2_map = compute_local_texture(gray, texture_window)

    if verbose:
        print(f"Aggregating to {tile_size}x{tile_size} tiles...")
    tiles = aggregate_to_tiles(rgb_array, aniso_map, theta_map, m2_map, tile_size)
    n_rows, n_cols = tiles['shape']
    if verbose:
        print(f"  Grid: {n_rows}x{n_cols} = {n_rows * n_cols} tiles")

    if verbose:
        print("Building candidate and seed masks...")
    candidate_mask = build_candidate_mask(
        tiles, aniso_min_candidate, m2_max, saturation_max, r_min, r_max
    )
    seed_mask = build_seed_mask(
        tiles, seed_m2_max, seed_saturation_max, seed_rg_max, seed_rb_max,
        seed_r_min, seed_r_max, seed_aniso_min
    )
    if verbose:
        print(f"  Candidate tiles: {int(candidate_mask.sum())}")
        print(f"  Initial seed tiles: {int(seed_mask.sum())}")

    if verbose:
        print("Running iterative region growing...")
    grown_mask = iterative_region_growing(
        seed_mask, candidate_mask,
        min_isolated_component=min_isolated_component,
        max_iterations=max_iterations,
        verbose=verbose,
    )
    if verbose:
        print(f"  Tiles reached: {int(grown_mask.sum())}")

    if verbose:
        print("Filtering by component size...")
    road_mask = filter_by_component_size(grown_mask, min_size=min_final_component)
    if verbose:
        print(f"  Final road tiles: {int(road_mask.sum())}")

    if save_outputs:
        if verbose:
            print("Rendering visualizations...")
        overlay_path = f"{output_prefix}_roads_overlay.png"
        contours_path = f"{output_prefix}_roads_contours.png"
        render_filled_overlay(image, road_mask, tile_size, overlay_path)
        render_contours(image, road_mask, tile_size, contours_path)
        if verbose:
            print(f"  -> {overlay_path}")
            print(f"  -> {contours_path}")

    return road_mask
