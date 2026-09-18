#!/usr/bin/env python3
"""Write the art block into README.md with correct display widths.

The two side-by-side panels only line up if their displayed heights match,
and the card's height depends on how many rows someone put in profile.yml.
Hardcoding widths therefore works for exactly one profile: change the card
and the columns go ragged. So the widths are solved from the rendered SVGs
on every build, and injected between the markers below.

Anything outside the markers is yours; this script never touches it.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

README = "README.md"
START = "<!-- profile-forge:start -->"
END = "<!-- profile-forge:end -->"

PORTRAIT = "ascii-portrait.svg"
CARD = "info-card.svg"
HEATMAP = "contrib-heatmap.svg"

ROW_TOTAL = 850    # combined width of the two panels
HEAT_W = 860       # heatmap display width


def size(path):
    s = open(path).read()
    return (int(re.search(r'<svg[^>]*\swidth="(\d+)"', s).group(1)),
            int(re.search(r'<svg[^>]*\sheight="(\d+)"', s).group(1)))


def main():
    missing = [f for f in (PORTRAIT, CARD, HEATMAP) if not os.path.exists(f)]
    if missing:
        sys.exit(f"missing {', '.join(missing)} — run the generators first")

    cfg = config.load()
    (pw, ph), (cw, ch) = size(PORTRAIT), size(CARD)

    # Equal displayed height: w/aspect must match, and the two sum to ROW_TOTAL.
    pa, ca = pw / ph, cw / ch
    p_disp = round(ROW_TOTAL * pa / (pa + ca))
    c_disp = ROW_TOTAL - p_disp

    prompt = f'{cfg["user"]}@github ~ $'
    block = f"""{START}
<div align="center">

<h3><code>{prompt} ./contributions.sh</code></h3>

<img src="./{HEATMAP}" width="{HEAT_W}" alt="Contribution heatmap, refreshed daily" />

<br><br>

<h3><code>{prompt} whoami</code></h3>

<table>
  <tr>
    <td valign="top"><img src="./{PORTRAIT}" width="{p_disp}" alt="ASCII portrait" /></td>
    <td valign="top"><img src="./{CARD}" width="{c_disp}" alt="Info card" /></td>
  </tr>
</table>

</div>
{END}"""

    text = open(README).read()
    if START not in text or END not in text:
        sys.exit(f"{README} has no {START} / {END} markers to write into")

    out = re.sub(re.escape(START) + r".*?" + re.escape(END), block,
                 text, flags=re.S)
    if out != text:
        open(README, "w").write(out)

    print(f"updated {README}")
    print(f"  portrait {pw}x{ph} -> width={p_disp} ({p_disp / pa:.0f}px tall)")
    print(f"  card     {cw}x{ch} -> width={c_disp} ({c_disp / ca:.0f}px tall)")


if __name__ == "__main__":
    main()
