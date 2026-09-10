#!/usr/bin/env python3
"""Check which anonymous Instagram viewers are still reachable.

Reads viewers.json and reports the status of each viewer's own website. These
tools go down and change domains often, so the point is to see which ones
still respond right now. The checker only fetches the viewer's homepage, never
Instagram itself.

Usage:
    python check_viewers.py                    # list the directory, no network
    python check_viewers.py --live             # check each URL, report up/down
    python check_viewers.py --markdown         # print a markdown table
    python check_viewers.py --live --markdown
    python check_viewers.py --live --record    # also append the run to history.json

Recording a run builds a timeline in history.json, which status_svg.py renders
as the status card in the README.
"""

import argparse
import json
import socket
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT = 8
HISTORY_FILE = "history.json"


def load_viewers(path="viewers.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("viewers", [])


def check_url(url, timeout=DEFAULT_TIMEOUT):
    """Return (state, detail) for one viewer URL. state is 'up' or 'down'."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ms = int((time.monotonic() - start) * 1000)
            return "up", f"{resp.status} ({ms} ms)"
    except urllib.error.HTTPError as e:
        return "down", f"HTTP {e.code}"
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            return "down", "timeout"
        return "down", "unreachable"
    except Exception:
        return "down", "error"


def check_all(viewers, timeout=DEFAULT_TIMEOUT):
    results = []
    for v in viewers:
        state, detail = check_url(v["url"], timeout)
        results.append((v, state, detail))
    return results


def record(results, path=HISTORY_FILE):
    """Append one run to the history file, creating it when it is missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        data = {"runs": []}

    data["runs"].append({
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": [{"name": v["name"], "state": state, "detail": detail} for v, state, detail in results],
    })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return len(data["runs"])


def render_terminal(viewers, live, timeout=DEFAULT_TIMEOUT, results=None):
    pad = max((len(v["name"]) for v in viewers), default=0)
    print(f"Anonymous Instagram viewer alternatives ({len(viewers)})")
    print()
    if live:
        if results is None:
            results = check_all(viewers, timeout)
        for v, state, detail in results:
            print(f"  {v['name']:<{pad}}  {state:<4}  {detail}")
        up = sum(1 for _, s, _ in results if s == "up")
        print()
        print(f"Summary: {up} up, {len(viewers) - up} down")
    else:
        for v in viewers:
            print(f"  {v['name']:<{pad}}  {v['url']}")
            if v.get("note"):
                print(f"  {'':<{pad}}  {v['note']}")


def render_markdown(viewers, live, timeout=DEFAULT_TIMEOUT, results=None):
    if live:
        if results is None:
            results = check_all(viewers, timeout)
        print("| Viewer | Status | URL | Note |")
        print("| --- | --- | --- | --- |")
        for v, state, detail in results:
            note = v.get("note", "")
            print(f"| {v['name']} | {state} ({detail}) | {v['url']} | {note} |")
    else:
        print("| Viewer | URL | Note |")
        print("| --- | --- | --- |")
        for v in viewers:
            print(f"| {v['name']} | {v['url']} | {v.get('note', '')} |")


def main():
    p = argparse.ArgumentParser(description="Check which anonymous Instagram viewers are still reachable.")
    p.add_argument("--live", action="store_true", help="fetch each viewer URL and report up/down")
    p.add_argument("--markdown", action="store_true", help="emit a markdown table instead of plain text")
    p.add_argument("--file", default="viewers.json", help="path to the viewers JSON (default viewers.json)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="request timeout in seconds (default 8)")
    p.add_argument("--record", action="store_true", help="append this run to the history file (implies --live)")
    p.add_argument("--history", default=HISTORY_FILE, help=f"history file to append to (default {HISTORY_FILE})")
    args = p.parse_args()

    live = args.live or args.record

    try:
        viewers = load_viewers(args.file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"could not load {args.file}: {e}")
        return 1

    if not viewers:
        print(f"no viewers found in {args.file}")
        return 1

    results = check_all(viewers, args.timeout) if args.record else None

    if args.markdown:
        render_markdown(viewers, live, args.timeout, results)
    else:
        render_terminal(viewers, live, args.timeout, results)

    if results is not None:
        print()
        print(f"recorded run {record(results, args.history)} in {args.history}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
