#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
========

Command-line entry point for the unsupervised road detection pipeline.

Usage
-----
    python main.py <image_path> [output_prefix] [--tile-size N]

Example
-------
    python main.py scene.png results/scene --tile-size 10

Outputs (written next to `output_prefix`)
------------------------------------------
    <output_prefix>_roads_overlay.png    Original image with a semi-transparent
                                          green overlay on detected road tiles.
    <output_prefix>_roads_contours.png   Original image with green tile contours
                                          on detected road tiles.
"""

import argparse
import sys

from road_detection.pipeline import detect_roads


def parse_args():
    parser = argparse.ArgumentParser(
        description="Unsupervised road detection in satellite imagery "
                    "via equivariant features and iterative region growing."
    )
    parser.add_argument("image_path", help="Path to the input RGB satellite image.")
    parser.add_argument("output_prefix", nargs="?", default=None,
                        help="Prefix for output files (default: derived from "
                             "the input image path).")
    parser.add_argument("--tile-size", type=int, default=None,
                        help="Tile side length in pixels. Use 10 for wide, "
                             "near-horizontal roads; use 5 for narrow or "
                             "strongly inclined roads (default: 10).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress output.")
    return parser.parse_args()


def main():
    args = parse_args()

    road_mask = detect_roads(
        image_path=args.image_path,
        output_prefix=args.output_prefix,
        tile_size=args.tile_size,
        verbose=not args.quiet,
    )

    n_road_tiles = int(road_mask.sum())
    n_total_tiles = road_mask.size
    coverage = 100.0 * n_road_tiles / n_total_tiles

    print(f"\nDetected {n_road_tiles} road tiles out of {n_total_tiles} "
          f"({coverage:.1f}% coverage).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
