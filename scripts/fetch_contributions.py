#!/usr/bin/env python3
"""Scrape the public contribution calendar — no token, no GraphQL.

GitHub serves the same calendar fragment the profile page uses at
    https://github.com/users/<user>/contributions
as public HTML, so this needs no authentication and works unchanged
inside GitHub Actions.

Two details the markup imposes:
  * A day cell carries its date and level, but not its count. The count
    lives in a separate <tool-tip for="<cell id>"> element, so the two
    have to be joined by id.
  * Levels run 0-4. Anything expecting a level 5 is reading a different
    (older) version of this page.

Writes data/contributions.json: raw days plus the stats the renderer
prints in its footer.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

USER = config.owner()
URL = f"https://github.com/users/{USER}/contributions"
OUT = "data/contributions.json"

HEADERS = {
    "User-Agent": f"{USER}-profile-art (+https://github.com/{USER})",
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
}


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # id -> count, read off the tooltips.
    counts = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        m = re.match(r"\s*(\d+)\s+contribution", tip.get_text(strip=True))
        counts[target] = int(m.group(1)) if m else 0

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        cid = cell.get("id", "")
        days.append({
            "date": cell["data-date"],
            "level": int(cell.get("data-level", 0)),
            "count": counts.get(cid, 0),
        })

    days.sort(key=lambda d: d["date"])
    if not days:
        sys.exit("parsed zero days — GitHub markup probably changed")
    return days


def streaks(days):
    """Longest run of consecutive active days, and the run ending today."""
    active = {d["date"] for d in days if d["count"] > 0}

    longest = run = 0
    prev = None
    for d in days:
        if d["count"] > 0:
            run = run + 1 if prev else 1
            longest = max(longest, run)
            prev = True
        else:
            run, prev = 0, False

    # Current streak: walk back from today (yesterday counts, since today
    # may simply not have happened yet).
    today = date.today()
    cur = 0
    cursor = today if today.isoformat() in active else today - timedelta(days=1)
    while cursor.isoformat() in active:
        cur += 1
        cursor -= timedelta(days=1)

    return cur, longest


def main():
    days = parse(fetch(URL))

    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"])
    cur, longest = streaks(days)

    monthly = defaultdict(int)
    for d in days:
        monthly[d["date"][:7]] += d["count"]

    payload = {
        "user": USER,
        "generated": date.today().isoformat(),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "stats": {
            "total": total,
            "active_days": sum(1 for d in days if d["count"] > 0),
            "current_streak": cur,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
            "max_level": max(d["level"] for d in days),
        },
        "monthly": dict(sorted(monthly.items())),
        "days": days,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")

    s = payload["stats"]
    print(f"wrote {OUT}")
    print(f"  {len(days)} days  {payload['range']['from']} -> "
          f"{payload['range']['to']}")
    print(f"  {total} contributions, {s['active_days']} active days")
    print(f"  streak: current {cur}, longest {longest}")
    print(f"  best day: {s['best_day']['date']} "
          f"({s['best_day']['count']})")


if __name__ == "__main__":
    main()
