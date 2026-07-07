# Build the DCHP specification.
#
#   make html   - render the HTML Editor's Copy with markdown2rfc (Docker)
#   make docx   - render the ISO-styled Word document with pandoc
#   make all    - build both
#   make clean  - remove the build/ directory
#
# Source scripts live in tools/; everything generated goes to build/ (which is
# git-ignored). `make html` needs Docker; `make docx` needs pandoc and python3
# (3.11+, for the tomllib-based converter). Override the interpreter with e.g.
# `make docx PYTHON=python3.13` on hosts whose default python3 is older.

SRCDIR   := draft
DOC      := digital-credentials-harmonized-presentation
SRC      := $(SRCDIR)/$(DOC).md

TOOLS    := tools
BUILD    := build
PYTHON   ?= python3

# Pinned by digest so the HTML rendering is reproducible: an untagged/:latest
# image could silently change the output between identical commits. Regenerate
# the digest with `docker inspect --format '{{index .RepoDigests 0}}' <image>`.
MD2RFC_IMAGE := danielfett/markdown2rfc@sha256:7b4412559d6ba5db45a14174a28da5b240512e7c2a886a5e4adb44e5e67f34ca

# Reference document with the ISO styles/layout, committed to the repo (derived
# once from the ISO template by tools/make-iso-reference.py; not regenerated per
# build).
REFDOC   := template/iso-reference.docx

HTML_OUT := $(BUILD)/$(DOC)-editors-copy.html

.PHONY: all html docx clean

all: html docx

## HTML Editor's Copy (markdown2rfc / mmark) -> build/
html: $(SRC)
	# Clean stale intermediates first so the copy below is unambiguous even if a
	# previous run was interrupted.
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
	docker run --rm -v "$(CURDIR)/$(SRCDIR):/data" $(MD2RFC_IMAGE) $(DOC).md
	mkdir -p $(BUILD)
	cp $(SRCDIR)/$(DOC).html $(HTML_OUT)
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
	@echo "HTML Editor's Copy -> $(HTML_OUT)"

## ISO-styled Word document (pandoc) -> build/
docx: $(SRC) $(REFDOC) $(TOOLS)/mmark-to-pandoc.py $(TOOLS)/iso-styles.lua
	mkdir -p $(BUILD)
	$(PYTHON) $(TOOLS)/mmark-to-pandoc.py < $(SRC) > $(BUILD)/$(DOC).pandoc.md
	pandoc $(BUILD)/$(DOC).pandoc.md \
		--reference-doc=$(REFDOC) \
		--lua-filter=$(TOOLS)/iso-styles.lua \
		-o $(BUILD)/$(DOC).docx
	rm -f $(BUILD)/$(DOC).pandoc.md
	@echo "ISO Word document -> $(BUILD)/$(DOC).docx"

clean:
	rm -rf $(BUILD)
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
