"""Shared chrome for the three profile SVGs.

Everything renders on an explicit dark panel rather than a transparent
background. GitHub serves READMEs in both light and dark themes, and an
SVG loaded through <img> cannot read which one is active — light-grey
glyphs on a transparent background vanish in light mode. A self-contained
terminal panel looks identical either way.
"""

# GitHub's own dark canvas, so the panels sit naturally on a dark profile.
BG = "#0d1117"
BORDER = "#21262d"
BAR = "#161b22"
FG = "#c9d1d9"
DIM = "#6e7681"
ACCENT = "#6366f1"     # default accent; profile.yml overrides it
GREEN = "#39d353"

DOTS = ("#ff5f57", "#febc2e", "#28c840")

# No webfonts: GitHub blocks external stylesheets inside README SVGs, so
# this has to be a stack of faces that ship with the OS.
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'DejaVu Sans Mono','Liberation Mono',monospace")

BAR_H = 30


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def header(w, title, bar_h=BAR_H):
    """Terminal title bar: traffic lights plus a dimmed window title."""
    dots = "".join(
        f'<circle cx="{18 + i * 16}" cy="{bar_h / 2:.0f}" r="5" '
        f'fill="{c}" opacity="0.85"/>'
        for i, c in enumerate(DOTS)
    )
    return f"""  <rect x="0" y="0" width="{w}" height="{bar_h}" fill="{BAR}"/>
  <rect x="0" y="{bar_h - 1}" width="{w}" height="1" fill="{BORDER}"/>
  {dots}
  <text x="{w / 2:.0f}" y="{bar_h / 2 + 4:.0f}" text-anchor="middle"
        font-family="{MONO}" font-size="11" fill="{DIM}">{esc(title)}</text>"""


def panel(w, h, title, body, defs="", extra_css="", radius=10):
    """Wrap body markup in a rounded terminal window."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"
     viewBox="0 0 {w} {h}" role="img">
  <defs>
    <clipPath id="frame">
      <rect x="0" y="0" width="{w}" height="{h}" rx="{radius}" ry="{radius}"/>
    </clipPath>
{defs}
  </defs>
  <style>
    text {{ white-space: pre; }}
{extra_css}
  </style>
  <g clip-path="url(#frame)">
    <rect x="0" y="0" width="{w}" height="{h}" fill="{BG}"/>
{header(w, title)}
{body}
  </g>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{radius}"
        ry="{radius}" fill="none" stroke="{BORDER}"/>
</svg>
"""
