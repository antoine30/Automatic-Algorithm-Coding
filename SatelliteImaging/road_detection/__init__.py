# -*- coding: utf-8 -*-
"""
road_detection
===============

Unsupervised road detection in satellite imagery using equivariant
geometric features (structure tensor) and iterative region growing.

No manual annotation is required at any stage of the pipeline.

Example
-------
>>> from road_detection import detect_roads
>>> road_mask = detect_roads("scene.png")
"""

from .pipeline import detect_roads

__all__ = ["detect_roads"]
__version__ = "1.0.0"
