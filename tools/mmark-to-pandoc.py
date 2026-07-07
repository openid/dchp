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
SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)\s*$")
# A code-fence line (CommonMark rules, which mmark inherits): three or more
# backticks/tildes indented at most 3 spaces — deeper indentation makes the
# line indented-code *content*, not a fence. group(2) is the info string.
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
SPECIAL_HEADING = re.compile(r"^(\s{0,3})\.(#{1,6})")


def _split_front_matter(lines: list[str]) -> tuple[dict, int]:
    """Return (metadata, body_start_index) for a leading ``%%% ... %%%`` block.

    If the source does not open with ``%%%`` there is no front matter: the whole
    input is the body. The closing delimiter is found by parsing: a ``%%%`` line
    *inside* a TOML multi-line string does not close the block (the truncated
    text is not valid TOML there), matching how mmark reads the file. A block
    that never closes, or whose content is not valid TOML, raises ValueError so
    the build fails loudly instead of leaking the metadata (author emails and
    all) into the Word document body.
    """
    if not lines or lines[0].strip() != "%%%":
        return {}, 0
    error: Exception | None = None
    for j in range(1, len(lines)):
        if lines[j].strip() != "%%%":
            continue
        try:
            return tomllib.loads("\n".join(lines[1:j])), j + 1
        except tomllib.TOMLDecodeError as e:
            error = e
    if error is not None:
        raise ValueError(f"front matter is not valid TOML: {error}")
    raise ValueError("front matter opened with '%%%' is never closed")


def _title_and_status(meta: dict) -> tuple[str | None, str | None]:
    """Extract (title, status) from the parsed front matter.

    The status (e.g. ``Editor's Copy``) is encoded after the *last* `` - `` in
    the single mmark ``title`` so the same title still drives the HTML draft.
    Splitting on the last separator keeps titles that themselves contain `` - ``
    intact.
    """
    title = meta.get("title")
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

    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if m:
            marker, info = m.group(1), m.group(2)
            if not in_fence:
                # A backtick fence's info string may not contain backticks
                # (such a line is a paragraph, not a fence); tilde fences
                # carry no such restriction.
                if marker[0] == "~" or "`" not in info:
                    in_fence, fence = True, marker
            elif (
                marker[0] == fence[0]
                and len(marker) >= len(fence)
                and not info.strip()
            ):
                # A closer must use the opener's character, be at least as
                # long, and be bare; any other fence-looking line is content.
                in_fence = False
            if not dropping_abstract:
                out.append(line)
            continue
        if in_fence:
            if not dropping_abstract:
                out.append(line)
            continue

        # The abstract runs until the next heading (any level) or part marker;
        # everything in between is dropped from the ISO Word output. Headings
        # may also be setext-style: text underlined with = or -. Approximation:
        # we end the drop at the line right before the underline, whereas a
        # multi-line setext paragraph would make mmark end it at the
        # paragraph's first line — close enough for a filter, and it keeps
        # whole sections from vanishing.
        if dropping_abstract:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            starts_setext = (
                line.strip() != ""
                and not IAL_LINE.match(line)
                and SETEXT_UNDERLINE.match(next_line)
            )
            if HEADING.match(line) or PART_MARKER.match(line) or starts_setext:
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
    # An editor may save the file with a UTF-8 BOM; it must not hide the
    # front-matter delimiter (str.strip() does not remove U+FEFF).
    lines = text.removeprefix("\ufeff").splitlines()
    front, start = _split_front_matter(lines)
    title, status = _title_and_status(front)

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
    try:
        sys.stdout.write(convert(sys.stdin.read()))
    except ValueError as e:
        raise SystemExit(f"error: {e}")
