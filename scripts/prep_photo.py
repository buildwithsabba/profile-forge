#!/usr/bin/env python3
"""Prep a portrait photo for ASCII conversion.

Pipeline: isolate the subject, frame the head, then grade for a glyph ramp.

  1. rembg isolates the subject, so a studio backdrop stops competing with
     the face for glyphs.
  2. The head is framed from the *silhouette*, never from the graded
     image. Dark hair carries almost no brightness, so any framing that
     looks for bright pixels crops the top of the head off.
  3. CLAHE boosts local contrast — a flatly-lit face otherwise converts to
     one undifferentiated mass of dense glyphs.
  4. A tone curve crushes the low end onto pure black, which the renderer
     maps to the blank end of the ramp (see make_ascii_svg.py).

The art renders light-on-dark, so black here means "no ink".
That is inverted from the usual white-background ASCII pipeline.

Run this only when the photo changes:
    python scripts/prep_photo.py            # uses photo: from profile.yml
    python scripts/prep_photo.py other.jpg
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    # Registers the HEIC/HEIF opener. iPhones shoot HEIC by default, and
    # people will upload straight from their camera roll.
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

SRC = sys.argv[1] if len(sys.argv) > 1 else config.load()["photo"]
CUTOUT = "assets/source-cutout.png"   # cached rembg result
OUT = "assets/source-prepped.png"

# --- framing --------------------------------------------------------------
HEAD_BAND = 0.60      # share of the silhouette, from the top, that is head
                      # and not shoulder; used to measure head width only
FRAME_W = 1.46        # frame width, in measured head widths
FRAME_ASPECT = 0.95   # frame width / height. Drives the panel's proportions,
                      # which in turn set the README column widths.
TOP_LIFT = 0.04       # headroom above the hairline, in head widths

# --- grading --------------------------------------------------------------
CLAHE_CLIP = 1.6      # higher = more local contrast, more noise
CLAHE_GRID = 8        # tile size for adaptive equalization
BLACK_POINT = 0.50    # input level mapped to pure black (kills the sweater)
WHITE_POINT = 0.97    # input level mapped to pure white
GAMMA = 1.50          # >1 darkens midtones
EDGE_FEATHER = 2      # px of alpha blur, softens the cutout boundary
NOISE_FLOOR = 0.06    # levels below this are forced to black, so faint
                      # backdrop residue does not earn a glyph
SILHOUETTE = 0.0      # minimum level inside the subject. Lifting near-black
                      # hair to the faintest glyph sounds like it would give
                      # the head a visible outline; in practice it flattens
                      # the whole skull into one dotted haze and costs more
                      # modelling in the face than it buys in silhouette.
                      # Left here, off, because it is the obvious thing to
                      # reach for.
# -------------------------------------------------------------------------


def cutout(path):
    """Isolate the subject, caching the (slow) rembg pass."""
    if os.path.exists(CUTOUT):
        print(f"  reusing cached cutout: {CUTOUT}")
        return Image.open(CUTOUT).convert("RGBA")

    from rembg import remove  # imported lazily: heavy, and only needed once

    print("  running rembg (first run downloads the u2net model)...")
    subject = remove(Image.open(path).convert("RGB"))
    subject.save(CUTOUT)
    return subject.convert("RGBA")


def head_frame(img):
    """Frame the head from the alpha silhouette.

    Head width is the *median* row width across the upper band, not the
    maximum: a single row clipping the top of a shoulder would otherwise
    double the measured width and leave the face adrift in empty panel.
    """
    mask = np.array(img.split()[-1]) > 12
    h, w = mask.shape

    rows = np.where(mask.any(axis=1))[0]
    if not len(rows):
        return img
    y_top, y_bot = rows[0], rows[-1]

    band = mask[y_top:y_top + int((y_bot - y_top) * HEAD_BAND)]
    widths, centers = [], []
    for row in band:
        xs = np.where(row)[0]
        if len(xs):
            widths.append(xs[-1] - xs[0])
            centers.append((xs[0] + xs[-1]) / 2.0)

    head_w = float(np.median(widths))
    cx = float(np.median(centers))

    fw = head_w * FRAME_W
    fh = fw / FRAME_ASPECT
    y0 = y_top - head_w * TOP_LIFT

    box = (int(round(max(0, cx - fw / 2))),
           int(round(max(0, y0))),
           int(round(min(w, cx + fw / 2))),
           int(round(min(h, y0 + fh))))

    print(f"  head width {head_w:.0f}px, centre x {cx:.0f}")
    print(f"  frame {box}  -> {box[2] - box[0]}x{box[3] - box[1]}")
    return img.crop(box)


def grade(img):
    """Grayscale, local contrast, levels, and mask out the background."""
    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.split()[-1]).astype(np.float32) / 255.0

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP,
                            tileGridSize=(CLAHE_GRID, CLAHE_GRID))
    gray = clahe.apply(gray)

    v = gray.astype(np.float32) / 255.0
    v = np.clip((v - BLACK_POINT) / max(1e-6, WHITE_POINT - BLACK_POINT), 0, 1)
    v = np.power(v, GAMMA)

    if EDGE_FEATHER:
        k = EDGE_FEATHER * 2 + 1
        alpha = cv2.GaussianBlur(alpha, (k, k), 0)

    v = v * alpha
    v[v < NOISE_FLOOR] = 0.0

    if SILHOUETTE:
        v = np.maximum(v, SILHOUETTE * (alpha > 0.6))
    return v


def main():
    if not os.path.exists(SRC):
        sys.exit(f"source photo not found: {SRC}")

    print(f"prep_photo: {SRC}")
    v = grade(head_frame(cutout(SRC)))

    out = (np.clip(v, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(out, mode="L").save(OUT)

    print(f"  wrote {OUT}  {out.shape[1]}x{out.shape[0]}")
    print(f"  ink coverage: {(out > 28).mean():.1%}  "
          f"(share of pixels that get a glyph)")


if __name__ == "__main__":
    main()
