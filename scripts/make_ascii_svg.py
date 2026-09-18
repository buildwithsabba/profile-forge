#!/usr/bin/env python3
"""Turn the prepped portrait into an SVG that types itself in.

Reads assets/source-prepped.png (see prep_photo.py) and writes
ascii-portrait.svg.

Two things matter for this to look like a portrait and not like static:

  Polarity. The art renders light-on-dark, so the ramp runs dark -> bright:
  a black pixel picks the space glyph and disappears into the panel, a
  bright pixel picks '@'. That is inverted from a white-background pipeline.

  Alignment. Monospace metrics differ across platforms and GitHub cannot
  load a webfont into a README SVG, so nothing here may depend on a
  particular face's metrics -- or on whitespace. Renderers collapse runs of
  spaces inside <text> even under white-space:pre, which spreads the
  surviving glyphs across the row and makes the portrait wobble. So no
  space is ever emitted: each row is split into runs of non-space glyphs,
  and every run is placed at its own absolute x with an explicit
  textLength. Column alignment then holds in any renderer.

  STATIC=1 python scripts/make_ascii_svg.py   # frozen frame, for previews
"""
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import svgkit as k

SRC = "assets/source-prepped.png"
OUT = os.environ.get("OUT", "ascii-portrait.svg")

# dark (blank) -> bright (dense)
RAMP = " .`:-=+*csS#%@"

CFG = config.load()
COLS = int(CFG["ascii_columns"])
FS = 12.0                  # font-size in px
CW = FS * 0.6              # monospace advance is ~0.6em across every face
CH = FS * 1.0              # line height
PAD_X, PAD_TOP, PAD_BOT = 16, 10, 14

ROW_DUR = 0.34             # how long one row takes to wipe in
STAGGER = 0.042            # delay between consecutive rows
STATIC = os.environ.get("STATIC") == "1"


def sample(path):
    """Downsample to a character grid, correcting for cell aspect ratio."""
    img = Image.open(path).convert("L")
    w, h = img.size
    rows = max(1, round(COLS * (h / w) * (CW / CH)))
    grid = np.asarray(img.resize((COLS, rows), Image.LANCZOS),
                      dtype=np.float32) / 255.0
    return grid, rows


def to_chars(grid):
    idx = np.clip((grid * (len(RAMP) - 1)).round().astype(int),
                  0, len(RAMP) - 1)
    return ["".join(RAMP[i] for i in row) for row in idx]


def build(lines, rows):
    w = int(COLS * CW + PAD_X * 2)
    h = int(k.BAR_H + PAD_TOP + rows * CH + PAD_BOT)

    defs, body = [], []
    for r, raw in enumerate(lines):
        runs = [(m.start(), m.group(0))
                for m in re.finditer(r"\S+", raw)]
        if not runs:
            continue

        y = k.BAR_H + PAD_TOP + (r + 1) * CH - CH * 0.22
        first, last = runs[0][0], runs[-1][0] + len(runs[-1][1])
        x = PAD_X + first * CW
        span = (last - first) * CW
        begin = r * STAGGER

        if STATIC:
            clip = ""
        else:
            # A per-row clip rectangle grows left to right, then freezes.
            defs.append(
                f'    <clipPath id="w{r}">'
                f'<rect x="{x:.1f}" y="{y - CH:.1f}" width="0" '
                f'height="{CH * 1.4:.1f}">'
                f'<animate attributeName="width" from="0" to="{span:.1f}" '
                f'begin="{begin:.2f}s" dur="{ROW_DUR}s" fill="freeze"/>'
                f'</rect></clipPath>'
            )
            clip = f' clip-path="url(#w{r})"'

        glyphs = "".join(
            f'<text x="{PAD_X + col * CW:.1f}" y="{y:.1f}" '
            f'textLength="{len(run) * CW:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{k.esc(run)}</text>'
            for col, run in runs
        )
        body.append(
            f'    <g font-family="{k.MONO}" font-size="{FS:g}" '
            f'fill="{k.FG}"{clip}>{glyphs}</g>'
        )

        if not STATIC:
            # A block cursor rides the wipe edge, then switches off.
            body.append(
                f'    <rect y="{y - CH * 0.78:.1f}" width="{CW:.1f}" '
                f'height="{CH * 0.86:.1f}" fill="{CFG["accent"]}" opacity="0">'
                f'<animate attributeName="x" from="{x:.1f}" '
                f'to="{x + span:.1f}" begin="{begin:.2f}s" '
                f'dur="{ROW_DUR}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0.9" begin="{begin:.2f}s"/>'
                f'<set attributeName="opacity" to="0" '
                f'begin="{begin + ROW_DUR:.2f}s"/>'
                f'</rect>'
            )

    title = f'{CFG["user"]}@{CFG["host"]}: ~/whoami'
    return k.panel(w, h, title, "\n".join(body), defs="\n".join(defs))


def main():
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC} — run scripts/prep_photo.py first")

    grid, rows = sample(SRC)
    lines = to_chars(grid)

    with open(OUT, "w") as f:
        f.write(build(lines, rows))

    total = (len(lines) - 1) * STAGGER + ROW_DUR
    print(f"wrote {OUT}  grid {COLS}x{rows}  "
          f"{os.path.getsize(OUT) / 1024:.0f} KB  "
          f"{'static' if STATIC else f'{total:.1f}s reveal'}")

    if os.environ.get("PREVIEW") == "1":
        for ln in lines:
            print(ln.rstrip())


if __name__ == "__main__":
    main()
