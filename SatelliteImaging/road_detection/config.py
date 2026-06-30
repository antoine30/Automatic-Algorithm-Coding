# -*- coding: utf-8 -*-
"""
config.py
==========

Default pipeline parameters. Override these on the command line or by
passing keyword arguments to `road_detection.pipeline.detect_roads`.
"""

# Tile size in pixels. Use 10 for wide, near-horizontal roads.
# Use 5 for narrow or strongly inclined roads (better spatial resolution
# at the cost of ~4x computation time).
TILE_SIZE = 10

# Structure tensor smoothing scale (pixels).
SIGMA = 5.0

# Local texture window size (pixels).
TEXTURE_WINDOW = 7

# ── Candidate mask thresholds (permissive) ──────────────────────────────
ANISO_MIN_CANDIDATE = 3.0
M2_MAX = 0.006
SATURATION_MAX = 14.0
R_MIN = 65
R_MAX = 175

# ── Seed mask thresholds (strict, high-confidence asphalt) ──────────────
SEED_M2_MAX = 0.001
SEED_SATURATION_MAX = 6
SEED_RG_MAX = 6
SEED_RB_MAX = 8
SEED_R_MIN = 80
SEED_R_MAX = 165
SEED_ANISO_MIN = 3.0

# ── Region growing parameters ────────────────────────────────────────────
MIN_ISOLATED_COMPONENT = 3
MIN_FINAL_COMPONENT = 8
MAX_ITERATIONS = 5
