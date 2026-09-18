#!/usr/bin/env python3
"""neofetch-style info card, built from profile.yml.

Content comes entirely from profile.yml; everything here is layout.
Deliberately no GitHub statistics: the heatmap already covers those, so
this panel is for the things a number cannot say.

    python scripts/make_info_card.py
    STATIC=1 python scripts/make_info_card.py   # frozen frame, for previews
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import svgkit as k

OUT = os.environ.get("OUT", "info-card.svg")
STATIC = os.environ.get("STATIC") == "1"

CFG = config.load()
HEAD = (CFG["user"], CFG["host"])
ROWS = CFG["rows"]            # (label, value); an empty label continues above
MOTTO = CFG["motto"]
ACCENT = CFG["accent"]
SWATCHES = CFG["swatches"]    # neofetch prints its palette at the bottom

W = 560
FS = 13.0
LH = 21.0
PAD_X = 18
LABEL_W = 74          # px reserved for the left column
STAGGER = 0.085
DUR = 0.42


def line(y, label, value, delay):
    style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
    cls = "" if STATIC else ' class="r"'
    out = f'    <g{cls}{style}>'
    if label:
        out += (f'<text x="{PAD_X}" y="{y:.0f}" font-family="{k.MONO}" '
                f'font-size="{FS:g}" fill="{ACCENT}" '
                f'font-weight="600">{k.esc(label)}</text>')
    out += (f'<text x="{PAD_X + LABEL_W}" y="{y:.0f}" font-family="{k.MONO}" '
            f'font-size="{FS:g}" fill="{k.FG}">{k.esc(value)}</text></g>')
    return out


def build():
    body, i = [], 0
    y = k.BAR_H + 26

    # neofetch header: user@host, then a rule the width of that string.
    user, host = HEAD
    title = f"{user}@{host}"
    body.append(
        f'    <g class="r" style="animation-delay:0s">'
        f'<text x="{PAD_X}" y="{y:.0f}" font-family="{k.MONO}" '
        f'font-size="{FS:g}" font-weight="700" fill="{k.GREEN}">{user}'
        f'<tspan fill="{k.DIM}">@</tspan>'
        f'<tspan fill="{ACCENT}">{host}</tspan></text></g>'
        if not STATIC else
        f'    <g><text x="{PAD_X}" y="{y:.0f}" font-family="{k.MONO}" '
        f'font-size="{FS:g}" font-weight="700" fill="{k.GREEN}">{user}'
        f'<tspan fill="{k.DIM}">@</tspan>'
        f'<tspan fill="{ACCENT}">{host}</tspan></text></g>'
    )
    i += 1
    y += LH * 0.62
    rule = len(title) * FS * 0.6
    body.append(
        f'    <rect x="{PAD_X}" y="{y:.0f}" width="{rule:.0f}" height="1" '
        f'fill="{k.BORDER}"/>'
    )
    y += LH * 0.85

    for label, value in ROWS:
        y += LH
        body.append(line(y, label, value, i * STAGGER))
        i += 1

    # Palette strip.
    y += LH * 1.25
    sw = 20
    for n, c in enumerate(SWATCHES):
        d = "" if STATIC else f' style="animation-delay:{i * STAGGER:.2f}s"'
        cls = "" if STATIC else ' class="r"'
        body.append(
            f'    <rect{cls}{d} x="{PAD_X + n * (sw + 4)}" y="{y:.0f}" '
            f'width="{sw}" height="9" rx="2" fill="{c}"/>'
        )
    i += 1

    if MOTTO:
        y += LH * 1.5
        d = "" if STATIC else f' style="animation-delay:{i * STAGGER:.2f}s"'
        cls = "" if STATIC else ' class="r"'
        body.append(
            f'    <text{cls}{d} x="{PAD_X}" y="{y:.0f}" '
            f'font-family="{k.MONO}" font-size="11.5" fill="{k.DIM}" '
            f'font-style="italic">{k.esc(MOTTO)}</text>'
        )

    h = int(y + 16)

    css = "" if STATIC else f"""
    .r {{
      opacity: 0;
      animation: in {DUR}s cubic-bezier(.2,.7,.3,1) both;
    }}
    @keyframes in {{
      from {{ opacity: 0; transform: translateX(-10px); }}
      to   {{ opacity: 1; transform: translateX(0); }}
    }}"""

    return k.panel(W, h, f"{HEAD[0]}@{HEAD[1]}: ~/neofetch",
                   "\n".join(body), extra_css=css), h


def main():
    svg, h = build()
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT}  {W}x{h}  {os.path.getsize(OUT) / 1024:.1f} KB  "
          f"{'static' if STATIC else 'animated'}")


if __name__ == "__main__":
    main()
