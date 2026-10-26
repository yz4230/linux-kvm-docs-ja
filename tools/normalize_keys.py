#!/usr/bin/env python3
"""Make RST field-list / definition-list keys consistent across the translation.

The English originals use a fixed set of structural keys (``:Capability:``,
``:Architectures:``, ``:Parameters:``, ``Groups:`` ...).  Most agents kept them
in English, a few translated them.  This script rewrites the translated
variants back to the English keys, then verifies per file that the resulting
key multiset matches the original file exactly.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
ORIG = Path("/Users/yz/cloned/linux/Documentation/virt/kvm")

KEY_MAP = {
    "アーキテクチャ": "Architectures",
    "ケイパビリティ": "Capability",
    "パラメータ": "Parameters",
    "戻り値": "Returns",
    "種別": "Type",
    "目的": "Purpose",
    "状態": "Status",
    "保護対象": "Protects",
    "コメント": "Comment",
    "使用例": "Usage example",
}

TERM_MAP = {
    "グループ": "Groups",
    "属性": "Attributes",
    "エラー": "Errors",
}

FIELD_RE = re.compile(r'^(\s*):([^:\s]+):(.*)$')
TERM_RE = re.compile(r'^(\s*)([^\s:]+):\s*$')


def rewrite(path: Path) -> list[str]:
    changes: list[str] = []
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = FIELD_RE.match(line)
        if m and m.group(2) in KEY_MAP:
            new = f"{m.group(1)}:{KEY_MAP[m.group(2)]}:{m.group(3)}"
            changes.append(f"{path.relative_to(ROOT)}:{i}: :{m.group(2)}: -> :{KEY_MAP[m.group(2)]}:")
            line = new
        else:
            m = TERM_RE.match(line)
            if m and m.group(2) in TERM_MAP:
                changes.append(
                    f"{path.relative_to(ROOT)}:{i}: {m.group(2)}: -> {TERM_MAP[m.group(2)]}:")
                line = f"{m.group(1)}{TERM_MAP[m.group(2)]}:"
        out.append(line)
    if changes:
        path.write_text("\n".join(out), encoding="utf-8")
    return changes


def keys(lines: list[str]) -> Counter:
    c: Counter = Counter()
    for line in lines:
        m = FIELD_RE.match(line)
        if m:
            c[f":{m.group(2)}:"] += 1
            continue
        m = TERM_RE.match(line)
        if m:
            c[f"{m.group(2)}:"] += 1
    return c


def main() -> int:
    changes: list[str] = []
    for p in sorted(SRC.rglob("*.rst")):
        changes += rewrite(p)
    print("\n".join(changes) or "no key rewrites needed")

    print("\n--- verification against originals ---")
    bad = 0
    for p in sorted(SRC.rglob("*.rst")):
        rel = p.relative_to(SRC)
        op = ORIG / rel
        if not op.exists():
            continue
        t, o = keys(p.read_text(encoding="utf-8").split("\n")), \
            keys(op.read_text(encoding="utf-8").split("\n"))
        if t != o:
            bad += 1
            extra = t - o
            missing = o - t
            print(f"{rel}: extra={dict(extra)} missing={dict(missing)}")
    if not bad:
        print("all files: field/term keys match the originals exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
