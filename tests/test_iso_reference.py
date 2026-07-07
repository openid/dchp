#!/usr/bin/env python3
"""Hygiene tests for the committed pandoc reference document.

``template/iso-reference.docx`` is derived from the ISO Word template by
``tools/make-iso-reference.py`` and committed to the repo (the build uses it
directly; the generator is not part of the build). The tool promises that no
ISO branding, copyright/IPR boilerplate, or document metadata from the ISO
template travels into the public repo. A regression here is silent — the file
is binary and nobody re-opens it on review — so these tests pin those
guarantees against the committed file.

Run:  python3 tests/test_iso_reference.py
"""
from __future__ import annotations

import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFDOC = ROOT / "template" / "iso-reference.docx"


def check_no_document_properties(z: zipfile.ZipFile) -> list[str]:
    """No docProps/ part may ship: core.xml carries the ISO template author's
    personal metadata (dc:creator / cp:lastModifiedBy), app.xml and custom.xml
    the ISO company/classification metadata. Nothing may still reference them.
    """
    problems = [
        f"{name}: docProps part shipped"
        for name in z.namelist()
        if name.startswith("docProps/")
    ]
    for name in ("[Content_Types].xml", "_rels/.rels"):
        if b"docProps/" in z.read(name):
            problems.append(f"{name}: dangling docProps reference")
    return problems


# Tripwire strings from the ISO title page, copyright/IPR notice, and the
# document-number placeholders. Any one of them surviving in any XML part
# means ISO boilerplate leaked into the public file.
ISO_BOILERPLATE_MARKERS = (
    "© ISO",
    "All rights reserved",
    "copyright@iso.org",
    "ISO copyright office",
    "#####",
)


def check_no_iso_boilerplate(z: zipfile.ZipFile) -> list[str]:
    """No ISO copyright/IPR or title-page text may remain in any XML part
    (body, headers, footers, notes); footers carry the draft label instead."""
    return [
        f"{name}: contains {marker!r}"
        for name in z.namelist()
        if name.endswith(".xml")
        for marker in ISO_BOILERPLATE_MARKERS
        if marker in z.read(name).decode("utf-8")
    ]


def check_no_trash_entries(z: zipfile.ZipFile) -> list[str]:
    """The source .dotx contains [trash]/*.dat zip-housekeeping junk left by
    whatever tool last edited the ISO template; it must not be copied over."""
    return [
        f"{name}: junk zip entry copied from the template"
        for name in z.namelist()
        if name.startswith("[trash]/")
    ]


def check_section_properties_kept(z: zipfile.ZipFile) -> list[str]:
    """pandoc derives page geometry and the running footers from the body-level
    <w:sectPr>; cleaning the body must not lose it."""
    doc = z.read("word/document.xml").decode("utf-8")
    return [] if "<w:sectPr" in doc else ["word/document.xml: <w:sectPr> lost"]


CHECKS = [
    check_no_document_properties,
    check_no_iso_boilerplate,
    check_no_trash_entries,
    check_section_properties_kept,
]


def main() -> int:
    with zipfile.ZipFile(REFDOC) as z:
        problems = [p for check in CHECKS for p in check(z)]
    for p in problems:
        print(f"FAIL: {p}", file=sys.stderr)
    if problems:
        print(f"FAIL: {REFDOC.relative_to(ROOT)} is not clean", file=sys.stderr)
        return 1
    print("OK: iso-reference.docx hygiene checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
