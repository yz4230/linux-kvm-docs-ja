#!/usr/bin/env python3
"""Translate-artifact post-processing for the KVM Japanese docs build.

Does three things, all idempotent:
  1. joins the api.rst chunks in order into source/api.rst
  2. strips markdown code fences an agent may have added by mistake
  3. normalises RST section underlines so the underline is at least as long
     as its title (docutils errors out on short underlines), touching only
     unindented text so literal blocks and grid tables stay untouched.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
CHUNKS = ROOT / "chunks"

UNDERLINE_CHARS = set('=-~^"\'`+*#:')
UNDERLINE_RE = re.compile(r'^([%s])\1{2,}\s*$' % re.escape(''.join(UNDERLINE_CHARS)))


def join_api_chunks() -> str:
    files = sorted(CHUNKS.glob("api_*.rst"))
    if not files:
        return "no api chunks found"
    parts = []
    for f in files:
        text = f.read_text(encoding="utf-8").rstrip("\n")
        parts.append(text)
    out = "\n\n".join(p for p in parts if p) + "\n"
    (SRC / "api.rst").write_text(out, encoding="utf-8")
    return f"joined {len(files)} chunks -> source/api.rst ({len(out.splitlines())} lines)"


def strip_fences(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "```" not in text:
        return False
    lines = text.split("\n")
    out = [ln for ln in lines if not ln.lstrip().startswith("```")]
    path.write_text("\n".join(out), encoding="utf-8")
    return True


def fix_underlines(path: Path) -> list[tuple[int, str, int, int]]:
    lines = path.read_text(encoding="utf-8").split("\n")
    fixed = []
    changed = False
    for i in range(1, len(lines)):
        m = UNDERLINE_RE.match(lines[i])
        if not m:
            continue
        title = lines[i - 1]
        if not title.strip() or title != title.lstrip():
            continue
        if UNDERLINE_RE.match(title):  # over/underline pair, leave as is
            continue
        if title.lstrip().startswith(".. "):
            continue
        char = m.group(1)
        if len(lines[i].rstrip()) < len(title.rstrip()):
            fixed.append((i + 1, char, len(lines[i].rstrip()), len(title.rstrip())))
            lines[i] = char * len(title.rstrip())
            changed = True
    if changed:
        path.write_text("\n".join(lines), encoding="utf-8")
    return fixed


def main() -> int:
    msgs = [join_api_chunks()]
    targets = sorted(p for p in SRC.rglob("*") if p.is_file())
    for p in targets:
        if strip_fences(p):
            msgs.append(f"stripped code fences: {p.relative_to(ROOT)}")
        fixed = fix_underlines(p)
        for line_no, char, old, new in fixed:
            msgs.append(
                f"underline fixed: {p.relative_to(ROOT)}:{line_no} {old}->{new} ({char!r})"
            )
    print("\n".join(msgs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
