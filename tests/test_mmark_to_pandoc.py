#!/usr/bin/env python3
"""Golden-output test for tools/mmark-to-pandoc.py.

The converter runs three stacked line transformations (front-matter parsing,
abstract dropping, fence-aware filtering) whose failures are otherwise silent —
a mangled normative example or a dropped subsection produces no build error, only
a wrong Word document. This test pins the converter's output for a sample that
exercises every transformation:

  * a single-quoted TOML title containing embedded `` - `` separators (title vs.
    status split);
  * an ``.# Abstract`` followed by a ``## Notice`` subsection that must survive;
  * a fenced code block whose contents (``%%%``, ``{mainmatter}``, ``.#``,
    ``{: ...}``) must pass through verbatim.

Run:  python3 tests/test_mmark_to_pandoc.py   (requires Python 3.11+ / tomllib)
"""
from __future__ import annotations

import difflib
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

# The converter's filename has a hyphen, so load it by path rather than import.
_spec = importlib.util.spec_from_file_location(
    "mmark_to_pandoc", ROOT / "tools" / "mmark-to-pandoc.py"
)
assert _spec and _spec.loader
mmark_to_pandoc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mmark_to_pandoc)


def main() -> int:
    source = (FIXTURES / "sample.md").read_text()
    expected = (FIXTURES / "sample.expected.md").read_text()
    got = mmark_to_pandoc.convert(source)
    if got != expected:
        sys.stderr.writelines(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                got.splitlines(keepends=True),
                fromfile="sample.expected.md",
                tofile="convert(sample.md)",
            )
        )
        print("FAIL: mmark-to-pandoc golden output mismatch", file=sys.stderr)
        return 1
    print("OK: mmark-to-pandoc golden output matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
