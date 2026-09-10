#!/usr/bin/env python3
"""Validate viewers.json against the schema the other scripts expect.

Every script in this repository reads viewers.json, so a typo in the data file
breaks them quietly: a missing field turns into a KeyError, a malformed URL
turns into a failed check, and a duplicate name hides a real entry. This script
reports each problem by entry, so you can fix the file before it costs you a
run.

Usage:
    python validate.py                 # validate viewers.json
    python validate.py other.json      # validate another file

Exits 0 when the file is clean and 1 when it is not.
"""

import json
import re
import sys
from urllib.parse import urlparse

DEFAULT_FILE = "viewers.json"

REQUIRED_FIELDS = ("name", "url", "note", "supports")
KNOWN_FIELDS = set(REQUIRED_FIELDS)
TAG_RE = re.compile(r"^[a-z][a-z0-9-]{1,23}$")


def problems_for(index, viewer):
    """Return the list of problem strings for one viewer entry."""
    where = f"viewers[{index}]"

    if not isinstance(viewer, dict):
        return [f"{where}: expected an object, found {type(viewer).__name__}"]

    name = viewer.get("name")
    label = f'{where} ("{name}")' if isinstance(name, str) and name else where
    out = []

    for field in REQUIRED_FIELDS:
        if field not in viewer:
            out.append(f"{label}: missing {field}")
        elif viewer[field] is None:
            out.append(f"{label}: {field} is null")
        elif isinstance(viewer[field], str) and not viewer[field].strip():
            out.append(f"{label}: {field} is empty")

    if isinstance(name, str) and name and name != name.strip():
        out.append(f"{label}: name has leading or trailing whitespace")

    url = viewer.get("url")
    if isinstance(url, str) and url:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            out.append(f"{label}: url must start with http:// or https:// ({url})")
        elif not parsed.netloc:
            out.append(f"{label}: url has no domain ({url})")

    supports = viewer.get("supports")
    if isinstance(supports, list):
        if not supports:
            out.append(f"{label}: supports is empty, give it at least one tag")
        seen = set()
        for tag in supports:
            if not isinstance(tag, str):
                out.append(f"{label}: supports entries must be strings, found {type(tag).__name__}")
            elif not TAG_RE.match(tag):
                out.append(f'{label}: "{tag}" is not a valid tag, use lowercase letters, digits, and hyphens')
            elif tag in seen:
                out.append(f'{label}: duplicate tag "{tag}"')
            else:
                seen.add(tag)
    elif "supports" in viewer:
        out.append(f"{label}: supports must be a list, found {type(supports).__name__}")

    note = viewer.get("note")
    if isinstance(note, str) and len(note) > 120:
        out.append(f"{label}: note is {len(note)} characters, keep it short for the terminal table")

    return out


def warnings_for(index, viewer):
    """Return the list of non-fatal warning strings for one viewer entry."""
    if not isinstance(viewer, dict):
        return []
    name = viewer.get("name")
    label = f'viewers[{index}] ("{name}")' if isinstance(name, str) and name else f"viewers[{index}]"
    return [f"{label}: unexpected field {key}" for key in viewer if key not in KNOWN_FIELDS]


def duplicate_problems(viewers):
    """Return problems for names and domains that appear more than once."""
    out = []
    by_name = {}
    by_domain = {}

    for index, viewer in enumerate(viewers):
        if not isinstance(viewer, dict):
            continue

        name = viewer.get("name")
        if isinstance(name, str) and name.strip():
            key = name.strip().lower()
            if key in by_name:
                out.append(f'viewers[{index}] ("{name}"): duplicate name, first seen at viewers[{by_name[key]}]')
            else:
                by_name[key] = index

        url = viewer.get("url")
        if isinstance(url, str) and url:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            if not domain:
                continue
            if domain in by_domain:
                out.append(f'viewers[{index}] ("{name}"): duplicate domain {domain}, first seen at viewers[{by_domain[domain]}]')
            else:
                by_domain[domain] = index

    return out


def collect_tags(viewers):
    """Return every tag used in the file, sorted."""
    tags = set()
    for viewer in viewers:
        if isinstance(viewer, dict) and isinstance(viewer.get("supports"), list):
            tags.update(t for t in viewer["supports"] if isinstance(t, str))
    return sorted(tags)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"could not find {path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"{path} is not valid JSON: {e}")
        return 1

    if not isinstance(data, dict):
        print(f'{path}: top level must be an object with a "viewers" key')
        return 1

    viewers = data.get("viewers")
    if not isinstance(viewers, list):
        print(f'{path}: missing a "viewers" list')
        return 1
    if not viewers:
        print(f"{path}: the viewers list is empty")
        return 1

    problems = []
    warnings = []
    for index, viewer in enumerate(viewers):
        problems.extend(problems_for(index, viewer))
        warnings.extend(warnings_for(index, viewer))
    problems.extend(duplicate_problems(viewers))

    for warning in warnings:
        print(f"warning: {warning}")
    for problem in problems:
        print(f"problem: {problem}")

    if problems:
        print()
        print(f"{path}: {len(problems)} problem(s) across {len(viewers)} entries")
        return 1

    tags = collect_tags(viewers)
    print(f"{path}: OK, {len(viewers)} entries")
    print(f"tags: {', '.join(tags) if tags else 'none'}")
    if warnings:
        print(f"{len(warnings)} warning(s), see above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
