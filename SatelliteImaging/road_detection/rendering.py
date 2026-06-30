# -*- coding: utf-8 -*-
"""
rendering.py
=============

Output rendering: overlay and contour visualizations of the detected
road mask on top of the original image.
"""

import numpy as np
from PIL import Image, ImageDraw


def render_filled_overlay(image, road_mask, tile_size, output_path,
                           color=(0, 220, 80), alpha=170):
    """
    Render the road mask as a semi-transparent colored overlay on the
    original image.

    Parameters
    ----------
    image : PIL.Image
        Original RGB image.
    road_mask : np.ndarray (bool)
        Tile-level road mask.
    tile_size : int
        Tile side length in pixels.
    output_path : str
        Path to save the output PNG.
    color : tuple of int
        RGB color for the overlay (default: green).
    alpha : int
        Overlay opacity, 0-255 (default: 170).
    """
    width, height = image.size
    n_rows, n_cols = road_mask.shape
    t = tile_size

    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    for row in range(n_rows):
        for col in range(n_cols):
            if road_mask[row, col]:
                y0, y1 = row * t, min(row * t + t, height)
                x0, x1 = col * t, min(col * t + t, width)
                overlay[y0:y1, x0:x1] = (*color, alpha)

    result = Image.alpha_composite(
        image.convert('RGBA'), Image.fromarray(overlay, 'RGBA')
    ).convert('RGB')
    result.save(output_path)


def render_contours(image, road_mask, tile_size, output_path,
                     color=(0, 220, 80), line_width=1):
    """
    Render the road mask as tile contours drawn over the original image,
    preserving full visibility of the underlying pixels.

    Parameters
    ----------
    image : PIL.Image
        Original RGB image.
    road_mask : np.ndarray (bool)
        Tile-level road mask.
    tile_size : int
        Tile side length in pixels.
    output_path : str
        Path to save the output PNG.
    color : tuple of int
        RGB color for the contour lines (default: green).
    line_width : int
        Contour line width in pixels.
    """
    width, height = image.size
    n_rows, n_cols = road_mask.shape
    t = tile_size

    result = image.copy()
    draw = ImageDraw.Draw(result)

    for row in range(n_rows):
        for col in range(n_cols):
            if road_mask[row, col]:
                y0, y1 = row * t, min(row * t + t, height)
                x0, x1 = col * t, min(col * t + t, width)
                draw.rectangle([x0, y0, x1 - 1, y1 - 1],
                               outline=color, width=line_width)

    result.save(output_path)
