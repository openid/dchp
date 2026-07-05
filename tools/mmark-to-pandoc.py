#!/usr/bin/env python3
"""Strip mmark-only syntax so the spec source can be fed to pandoc.

The canonical spec source is authored in mmark (so ``markdown2rfc`` can render
the HTML editor's draft). mmark adds a few constructs that pandoc does not
understand; this filter removes them so the *same* source can also be converted
to the ISO Word document by pandoc:

  * the ``%%% ... %%%`` TOML front matter block (mmark document metadata) — the
    ``title`` is kept and re-emitted as a pandoc YAML metadata block so the Word
    document still has a title;
  * the ``.# Abstract`` section (an RFC/mmark concept; ISO documents have no
    abstract, so the whole abstract block is dropped);
  * the ``{frontmatter}`` / ``{mainmatter}`` / ``{backmatter}`` part markers;
  * defensive clean-up of kramdown-style ``{: ...}`` attribute lists.

Everything else (headings, paragraphs, lists, tables, definition lists, notes)
is common Markdown and is passed through unchanged. Reads stdin, writes stdout.
"""
from __future__ import annotations

import json
import re
import sys


def strip(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []

    i = 0
    n = len(lines)

    # 1. Drop a leading %%% ... %%% TOML front matter block, but keep the title
    #    so it can be re-emitted as pandoc metadata (mmark carried the title in
    #    the front matter; the ISO Word document needs one too).
    title = None
    if i < n and lines[i].strip() == "%%%":
        i += 1
        while i < n and lines[i].strip() != "%%%":
            m = re.match(r'\s*title\s*=\s*"(.*)"\s*$', lines[i])
            if m:
                title = m.group(1)
            i += 1
        i += 1  # skip closing %%%

    part_marker = re.compile(r"^\{(frontmatter|mainmatter|backmatter)\}\s*$")
    abstract_start = re.compile(r"^\.#\s+Abstract\b")
    ial_line = re.compile(r"^\{:.*\}\s*$")  # kramdown inline attribute list

    while i < n:
        line = lines[i]

        # 2. Drop the abstract block: from ".# Abstract" up to the next part
        #    marker or top-level heading (exclusive).
        if abstract_start.match(line):
            i += 1
            while i < n and not (
                part_marker.match(lines[i]) or lines[i].startswith("# ")
            ):
                i += 1
            continue

        # 3. Drop mmark part markers entirely.
        if part_marker.match(line):
            i += 1
            continue

        # 4. Drop stray kramdown attribute-list lines.
        if ial_line.match(line):
            i += 1
            continue

        # Defensive: turn any other ".# Heading" into a normal heading.
        line = re.sub(r"^\.#", "#", line)

        out.append(line)
        i += 1

    # Collapse leading blank lines produced by the removals.
    while out and out[0].strip() == "":
        out.pop(0)

    body = "\n".join(out) + "\n"

    # Re-emit the title as a pandoc YAML metadata block. The Lua filter turns it
    # into the document's title block; here we just carry it across.
    if title:
        body = "---\ntitle: " + json.dumps(title) + "\n---\n\n" + body
    return body


if __name__ == "__main__":
    sys.stdout.write(strip(sys.stdin.read()))
