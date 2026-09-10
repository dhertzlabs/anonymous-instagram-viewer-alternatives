#!/usr/bin/env python3
"""Pick a viewer from the directory for the job you actually have.

The directory in viewers.json tags each viewer with what it supports, so you can
ask for the job in hand and get the entries that do it, broadest first. This
reads the data file only and never touches the network: run check_viewers.py
--live afterwards to see which of the picks are reachable right now.

Usage:
    python picker.py                       # ask what you need
    python picker.py --need stories        # entries that do one thing
    python picker.py --need stories,reels  # entries that do all of them
    python picker.py --need stories,reels --any   # entries that do any of them
    python picker.py --list                # every viewer and its tags
"""

import argparse
import json

DEFAULT_FILE = "viewers.json"


def load_viewers(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [v for v in data.get("viewers", []) if isinstance(v, dict)]


def tags_of(viewer):
    return {t for t in viewer.get("supports", []) if isinstance(t, str)}


def available_tags(viewers):
    tags = set()
    for viewer in viewers:
        tags.update(tags_of(viewer))
    return sorted(tags)


def parse_needs(raw, known):
    """Split a comma list into tags, or return (None, unknown) if any are new."""
    wanted = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = [tag for tag in wanted if tag not in known]
    return wanted, unknown


def select(viewers, needs, match_all):
    """Return (viewer, tags, matched) rows, best match first."""
    rows = []
    for index, viewer in enumerate(viewers):
        tags = tags_of(viewer)
        if not needs:
            rows.append((viewer, tags, 0, index))
            continue
        matched = tags & set(needs)
        if (matched == set(needs)) if match_all else bool(matched):
            rows.append((viewer, tags, len(matched), index))
    rows.sort(key=lambda row: (-row[2], -len(row[1]), row[3]))
    return rows


def print_rows(rows, needs, total):
    if not rows:
        print("No viewer in the directory matches that.")
        if needs:
            print("Try --any to accept a partial match, or --list to see every tag in use.")
        return

    pad = max(len(v.get("name", "")) for v, _, _, _ in rows)
    for viewer, tags, matched, _ in rows:
        name = viewer.get("name", "")
        note = viewer.get("note", "")
        print(f"  {name:<{pad}}  {note}")
        print(f"  {'':<{pad}}  {viewer.get('url', '')}")
        if needs and matched < len(tags):
            print(f"  {'':<{pad}}  matches: {', '.join(sorted(set(needs) & tags))}")
        print()

    print(f"{len(rows)} of {total} viewers. Run check_viewers.py --live to see which are reachable now.")


def print_directory(viewers):
    pad = max((len(v.get("name", "")) for v in viewers), default=0)
    for viewer in viewers:
        tags = ", ".join(sorted(tags_of(viewer))) or "untagged"
        print(f"  {viewer.get('name', ''):<{pad}}  {viewer.get('note', '')}")
        print(f"  {'':<{pad}}  {tags}")
    print()
    print(f"{len(viewers)} viewers, tags: {', '.join(available_tags(viewers))}")


def main():
    p = argparse.ArgumentParser(description="Pick a viewer from viewers.json for the job you have.")
    p.add_argument("--need", help="comma-separated tags, for example stories,reels")
    p.add_argument("--any", action="store_true", help="accept a partial match instead of requiring every tag")
    p.add_argument("--list", action="store_true", help="list every viewer and its tags, then exit")
    p.add_argument("--file", default=DEFAULT_FILE, help=f"path to the viewers JSON (default {DEFAULT_FILE})")
    args = p.parse_args()

    try:
        viewers = load_viewers(args.file)
    except FileNotFoundError:
        print(f"could not find {args.file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"could not load {args.file}: {e}")
        return 1

    if not viewers:
        print(f"no viewers found in {args.file}")
        return 1

    known = available_tags(viewers)

    if args.list:
        print_directory(viewers)
        return 0

    needs = []
    if args.need is not None:
        needs, unknown = parse_needs(args.need, known)
        if unknown:
            print(f"unknown tag(s): {', '.join(unknown)}")
            print(f"tags in use: {', '.join(known)}")
            return 1
    else:
        print("What do you need? Pick one or more, separated by commas.")
        print(f"  {', '.join(known)}")
        try:
            answer = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if answer:
            needs, unknown = parse_needs(answer, known)
            if unknown:
                print(f"unknown tag(s): {', '.join(unknown)}")
                print(f"tags in use: {', '.join(known)}")
                return 1

    if not needs:
        print("Nothing chosen, showing the whole directory.")
        print()

    print_rows(select(viewers, needs, not args.any), needs, len(viewers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
