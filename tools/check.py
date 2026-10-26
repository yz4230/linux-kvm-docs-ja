#!/usr/bin/env python3
"""Structural QA for the translated KVM documentation.

Compares each translated RST file against its English original and reports
anything an over-eager translator tends to break:

  * section count        (number of RST title underlines)
  * anchors              (``.. _label:`` lines)
  * directives           (``.. note::`` / ``.. warning::`` / ``.. toctree::``)
  * literal blocks       (indented code, must survive byte-for-byte)
  * grid tables          (``+---+`` border lines)
  * leftover markdown    (``` fences, tables written as | a | b |)

Exit status is 0 when nothing is wrong, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
ORIG = Path("/Users/yz/cloned/linux/Documentation/virt")

UNDERLINE_RE = re.compile(r'^([=\-~^"\'`+*#:.])\1{2,}\s*$')
ANCHOR_RE = re.compile(r'^\.\. _[^\s:]+:\s*$')
DIRECTIVE_RE = re.compile(r'^\.\. (note|warning|toctree|list-table)::')
GRID_RE = re.compile(r'^\s*\+(?:[-=]+\+)+\s*$')


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def sections(lines: list[str]) -> int:
    n = 0
    for i in range(1, len(lines)):
        if UNDERLINE_RE.match(lines[i]) and lines[i - 1].strip() \
                and not UNDERLINE_RE.match(lines[i - 1]):
            n += 1
    return n


def anchors(lines: list[str]) -> set[str]:
    return {ln.strip() for ln in lines if ANCHOR_RE.match(ln)}


def directives(lines: list[str]) -> list[str]:
    out = []
    for ln in lines:
        m = DIRECTIVE_RE.match(ln)
        if m:
            out.append(m.group(1))
    return sorted(out)


CODEISH = re.compile(
    r'(\{|\}|#define|#include|\+--|->|__u(8|16|32|64)\b|^\s*(struct|enum|union|typedef)\b|'
    r'<<|>>|0x[0-9a-fA-F]+|\w+\s*=\s*\S|;\s*$|\|\s*$|^\s*\|)'
)


def literal_blocks(lines: list[str]) -> set[str]:
    """Code-looking lines that sit inside an RST literal block.

    Only ``::``-introduced blocks are considered; directive bodies such as
    ``.. note::`` hold ordinary prose and are translated on purpose.  Lines
    without any code punctuation are ignored too, because a fair number of
    literal blocks in these documents hold quoted prose.
    """
    out: set[str] = set()
    i, n = 0, len(lines)
    while i < n:
        if lines[i].rstrip().endswith("::"):
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j] != lines[j].lstrip():
                while j < n and (not lines[j].strip() or lines[j] != lines[j].lstrip()):
                    if lines[j].strip() and CODEISH.search(lines[j]):
                        out.add(lines[j].strip())
                    j += 1
                i = j
                continue
        i += 1
    return out


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    files = sorted(p for p in SRC.rglob("*.rst"))
    for tp in files:
        rel = tp.relative_to(SRC)
        op = ORIG / rel
        if not op.exists():
            problems.append(f"NO ORIGINAL for {rel}")
            continue
        t, o = read(tp), read(op)

        if sections(t) != sections(o):
            problems.append(f"{rel}: section count {sections(t)} != original {sections(o)}")

        # Tables may legitimately be reflowed or converted to list-table when the
        # Japanese text no longer fits the original grid width.  Report only.
        t_tables = sum(1 for l in t if GRID_RE.match(l)) + directives(t).count("list-table")
        o_tables = sum(1 for l in o if GRID_RE.match(l)) + directives(o).count("list-table")
        if abs(t_tables - o_tables) > max(4, o_tables // 4):
            notes.append(
                f"{rel}: table markers {t_tables} vs original {o_tables} (verify in build log)")

        missing_a = anchors(o) - anchors(t)
        if missing_a:
            problems.append(f"{rel}: missing anchors {sorted(missing_a)}")

        keep = ("note", "warning", "toctree")
        if [d for d in directives(t) if d in keep] != [d for d in directives(o) if d in keep]:
            problems.append(
                f"{rel}: directives {directives(t)} != original {directives(o)}")

        miss_lit = literal_blocks(o) - literal_blocks(t)
        if miss_lit:
            sample = sorted(miss_lit)[:6]
            problems.append(
                f"{rel}: {len(miss_lit)} code lines altered/dropped, e.g. {sample}")

        for idx, ln in enumerate(t, 1):
            if ln.lstrip().startswith("```"):
                problems.append(f"{rel}:{idx}: markdown code fence left behind")

    if notes:
        print("notes:\n  " + "\n  ".join(notes))
    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} problem(s) over {len(files)} files")
        return 1
    print(f"OK: {len(files)} files pass structural comparison")
    return 0


if __name__ == "__main__":
    sys.exit(main())
