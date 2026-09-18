#!/usr/bin/env python3
"""Check the generated SVGs before they reach a profile page.

Every failure here is one that is invisible until someone else looks at your
profile: a legend running off the right edge, a panel that only renders in
dark mode, an accidental external reference that turns into a broken-image
icon when that host goes down.

Runs in CI on every build. Exits non-zero on the first real problem.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

FILES = ("ascii-portrait.svg", "info-card.svg", "contrib-heatmap.svg")

problems = []
notes = []


def bounds(svg):
    """Horizontal extent of everything drawn, in user units.

    Text advance is estimated from textLength where present, and from
    font-size * 0.6 otherwise -- the advance of every monospace face worth
    naming. text-anchor is honoured, since that is exactly what a
    right-aligned legend depends on.
    """
    spans = []

    for m in re.finditer(r'<rect[^>]*?x="([\d.-]+)"[^>]*?width="([\d.]+)"', svg):
        x, w = float(m.group(1)), float(m.group(2))
        spans.append((x, x + w))

    for m in re.finditer(r'<text([^>]*)>(.*?)</text>', svg, re.S):
        attrs, body = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
        xm = re.search(r'\sx="([\d.-]+)"', attrs)
        if not xm:
            continue
        x = float(xm.group(1))
        tl = re.search(r'textLength="([\d.]+)"', attrs)
        fs = re.search(r'font-size="([\d.]+)"', attrs)
        adv = float(tl.group(1)) if tl else \
            len(body) * (float(fs.group(1)) if fs else 12.0) * 0.6
        if 'text-anchor="end"' in attrs:
            spans.append((x - adv, x))
        elif 'text-anchor="middle"' in attrs:
            spans.append((x - adv / 2, x + adv / 2))
        else:
            spans.append((x, x + adv))

    return spans


for name in FILES:
    if not os.path.exists(name):
        problems.append(f"{name}: missing — did the generator run?")
        continue

    svg = open(name).read()

    try:
        ET.fromstring(svg)
    except ET.ParseError as e:
        problems.append(f"{name}: not valid XML — {e}")
        continue

    if re.search(r"<script\b", svg, re.I):
        problems.append(f"{name}: contains <script>, which GitHub strips")

    external = re.findall(r'(?:xlink:href|href|src)="(?!#)([^"]+)"', svg)
    if external:
        problems.append(f"{name}: references something external: {external[:3]}")

    if "@import" in svg or "fonts.googleapis" in svg:
        problems.append(f"{name}: pulls in a webfont, which will not load")

    # A panel with no opaque background is invisible in one GitHub theme.
    if not re.search(r'<rect[^>]*fill="#[0-9a-fA-F]{6}"', svg):
        problems.append(f"{name}: no opaque background rect — it will "
                        f"disappear in one of GitHub's two themes")

    W = int(re.search(r'<svg[^>]*\swidth="(\d+)"', svg).group(1))
    H = int(re.search(r'<svg[^>]*\sheight="(\d+)"', svg).group(1))

    spans = [(a, b) for a, b in bounds(svg) if (b - a) < W * 0.9]
    if spans:
        lo = min(a for a, _ in spans)
        hi = max(b for _, b in spans)
        if lo < -1 or hi > W + 1:
            problems.append(
                f"{name}: content runs from x={lo:.0f} to x={hi:.0f}, "
                f"outside the {W}px panel — something will be clipped")
        else:
            notes.append(f"{name}: {W}x{H}, margins {lo:.0f} / {W - hi:.0f}")

    if not re.search(r'<(?:animate|set)\b', svg) and "@keyframes" not in svg:
        notes.append(f"{name}: no animation found (fine if STATIC=1)")

    kb = os.path.getsize(name) / 1024
    if kb > 900:
        problems.append(f"{name}: {kb:.0f} KB is too heavy for a README; "
                        f"lower ascii_columns in profile.yml")

for n in notes:
    print(f"  {n}")

if problems:
    print("\nverify failed:", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)

print(f"\nverify OK — {len(FILES)} self-contained SVGs, nothing clipped")
