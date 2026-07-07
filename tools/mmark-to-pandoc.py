#!/usr/bin/env python3
"""Strip mmark-only syntax so the spec source can be fed to pandoc.

The canonical spec source is authored in mmark (so ``markdown2rfc`` can render
the HTML editor's draft). mmark adds a few constructs that pandoc does not
understand; this filter removes them so the *same* source can also be converted
to the ISO Word document by pandoc:

  * the ``%%% ... %%%`` TOML front matter block (mmark document metadata) — it is
    parsed with ``tomllib`` and the ``title`` is re-emitted as pandoc metadata.
    The mmark title encodes the document status after the last `` - `` (e.g.
    ``"... - Editor's Copy"``); we split it back into a ``title`` and a
    ``subtitle`` so the Word document gets a styled title + status block;
  * the ``.# Abstract`` section (an RFC/mmark concept; ISO documents have no
    abstract, so the whole abstract block is dropped — up to, but not including,
    the next heading of *any* level, matching how mmark ends the abstract);
  * the ``{frontmatter}`` / ``{mainmatter}`` / ``{backmatter}`` part markers;
  * kramdown-style ``{: ...}`` inline-attribute-list lines;
  * mmark special headings ``.# Heading`` become normal ``# Heading``.

All of the above filtering is skipped *inside fenced code blocks* (``` ``` `` /
``~~~``), so normative request/response examples that happen to contain these
constructs pass through verbatim. Everything else (headings, paragraphs, lists,
tables, definition lists, notes) is common Markdown and is passed through
unchanged. Reads stdin, writes stdout.

Requires Python 3.11+ for ``tomllib`` (or the ``tomli`` backport on 3.10).
"""
from __future__ import annotations

import json
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


# An ATX heading, including the mmark special-heading ".#" form.
HEADING = re.compile(r"^\s{0,3}\.?#{1,6}(?:\s|$)")
PART_MARKER = re.compile(r"^\{(?:frontmatter|mainmatter|backmatter)\}\s*$")
ABSTRACT_START = re.compile(r"^\.#\s+Abstract\b")
IAL_LINE = re.compile(r"^\{:.*\}\s*$")            # kramdown inline attribute list
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")          # opening/closing code fence
SPECIAL_HEADING = re.compile(r"^(\s{0,3})\.(#{1,6})")


def _split_front_matter(lines: list[str]) -> tuple[str, int]:
    """Return (toml_text, body_start_index) for a leading ``%%% ... %%%`` block.

    If the source does not open with ``%%%`` there is no front matter: the whole
    input is the body.
    """
    if lines and lines[0].strip() == "%%%":
        for j in range(1, len(lines)):
            if lines[j].strip() == "%%%":
                return "\n".join(lines[1:j]), j + 1
    return "", 0


def _title_and_status(toml_text: str) -> tuple[str | None, str | None]:
    """Parse the TOML front matter into (title, status).

    The status (e.g. ``Editor's Copy``) is encoded after the *last* `` - `` in
    the single mmark ``title`` so the same title still drives the HTML draft.
    Splitting on the last separator keeps titles that themselves contain `` - ``
    intact. ``tomllib`` handles basic, literal, and multi-line TOML strings, so
    single-quoted titles and escaped quotes are parsed correctly.
    """
    if not toml_text.strip():
        return None, None
    title = tomllib.loads(toml_text).get("title")
    if not isinstance(title, str) or not title.strip():
        return None, None
    main, sep, status = title.rpartition(" - ")
    if sep:
        return main.strip(), status.strip()
    return title.strip(), None


def _process_body(lines: list[str]) -> list[str]:
    out: list[str] = []
    in_fence = False
    fence = ""
    dropping_abstract = False

    for line in lines:
        m = FENCE.match(line)
        if m:
            marker = m.group(1)[0] * 3  # normalise to ``` or ~~~
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            if not dropping_abstract:
                out.append(line)
            continue
        if in_fence:
            if not dropping_abstract:
                out.append(line)
            continue

        # The abstract runs until the next heading (any level) or part marker;
        # everything in between is dropped from the ISO Word output.
        if dropping_abstract:
            if HEADING.match(line) or PART_MARKER.match(line):
                dropping_abstract = False  # fall through and handle this line
            else:
                continue

        if ABSTRACT_START.match(line):
            dropping_abstract = True
            continue
        if PART_MARKER.match(line):
            continue
        if IAL_LINE.match(line):
            continue

        line = SPECIAL_HEADING.sub(r"\1\2", line)  # ".# Heading" -> "# Heading"
        out.append(line)

    # Collapse leading blank lines produced by the removals.
    while out and out[0].strip() == "":
        out.pop(0)
    return out


def convert(text: str) -> str:
    lines = text.splitlines()
    toml_text, start = _split_front_matter(lines)
    title, status = _title_and_status(toml_text)

    body = "\n".join(_process_body(lines[start:])) + "\n"

    # Re-emit the title (and status subtitle) as a pandoc YAML metadata block;
    # the Lua filter renders them as the Word document's title block.
    if title:
        meta = ["---", "title: " + json.dumps(title)]
        if status:
            meta.append("subtitle: " + json.dumps(status))
        meta += ["---", "", ""]
        body = "\n".join(meta) + body
    return body


if __name__ == "__main__":
    sys.stdout.write(convert(sys.stdin.read()))
