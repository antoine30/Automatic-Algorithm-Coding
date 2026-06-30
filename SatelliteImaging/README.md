# Unsupervised Road Detection in Satellite Imagery

Detects roads in very high resolution satellite imagery without any
manual annotation, using equivariant geometric features (structure
tensor) and iterative region growing from high-confidence seeds.

## How it works

1. **Equivariant feature extraction** (`equivariant_features.py`)
   The structure tensor is computed at each pixel, yielding an
   anisotropy map (how strongly a single direction dominates locally)
   and an orientation map. These features are invariant under
   translation and rotation (T(2), SO(2), SE(2) symmetries), which
   makes the pipeline robust across image orientations. A local
   texture variance map is computed in parallel to discriminate smooth
   asphalt from textured rooftops and vegetation.

2. **Tile aggregation and mask construction** (`masks.py`)
   Pixel-level features are aggregated into a tile grid. Two masks are
   built: a permissive *candidate* mask (tiles that could plausibly be
   road) and a strict *seed* mask (tiles that are road with very high
   confidence — clean, well-lit asphalt).

3. **Iterative region growing** (`iterative_growing.py`)
   A breadth-first search propagates the seed mask into the candidate
   mask. A single pass typically misses secondary roads disconnected
   from the main network in feature space. The iterative expansion
   promotes isolated candidate components to seed status and repeats
   the search until convergence, recovering these secondary segments.

4. **Rendering** (`rendering.py`)
   The final road mask is rendered both as a semi-transparent overlay
   and as tile contours over the original image.

The full pipeline is orchestrated in `pipeline.py` and exposed via the
command-line entry point `main.py`.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py scene.png
```

With a custom output prefix and tile size:

```bash
python main.py scene.png results/scene --tile-size 5
```

Use `--tile-size 5` for narrow or strongly inclined roads, where the
default 10-pixel tiles mix road and building signal. This roughly
quadruples computation time.

As a library:

```python
from road_detection import detect_roads

road_mask = detect_roads("scene.png", tile_size=10)
```

## Parameters

All thresholds are defined in `road_detection/config.py` and can be
overridden via keyword arguments to `detect_roads()`. The default
values were calibrated on very high resolution (~50 cm/pixel) French
urban satellite imagery and may require adjustment for other sensors
or resolutions.

## Limitations

- **Vehicles**: parked cars on roads are physically indistinguishable
  from asphalt at typical VHR resolutions using local features alone.
- **Surface ambiguity**: shaded rooftops in concrete or smooth
  materials can share local feature signatures with secondary roads.
  Resolving this fully requires contextual information beyond what
  this geometric pipeline provides (see the companion Siamese network
  project for a learning-based resolution).

## License

CC-BY 4.0
