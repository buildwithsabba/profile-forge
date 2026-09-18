"""Load and validate profile.yml.

This file is the only thing most people will ever edit, and many of them
will edit it in the GitHub web editor with no way to run anything locally.
So every failure here has to explain itself in plain language and name the
file and key at fault: a stack trace in an Actions log is a dead end for
someone who just wanted a nice profile page.
"""
import glob
import os
import sys

import yaml

CONFIG = os.environ.get("PROFILE_CONFIG", "profile.yml")

# Photo extensions worth trying, in preference order. HEIC is first-class:
# it is what an iPhone produces by default, and this repo is aimed at people
# who will upload straight from their phone.
PHOTO_EXTS = ("jpg", "jpeg", "png", "heic", "heif", "webp")

DEFAULTS = {
    "user": "you",
    "host": "github",
    "card": [],
    "motto": "",
    "photo": "",
    "accent": "#6366f1",
    "swatches": ["#6366f1", "#818cf8", "#a5b4fc", "#39d353", "#26a641",
                 "#006d32", "#febc2e", "#ff5f57"],
    "ascii_columns": 100,
}


def die(message, hint=""):
    print(f"\n  {CONFIG}: {message}", file=sys.stderr)
    if hint:
        print(f"  -> {hint}", file=sys.stderr)
    print(file=sys.stderr)
    sys.exit(1)


def find_photo(configured=""):
    """Locate the portrait: the configured path, else assets/photo.*"""
    if configured:
        if os.path.exists(configured):
            return configured
        die(f"photo: points at '{configured}', which is not in this repo",
            "Either fix the path or delete the 'photo:' line and name your "
            "file assets/photo.jpg")

    for ext in PHOTO_EXTS:
        for path in sorted(glob.glob(f"assets/photo.{ext}")) + \
                sorted(glob.glob(f"assets/photo.{ext.upper()}")):
            return path

    die("no portrait found in assets/",
        "Upload your photo as assets/photo.jpg (png, heic and webp also "
        "work). One face, looking at the camera, works best.")


def rows(card):
    """Normalise the card into (label, value) pairs.

    Each entry is a single-key mapping, which keeps the YAML readable:

        card:
          - Role: AI Builder
          - "": second line of the row above
    """
    out = []
    for i, entry in enumerate(card, 1):
        if isinstance(entry, str):
            # Someone wrote "- Role: value" as a plain string, or just text.
            label, _, value = entry.partition(":")
            out.append((label.strip() if value else "", (value or label).strip()))
            continue
        if not isinstance(entry, dict) or len(entry) != 1:
            die(f"card entry {i} is not a single 'Label: value' pair",
                'Write each row as one line, e.g.  - Role: AI Builder')
        (label, value), = entry.items()
        out.append(("" if label is None else str(label).strip(),
                    "" if value is None else str(value).strip()))
    return out


def load():
    if not os.path.exists(CONFIG):
        die("file not found",
            "Copy profile.example.yml to profile.yml and fill it in.")

    try:
        raw = yaml.safe_load(open(CONFIG)) or {}
    except yaml.YAMLError as e:
        die(f"is not valid YAML\n\n{e}",
            "Usually a missing quote, or a value containing a ':' that "
            'needs quoting: - Now: "building: the thing"')

    if not isinstance(raw, dict):
        die("should be a list of settings, not a single value")

    unknown = set(raw) - set(DEFAULTS)
    if unknown:
        die(f"unknown setting(s): {', '.join(sorted(unknown))}",
            f"Valid settings are: {', '.join(sorted(DEFAULTS))}")

    cfg = {**DEFAULTS, **{k: v for k, v in raw.items() if v is not None}}

    if not cfg["card"]:
        die("'card' has no rows",
            "Add at least one, e.g.  - Role: what you do")

    cfg["rows"] = rows(cfg["card"])
    cfg["photo"] = find_photo(cfg["photo"])

    for key in ("user", "host", "motto"):
        cfg[key] = str(cfg[key]).strip()

    if not str(cfg["accent"]).startswith("#"):
        die(f"accent: '{cfg['accent']}' is not a hex colour",
            'Use a value like "#6366f1"')

    # If someone picks an accent but leaves the palette strip alone, lead
    # the strip with their colour. Otherwise an orange card still prints an
    # indigo palette, which reads as a bug rather than a default.
    if "swatches" not in raw and cfg["accent"] != DEFAULTS["accent"]:
        cfg["swatches"] = [cfg["accent"]] + \
            [c for c in DEFAULTS["swatches"] if c != DEFAULTS["accent"]][:7]

    return cfg


def owner():
    """The GitHub account the heatmap belongs to.

    In Actions this comes free from the repository itself, which keeps the
    template working for everyone without anyone editing a username.
    """
    for var in ("GH_USER", "GITHUB_REPOSITORY_OWNER"):
        if os.environ.get(var):
            return os.environ[var]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        return repo.split("/")[0]
    try:
        return load()["host"]
    except SystemExit:
        die("cannot tell which GitHub account to read contributions for",
            "Run with GH_USER=yourusername, or let GitHub Actions do it.")


if __name__ == "__main__":
    c = load()
    print(f"config OK: {CONFIG}")
    print(f"  user@host : {c['user']}@{c['host']}")
    print(f"  photo     : {c['photo']}")
    print(f"  card rows : {len(c['rows'])}")
    print(f"  accent    : {c['accent']}")
