#!/usr/bin/env python3
"""Render data/contributions.json as an animated 53-week calendar.

The grid reveals itself diagonally — each box is delayed by (col + row),
so the wave sweeps from the top-left corner — then freezes. It plays once
on load; there is no looping glow, which reads as a broken page element
after the first second.

Grid position is derived from each date (weekday = row, week index =
column) rather than from GitHub's element ids, so a markup change upstream
cannot silently transpose the calendar.

    python scripts/render_heatmap_svg.py
    STATIC=1 python scripts/render_heatmap_svg.py
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgkit as k

SRC = "data/contributions.json"
OUT = os.environ.get("OUT", "contrib-heatmap.svg")
STATIC = os.environ.get("STATIC") == "1"

# GitHub emits levels 0-4 only. PEAK is this renderer's own addition: the
# single best day of the year gets a brighter box than the scale allows.
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
PEAK = "#69f0a0"

BOX, GAP = 11, 3
CELL = BOX + GAP
LEFT = 30            # room for the weekday labels
TOP = 20             # room for the month labels
PAD_X = 18
STEP = 0.014         # per-diagonal delay
DUR = 0.42

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}


def grid(days):
    """Map each day onto (col, row), Sunday-first like GitHub's own grid."""
    first = date.fromisoformat(days[0]["date"])
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
    out = []
    for d in days:
        dt = date.fromisoformat(d["date"])
        delta = (dt - start).days
        out.append((delta // 7, delta % 7, dt, d))
    return out, start


def build(payload):
    days = payload["days"]
    cells, start = grid(days)
    cols = max(c for c, _, _, _ in cells) + 1
    peak = payload["stats"]["best_day"]

    gw = cols * CELL - GAP
    w = int(PAD_X * 2 + LEFT + gw)

    body = []
    y0 = k.BAR_H + 14

    # Month labels, at the first column of each month.
    seen = set()
    for col, row, dt, _ in cells:
        if dt.month not in seen and dt.day <= 7:
            seen.add(dt.month)
            x = PAD_X + LEFT + col * CELL
            if x < w - 30:
                body.append(
                    f'    <text x="{x}" y="{y0 + 10}" font-family="{k.MONO}" '
                    f'font-size="9.5" fill="{k.DIM}">'
                    f'{MONTHS[dt.month - 1]}</text>'
                )

    gy = y0 + TOP

    for row, label in DAY_LABELS.items():
        body.append(
            f'    <text x="{PAD_X}" y="{gy + row * CELL + BOX - 2}" '
            f'font-family="{k.MONO}" font-size="9.5" fill="{k.DIM}">'
            f'{label}</text>'
        )

    for col, row, dt, d in cells:
        x = PAD_X + LEFT + col * CELL
        y = gy + row * CELL
        is_peak = (d["date"] == peak["date"] and peak["count"] > 0)
        fill = PEAK if is_peak else PALETTE[min(d["level"], len(PALETTE) - 1)]
        attrs = ""
        if not STATIC:
            attrs = f' class="b" style="animation-delay:{(col + row) * STEP:.3f}s"'
        # title makes each box hoverable in the browser, and readable to
        # a screen reader, without any JavaScript.
        n = d["count"]
        label = "No contributions" if not n else \
            f"{n} contribution{'s' if n != 1 else ''}"
        body.append(
            f'    <rect{attrs} x="{x}" y="{y}" width="{BOX}" height="{BOX}" '
            f'rx="2.5" fill="{fill}"><title>{label} on {d["date"]}</title>'
            f'</rect>'
        )

    fy = gy + 7 * CELL + 18

    # Legend, anchored to the right edge and laid out leftward, so it
    # cannot run past the panel however wide the grid ends up.
    lsw = BOX - 1
    lgap = 4
    boxes_w = len(PALETTE) * lsw + (len(PALETTE) - 1) * lgap
    right = w - PAD_X
    body.append(
        f'    <text x="{right}" y="{fy + 8}" text-anchor="end" '
        f'font-family="{k.MONO}" font-size="9.5" fill="{k.DIM}">More</text>'
    )
    bx = right - 28 - boxes_w
    for i, c in enumerate(PALETTE):
        body.append(
            f'    <rect x="{bx + i * (lsw + lgap)}" y="{fy}" '
            f'width="{lsw}" height="{lsw}" rx="2" fill="{c}"/>'
        )
    body.append(
        f'    <text x="{bx - 6}" y="{fy + 8}" text-anchor="end" '
        f'font-family="{k.MONO}" font-size="9.5" fill="{k.DIM}">Less</text>'
    )

    # Footer stats, left-aligned under the grid.
    s = payload["stats"]
    body.append(
        f'    <text x="{PAD_X}" y="{fy + 8}" font-family="{k.MONO}" '
        f'font-size="10.5" fill="{k.FG}">'
        f'<tspan fill="{k.GREEN}" font-weight="700">{s["total"]}</tspan>'
        f'<tspan fill="{k.DIM}"> contributions in the last year · </tspan>'
        f'<tspan>{s["active_days"]}</tspan>'
        f'<tspan fill="{k.DIM}"> active days · longest streak </tspan>'
        f'<tspan>{s["longest_streak"]}</tspan>'
        f'</text>'
    )

    h = int(fy + 24)

    css = "" if STATIC else f"""
    .b {{
      opacity: 0;
      transform-box: fill-box;
      transform-origin: center;
      animation: pop {DUR}s cubic-bezier(.2,.8,.3,1) both;
    }}
    @keyframes pop {{
      from {{ opacity: 0; transform: translateY(-6px) scale(.5); }}
      to   {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}"""

    user = payload.get("user", "you")
    title = f"{user}@github: ~/contributions --year {date.today().year}"
    return k.panel(w, h, title, "\n".join(body), extra_css=css), w, h, cols


def main():
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC} — run scripts/fetch_contributions.py first")

    payload = json.load(open(SRC))
    svg, w, h, cols = build(payload)
    with open(OUT, "w") as f:
        f.write(svg)

    print(f"wrote {OUT}  {w}x{h}  {cols} weeks  "
          f"{os.path.getsize(OUT) / 1024:.0f} KB  "
          f"{'static' if STATIC else 'animated'}")


if __name__ == "__main__":
    main()
