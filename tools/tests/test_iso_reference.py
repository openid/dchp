#!/usr/bin/env python3
"""Hygiene tests for committed Word (WordprocessingML) files.

``tools/template/iso-reference.docx`` is derived from the ISO Word template by
``tools/make-iso-reference.py`` and committed to the repo (the build uses it
directly; the generator is not part of the build). The tool promises that no
ISO branding, copyright/IPR boilerplate, or document metadata from the ISO
template travels into the public repo. A regression here is silent — the
files are binary and nobody re-opens them on review — so these tests pin
those guarantees against *every* committed .docx/.dotx (the ISO template
itself is deliberately not committed — see tools/make-iso-reference.py).

Run:  python3 tools/tests/test_iso_reference.py
"""
from __future__ import annotations

import importlib.util
import io
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
REFDOC = ROOT / "tools" / "template" / "iso-reference.docx"
TEMPLATE = ROOT / "tools" / "template" / "Word_template_for_ISO_standards.dotx"

# The generator's filename has a hyphen, so load it by path rather than import.
_spec = importlib.util.spec_from_file_location(
    "make_iso_reference", ROOT / "tools" / "make-iso-reference.py"
)
assert _spec and _spec.loader
make_iso_reference = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_iso_reference)


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


# Tripwire strings from the ISO title page, copyright/IPR notice, the
# document-number placeholders, and the ISO classification label. Any one of
# them surviving in any XML part means ISO boilerplate leaked into the
# public file.
ISO_BOILERPLATE_MARKERS = (
    "© ISO",
    "All rights reserved",
    "copyright@iso.org",
    "ISO copyright office",
    "#####",
    "ISO - Internal",
)


def committed_word_files() -> list[pathlib.Path]:
    """Every WordprocessingML package committed to the repo."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.docx", "*.dotx", "*.docm", "*.dotm"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return [ROOT / name for name in out.split("\0") if name]


def check_no_iso_boilerplate(z: zipfile.ZipFile) -> list[str]:
    """No ISO copyright/IPR or title-page text may remain in any XML part
    (body, headers, footers, notes); footers carry the draft label instead."""
    problems = []
    for name in z.namelist():
        if not name.endswith(".xml"):
            continue
        text = z.read(name).decode("utf-8")
        problems += [
            f"{name}: contains {marker!r}"
            for marker in ISO_BOILERPLATE_MARKERS
            if marker in text
        ]
    return problems


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


def check_in_sync_with_generator(z: zipfile.ZipFile) -> list[str]:
    """Regenerating from the ISO template must reproduce the committed
    reference document part-for-part. Otherwise the ISO template or the
    generator changed without `python3 tools/make-iso-reference.py` being
    re-run — and the build, which reads only the committed file, would
    silently ship the stale styles. (Parts are compared decompressed, so
    zlib differences between environments cannot cause false failures.)

    The ISO template is not committed (see tools/make-iso-reference.py), so
    this check runs only where an editor has placed it locally; CI skips it.
    """
    if not TEMPLATE.is_file():
        print(f"SKIP: generator sync check ({TEMPLATE.name} not present)")
        return []
    fresh = zipfile.ZipFile(io.BytesIO(make_iso_reference.build(TEMPLATE)))
    if fresh.namelist() != z.namelist():
        return [
            "part list differs from regeneration "
            f"(committed {z.namelist()} vs fresh {fresh.namelist()}); "
            "re-run tools/make-iso-reference.py and commit the result"
        ]
    return [
        f"{name}: differs from regeneration; "
        "re-run tools/make-iso-reference.py and commit the result"
        for name in fresh.namelist()
        if fresh.read(name) != z.read(name)
    ]


# Hygiene rules applied to every committed Word file.
FILE_CHECKS = [
    check_no_document_properties,
    check_no_iso_boilerplate,
    check_no_trash_entries,
]

# Structural/consistency rules for the pandoc reference document itself.
REFDOC_CHECKS = [
    check_section_properties_kept,
    check_in_sync_with_generator,
]


def main() -> int:
    problems: list[str] = []
    files = committed_word_files()
    if REFDOC not in files:
        problems.append(f"{REFDOC.relative_to(ROOT)}: not committed")
    for path in files:
        checks = FILE_CHECKS + (REFDOC_CHECKS if path == REFDOC else [])
        with zipfile.ZipFile(path) as z:
            for check in checks:
                problems += [
                    f"{path.relative_to(ROOT)}: {p}" for p in check(z)
                ]
    for p in problems:
        print(f"FAIL: {p}", file=sys.stderr)
    if problems:
        return 1
    print(f"OK: hygiene checks pass for {len(files)} committed Word file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
