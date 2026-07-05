#!/usr/bin/env python3
"""Derive a clean pandoc reference document from the ISO Word template.

Pandoc's ``--reference-doc`` needs a ``.docx`` whose *styles* (Heading1..6,
ForewordTitle, TermNum, Terms, Definition, ANNEX, BiblioTitle, Note, ...) and
page/section setup are used to render the generated document. We reuse the ISO
Word template's styles and layout so the exported document looks like an ISO
deliverable, but we deliberately do NOT carry over any ISO copyright / IPR
boilerplate or branding: the document is not an ISO deliverable yet.

This script therefore:
  1. flips the main-document content type from *template* (.dotx) to *document*
     (.docx) so the result is a normal Word document;
  2. neutralises the ISO copyright notice and document-number placeholders that
     live in the running headers/footers; and
  3. drops the ISO logo images and the ISO document metadata (docProps and
     customXml parts) so no ISO branding or classification travels with the
     exported file; and
  4. un-hides the styles (removes <w:semiHidden/>) so every docx viewer applies
     the ISO heading styles instead of falling back to plain body text.

Everything else (styles, numbering, theme, fonts, headers/footers) is copied
through so the document keeps the ISO look-and-feel.

Usage:
    python3 tools/make-iso-reference.py [INPUT.dotx] [OUTPUT.docx]

Defaults: template/Word_template_for_ISO_standards.dotx -> build/iso-reference.docx
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

# --- Neutralise ISO branding in running headers/footers ----------------------
# The ISO template ships placeholder branding in the running headers/footers:
#   footers: "© ISO #### – All rights reserved"  (with NBSPs and an en-dash)
#   headers: "ISO #####-#:####(X)"               (document-number placeholder)
# We replace the text of any run (<w:t>) that carries this ISO branding with a
# neutral, non-IPR marker, leaving page-number fields (separate runs) intact.
# Matching by content (not exact whitespace) keeps this robust to the template's
# non-breaking spaces and dash characters.
DRAFT_LABEL = "Working Group Draft"
_RUN_TEXT = re.compile(r"(<w:t\b[^>]*>)([^<]*)(</w:t>)", re.S)


def _neutralise_runs(xml: str) -> str:
    def repl(m: "re.Match[str]") -> str:
        inner = m.group(2)
        if "####" in inner or "All rights reserved" in inner or "© ISO" in inner:
            return m.group(1) + DRAFT_LABEL + m.group(3)
        return m.group(0)

    return _RUN_TEXT.sub(repl, xml)


# --- Main-document content-type override: template -> document ----------------
CT_TEMPLATE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.template.main+xml"
)
CT_DOCUMENT = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document.main+xml"
)

# --- Parts to drop entirely (ISO logos and ISO document metadata) ------------
# The template's only images are the ISO logo/branding, referenced solely by the
# title page (which pandoc discards). customXml holds ISO metadata bindings and
# docProps/{app,custom}.xml hold ISO company/classification metadata. None are
# needed to style the document, so we drop them.
DROP_PREFIXES = ("word/media/", "customXml/")
DROP_EXACT = {"docProps/app.xml", "docProps/custom.xml"}


def _is_dropped(name: str) -> bool:
    return name in DROP_EXACT or name.startswith(DROP_PREFIXES)


# Substrings that identify a relationship/content-type entry pointing at a
# dropped part, so we can keep [Content_Types].xml and the *.rels files
# internally consistent after the drop.
_DANGLING = ("media/", "customXml/", "docProps/app.xml", "docProps/custom.xml")
_XML_ELEMENT = re.compile(r"<(Relationship|Override|Default)\b[^>]*/>")


def _strip_dangling(xml: str) -> str:
    def repl(m: "re.Match[str]") -> str:
        el = m.group(0)
        if any(ref in el for ref in _DANGLING):
            return ""
        return el

    return _XML_ELEMENT.sub(repl, xml)


# The ISO template hides most of its styles from the Word gallery
# (<w:semiHidden/> / <w:unhideWhenUsed/>). Several docx viewers (Preview/Quick
# Look, Pages, Google Docs, some LibreOffice paths) skip the *formatting* of
# semi-hidden styles and fall back to Normal, so the unnumbered headings
# (Foreword/Introduction, which use the ForewordTitle/IntroTitle styles) render
# as plain body text. We remove those flags so every viewer applies the ISO
# styles — and so editors can see them in the Word styles pane.
_HIDE_FLAGS = re.compile(r"<w:(?:semiHidden|unhideWhenUsed)\b[^>]*/>")


def _activate_styles(xml: str) -> str:
    return _HIDE_FLAGS.sub("", xml)


def transform(name: str, data: bytes) -> bytes:
    if name == "[Content_Types].xml":
        text = data.decode("utf-8").replace(CT_TEMPLATE, CT_DOCUMENT)
        return _strip_dangling(text).encode("utf-8")
    if name.endswith(".rels"):
        return _strip_dangling(data.decode("utf-8")).encode("utf-8")
    if name == "word/styles.xml":
        return _activate_styles(data.decode("utf-8")).encode("utf-8")
    if name.startswith(("word/header", "word/footer")) and name.endswith(".xml"):
        return _neutralise_runs(data.decode("utf-8")).encode("utf-8")
    return data


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "template" / "Word_template_for_ISO_standards.dotx"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "build" / "iso-reference.docx"

    if not src.is_file():
        print(f"error: template not found: {src}", file=sys.stderr)
        return 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
        dst, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            if _is_dropped(item.filename):
                continue
            data = transform(item.filename, zin.read(item.filename))
            zout.writestr(item, data)

    try:
        shown = dst.relative_to(root)
    except ValueError:
        shown = dst
    print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
