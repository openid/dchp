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


# Focused cases for the individual line transformations: (name, source,
# expected convert() output). Each pins one behavior the golden sample does
# not exercise; the fence cases follow CommonMark's fence rules, which mmark
# inherits.
CASES: list[tuple[str, str, str]] = [
    (
        "inner 3-backtick line does not close a 4-backtick fence "
        "(closer must be at least as long as the opener)",
        "# Scope\n\n````\n```\n{: #example-ial}\n```\n````\n\n{backmatter}\n\n# After\n",
        "# Scope\n\n````\n```\n{: #example-ial}\n```\n````\n\n\n# After\n",
    ),
    (
        "a fence line with an info string does not close an open fence "
        "(closing fences must be bare)",
        '# Scope\n\n```\n```python\n{mainmatter}\n.# not a heading\n```\n\nAfter text.\n',
        '# Scope\n\n```\n```python\n{mainmatter}\n.# not a heading\n```\n\nAfter text.\n',
    ),
    (
        "backticks indented 4+ spaces are indented-code content, not a fence",
        "# Scope\n\n    ```\n\n{mainmatter}\n\nAfter text.\n",
        "# Scope\n\n    ```\n\n\nAfter text.\n",
    ),
    (
        "an ordinary fenced block with an info string still passes through "
        "and filtering resumes after it",
        '```json\n{"a": 1}\n```\n\n{: .x}\n',
        '```json\n{"a": 1}\n```\n\n',
    ),
    (
        "a UTF-8 BOM does not hide the front-matter delimiter",
        '﻿%%%\ntitle = "T - S"\n%%%\n\n# Scope\n',
        '---\ntitle: "T"\nsubtitle: "S"\n---\n\n# Scope\n',
    ),
    (
        "a %%% line inside a TOML multi-line string does not close the "
        "front matter",
        '%%%\ntitle = "T - S"\ndescription = """\n%%%\n"""\n%%%\n\n# Scope\n',
        '---\ntitle: "T"\nsubtitle: "S"\n---\n\n# Scope\n',
    ),
    (
        "a setext heading terminates the abstract drop "
        "(mmark ends the abstract at the next heading of any style)",
        ".# Abstract\n\nAbstract text.\n\nForeword\n========\n\n"
        "Foreword body.\n\n# Scope\n",
        "Foreword\n========\n\nForeword body.\n\n# Scope\n",
    ),
]


def _convert_or_error(source: str) -> str:
    try:
        return mmark_to_pandoc.convert(source)
    except Exception as e:  # an unexpected raise is a failure; show it as one
        return f"<convert() raised {type(e).__name__}: {e}>\n"


def _diff(name: str, expected: str, got: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            got.splitlines(keepends=True),
            fromfile=f"expected [{name}]",
            tofile="got",
        )
    )


def check_golden() -> list[str]:
    source = (FIXTURES / "sample.md").read_text()
    expected = (FIXTURES / "sample.expected.md").read_text()
    got = mmark_to_pandoc.convert(source)
    if got != expected:
        return ["golden output mismatch:\n" + _diff("sample.md", expected, got)]
    return []


def check_cases() -> list[str]:
    return [
        f"{name}:\n" + _diff(name, expected, got)
        for name, source, expected in CASES
        if (got := _convert_or_error(source)) != expected
    ]


def check_unclosed_front_matter() -> list[str]:
    """A ``%%%`` block that never closes must fail the build loudly — both
    silently dropping the rest of the file and emitting the raw TOML (author
    emails and all) as Word body text are wrong."""
    source = '%%%\ntitle = "T"\n\n# Scope\n'
    try:
        mmark_to_pandoc.convert(source)
    except ValueError as e:
        if "front matter" in str(e):
            return []
        return [f"unclosed front matter: error message lacks context: {e}"]
    return ["unclosed front matter: convert() did not raise"]


def main() -> int:
    failures = check_golden() + check_cases() + check_unclosed_front_matter()
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"OK: mmark-to-pandoc golden output and {len(CASES)} cases match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
