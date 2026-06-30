# -*- coding: utf-8 -*-
"""
iterative_growing.py
======================

Iterative region growing from high-confidence seeds.

A plain breadth-first search (BFS) from the initial seeds fails to
reach secondary roads that are spatially disconnected from the main
road network in feature space (e.g. across an intersection, a patch
of low signal, or a road surface slightly different from the seed
reference). This module solves the problem by iteratively promoting
disconnected candidate components to seed status, until convergence.

This iterative expansion is the key contribution that allows the
pipeline to recover secondary and inclined roads that a single-pass
BFS would miss entirely.
"""

import numpy as np
from collections import deque
from scipy.ndimage import label


def bfs_grow(seed_mask, candidate_mask):
    """
    Propagate the seed mask into the candidate mask using breadth-first
    search with 8-connectivity.

    Parameters
    ----------
    seed_mask : np.ndarray (bool)
        Initial seed tiles (high confidence).
    candidate_mask : np.ndarray (bool)
        Permissive candidate tiles that the BFS is allowed to expand into.

    Returns
    -------
    np.ndarray (bool)
        Mask of all tiles reached by the BFS, including the original seeds.
    """
    n_rows, n_cols = seed_mask.shape
    accepted = seed_mask.copy()
    queue = deque(zip(*np.where(seed_mask)))

    while queue:
        row, col = queue.popleft()
        for d_row in (-1, 0, 1):
            for d_col in (-1, 0, 1):
                if d_row == 0 and d_col == 0:
                    continue
                n_row, n_col = row + d_row, col + d_col
                if not (0 <= n_row < n_rows and 0 <= n_col < n_cols):
                    continue
                if accepted[n_row, n_col]:
                    continue
                if candidate_mask[n_row, n_col]:
                    accepted[n_row, n_col] = True
                    queue.append((n_row, n_col))

    return accepted


def iterative_region_growing(seed_mask, candidate_mask,
                              min_isolated_component=3,
                              max_iterations=5,
                              verbose=True):
    """
    Region growing with iterative seed expansion.

    At each iteration:
      1. BFS-propagate from the current seed set into the candidate mask.
      2. Identify connected components of candidates NOT reached by the
         BFS (e.g. secondary roads disconnected from the main network).
      3. Promote components of size >= `min_isolated_component` to
         seed status.
      4. Repeat until no new seeds are added (convergence) or
         `max_iterations` is reached.

    Parameters
    ----------
    seed_mask : np.ndarray (bool)
        Initial high-confidence seed tiles.
    candidate_mask : np.ndarray (bool)
        Permissive candidate tiles.
    min_isolated_component : int
        Minimum size (in tiles) for a disconnected candidate component
        to be promoted to seed status.
    max_iterations : int
        Maximum number of expansion iterations.
    verbose : bool
        If True, print progress at each iteration.

    Returns
    -------
    np.ndarray (bool)
        Final mask of all tiles reached after convergence.
    """
    seeds = seed_mask.copy()

    for iteration in range(max_iterations):
        accepted = bfs_grow(seeds, candidate_mask)
        not_reached = candidate_mask & ~accepted

        labeled, n_components = label(not_reached)
        added = 0
        for component_id in range(1, n_components + 1):
            component = (labeled == component_id)
            if component.sum() >= min_isolated_component:
                seeds |= component
                added += int(component.sum())

        if verbose:
            print(f"  iteration {iteration + 1}: "
                  f"reached={int(accepted.sum())} tiles, "
                  f"+{added} seed tiles added")

        if added == 0:
            break

    return bfs_grow(seeds, candidate_mask)


def filter_by_component_size(mask, min_size=8):
    """
    Keep only connected components of at least `min_size` tiles.

    This final filtering step removes residual noise — small isolated
    components that survived region growing but are too small to be
    a plausible road segment.

    Parameters
    ----------
    mask : np.ndarray (bool)
        Input mask.
    min_size : int
        Minimum component size in tiles to keep.

    Returns
    -------
    np.ndarray (bool)
        Filtered mask.
    """
    labeled, n_components = label(mask)
    keep = np.zeros_like(mask, dtype=bool)

    for component_id in range(1, n_components + 1):
        component = (labeled == component_id)
        if component.sum() >= min_size:
            keep |= component

    return keep
