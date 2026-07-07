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
  2. replaces the document body — the ISO title page with its document-number
     placeholders, WD/CD review warning, and the full ISO copyright/IPR
     notice — with a single empty paragraph, keeping only the body-level
     <w:sectPr> (page geometry, running footers) that pandoc reads;
  3. neutralises the ISO copyright notice and document-number placeholders that
     live in the running headers/footers;
  4. drops the ISO logo images, the embedded OLE object, and the ISO document
     metadata (docProps and customXml parts) so no ISO branding, classification,
     or template-author identity travels with the exported file; and
  5. un-hides the styles (removes <w:semiHidden/>) so every docx viewer applies
     the ISO heading styles instead of falling back to plain body text.

This script is NOT run on every build. Its output is committed as
``template/iso-reference.docx`` and used directly by ``make docx``; run this
script by hand to regenerate that file whenever the ISO template (or this
script) changes. The ISO template itself is deliberately NOT committed — it is
ISO-copyrighted and carries personal and classification metadata (docProps) —
so obtain it from ISO/IEC JTC 1/SC 17 WG 10 and place it at
``template/Word_template_for_ISO_standards.dotx`` (or pass its path) to
regenerate. ``tests/test_iso_reference.py`` checks the committed file matches
what this script produces whenever that template is present locally, and
always checks that no ISO metadata/boilerplate ships in any committed Word
file.
Note: pandoc derives a single-section layout from the reference document, so the
committed ``iso-reference.docx`` may still benefit from a one-time manual pass in
Word to finalise section setup, page-numbering restarts, and margins.

Everything else (styles, numbering, theme, fonts, headers/footers) is copied
through so the document keeps the ISO look-and-feel.

Usage:
    python3 tools/make-iso-reference.py [INPUT.dotx] [OUTPUT.docx]

Defaults: template/Word_template_for_ISO_standards.dotx -> template/iso-reference.docx
"""
from __future__ import annotations

import io
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
DRAFT_LABEL = "Editor's Copy"
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

# --- Parts to drop entirely (ISO logos, OLE object, ISO document metadata) ---
# The template's only images (word/media) are the ISO logo/branding and the
# template's embedded OLE object (word/embeddings/oleObject1.bin), all referenced
# solely by the title page (which pandoc discards). customXml holds ISO metadata
# bindings; docProps holds the ISO company/classification metadata (app.xml,
# custom.xml) and the template author's personal metadata (core.xml carries
# dc:creator / cp:lastModifiedBy). None are needed to style the document, so we
# drop them all — Word and pandoc are fine without document properties.
# [trash]/ is zip-housekeeping junk left in the .dotx by whatever tool last
# edited the ISO template; it is not part of the OPC package.
DROP_PREFIXES = ("word/media/", "word/embeddings/", "customXml/", "docProps/", "[trash]/")


def _is_dropped(name: str) -> bool:
    return name.startswith(DROP_PREFIXES)


# Substrings that identify a relationship/content-type entry pointing at a
# dropped part, so we can keep [Content_Types].xml and the *.rels files
# internally consistent after the drop.
_DANGLING = (
    "media/",
    "embeddings/",
    "customXml/",
    "docProps/",
)
_XML_ELEMENT = re.compile(r"<(Relationship|Override|Default)\b[^>]*/>")


def _strip_dangling(xml: str) -> str:
    def repl(m: "re.Match[str]") -> str:
        el = m.group(0)
        if any(ref in el for ref in _DANGLING):
            return ""
        return el

    return _XML_ELEMENT.sub(repl, xml)


# The template's document body is the ISO title page: document-number
# placeholders, the WD/CD review warning, the full ISO copyright/IPR notice,
# and the logo drawings / OLE object that referenced the dropped media parts.
# Pandoc ignores the reference document's body — it reads only the styles and
# the final body-level <w:sectPr> — so replace the whole body with one empty
# paragraph plus that <w:sectPr>. Nothing ISO-owned survives in the committed
# file when it is opened standalone, and no dangling image references are left
# behind. (Both .* are greedy, so the match keeps the *last* sectPr: the
# body-level one.)
_BODY = re.compile(r"(<w:body>).*(<w:sectPr\b.*</w:sectPr>)\s*(</w:body>)", re.S)


def _empty_body(xml: str) -> str:
    return _BODY.sub(r"\1<w:p/>\2\3", xml)


# Belt-and-braces for the header/footer parts we keep: _strip_dangling removes
# media/OLE relationships from *all* .rels files, so also strip any
# <w:drawing>/<w:object>/<w:pict> elements there (none in the current template)
# rather than leave dangling references that render as broken-image
# placeholders.
_DRAWING_OR_OBJECT = re.compile(
    r"<w:(drawing|object|pict)\b.*?</w:\1>", re.S
)


def _strip_media_elements(xml: str) -> str:
    return _DRAWING_OR_OBJECT.sub("", xml)


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
    if name == "word/document.xml":
        return _empty_body(data.decode("utf-8")).encode("utf-8")
    if name == "word/styles.xml":
        return _activate_styles(data.decode("utf-8")).encode("utf-8")
    if name.startswith(("word/header", "word/footer")) and name.endswith(".xml"):
        text = _strip_media_elements(data.decode("utf-8"))
        return _neutralise_runs(text).encode("utf-8")
    return data


def build(src: Path) -> bytes:
    """Return the transformed reference document as .docx bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
        buf, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            if _is_dropped(item.filename):
                continue
            data = transform(item.filename, zin.read(item.filename))
            zout.writestr(item, data)
    return buf.getvalue()


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "template" / "Word_template_for_ISO_standards.dotx"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "template" / "iso-reference.docx"

    if not src.is_file():
        print(f"error: template not found: {src}", file=sys.stderr)
        return 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(build(src))

    try:
        shown = dst.relative_to(root)
    except ValueError:
        shown = dst
    print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
