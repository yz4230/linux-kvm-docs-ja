#!/usr/bin/env python3
"""Targeted corrections for keys the generic normaliser could not resolve.

The English originals are not uniform: ``x86/hypercalls.rst`` uses the singular
``:Architecture:`` and the term lines ``Usage:`` / ``Where:``, while
``devices/vfio.rst`` uses lower-case ``where:``, ``x86/msr.rst`` uses
lower-case ``data:``, and so on.  Each entry below is (file, regex, replacement)
applied once; the script prints what it changed and is safe to re-run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

FIXES: list[tuple[str, str, str]] = [
    # x86/hypercalls.rst: original uses the singular field key and capitalised terms
    ("x86/hypercalls.rst", r'^(\s*):Architectures:', r'\1:Architecture:'),
    ("x86/hypercalls.rst", r'^(\s*)使用法:\s*$', r'\1Usage:'),
    ("x86/hypercalls.rst", r'^(\s*)ここで:\s*$', r'\1Where:'),
    # x86/msr.rst: original term line is lower-case
    ("x86/msr.rst", r'^(\s*)データ:\s*$', r'\1data:'),
    # devices/vm.rst: attribute action list
    ("devices/vm.rst", r'^(\s*)アクション:\s*$', r'\1Actions:'),
    # x86/running-nested-guests.rst: glossary section term
    ("x86/running-nested-guests.rst", r'^(\s*)用語:\s*$', r'\1Terminology:'),
    # lower-case "where:" in the ARM device docs
    ("devices/arm-vgic-its.rst", r'^(\s*)ここで:\s*$', r'\1where:'),
    ("devices/vfio.rst", r'^(\s*)ここで:\s*$', r'\1where:'),
]


def main() -> int:
    changed = 0
    for rel, pattern, repl in FIXES:
        p = SRC / rel
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
        if n:
            p.write_text(new, encoding="utf-8")
            print(f"{rel}: {n} x {pattern!r} -> {repl!r}")
            changed += n
    print(f"{changed} replacement(s) applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
