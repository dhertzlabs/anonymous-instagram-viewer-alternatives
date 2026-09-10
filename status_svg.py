#!/usr/bin/env python3
"""Render the latest recorded run as status.svg, a status card for the README.

check_viewers.py --live --record appends one row per run to history.json. This
script turns the most recent run into a self-contained SVG, which GitHub renders
inline in a README, so the card shows the current state of the directory every
time you re-record and commit.

A viewer is not simply up or down. A tool that answers with HTTP 403 is running
and refusing automated requests, which is not the same as a domain that no
longer resolves, so the card marks those two cases differently.

Usage:
    python status_svg.py                        # read history.json, write status.svg
    python status_svg.py --out docs/status.svg  # write it somewhere else
"""

import argparse
import json
import time
from xml.sax.saxutils import escape

WIDTH = 780
PAD = 24
ROW_H = 26
HEAD_H = 78
FOOT_H = 40

UP = "#3fb950"
BLOCKED = "#d29922"
NO_RESPONSE = "#f85149"
TITLE = "#8b949e"
FAINT = "#6e7681"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def classify(state, detail):
    """Return (label, color) for one check result."""
    if state == "up":
        return "up", UP
    if detail.startswith("HTTP"):
        return "blocked", BLOCKED
    return "no response", NO_RESPONSE


def format_stamp(raw):
    """Turn 2026-09-10T12:00:00Z into 2026-09-10 12:00 UTC."""
    try:
        return time.strftime("%Y-%m-%d %H:%M UTC", time.strptime(str(raw), "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return str(raw)


def render(run):
    """Return the SVG document for one recorded run."""
    results = run.get("results") or []
    rows = len(results)
    height = HEAD_H + rows * ROW_H + FOOT_H
    reachable = sum(1 for r in results if r.get("state") == "up")
    stamp = escape(format_stamp(run.get("at", "")))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="Anonymous Instagram viewer status: {reachable} of {rows} reachable">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="8" '
        f'fill="none" stroke="{TITLE}" stroke-opacity="0.35"/>',
        f'<text x="{PAD}" y="40" font-family="{FONT}" font-size="17" font-weight="600" '
        f'fill="{TITLE}">Anonymous Instagram viewer status</text>',
        f'<text x="{WIDTH - PAD}" y="40" font-family="{FONT}" font-size="12" '
        f'text-anchor="end" fill="{FAINT}">{stamp} &#183; {reachable} of {rows} reachable</text>',
    ]

    y = HEAD_H
    for result in results:
        label, color = classify(result.get("state", ""), str(result.get("detail", "")))
        name = escape(str(result.get("name", "")))
        detail = escape(str(result.get("detail", "")))
        out.append(f'<circle cx="{PAD + 5}" cy="{y - 4}" r="5" fill="{color}"/>')
        out.append(f'<text x="{PAD + 20}" y="{y}" font-family="{FONT}" font-size="13" '
                   f'fill="{TITLE}">{name}</text>')
        out.append(f'<text x="{WIDTH - PAD}" y="{y}" font-family="{FONT}" font-size="12" '
                   f'text-anchor="end" fill="{FAINT}">{label} &#183; {detail}</text>')
        y += ROW_H

    out.append(f'<text x="{PAD}" y="{height - 16}" font-family="{FONT}" font-size="11" '
               f'fill="{FAINT}">Latest run from history.json. '
               f'Refresh with check_viewers.py --live --record.</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description="Render the latest recorded run as status.svg.")
    p.add_argument("--history", default="history.json", help="path to the history file (default history.json)")
    p.add_argument("--out", default="status.svg", help="path to write the SVG (default status.svg)")
    args = p.parse_args()

    try:
        with open(args.history, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"could not find {args.history}")
        print("run: python check_viewers.py --live --record")
        return 1
    except json.JSONDecodeError as e:
        print(f"could not load {args.history}: {e}")
        return 1

    runs = data.get("runs") if isinstance(data, dict) else None
    if not runs:
        print(f"no runs recorded in {args.history}")
        print("run: python check_viewers.py --live --record")
        return 1

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(runs[-1]))

    print(f"wrote {args.out} from {len(runs)} recorded run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
