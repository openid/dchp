# Build the DCHP specification.
#
#   make html   - render the HTML Editor's Copy with markdown2rfc (Docker)
#   make docx   - render the ISO-styled Word document with pandoc
#   make all    - build both
#   make test   - run the test suite
#   make clean  - remove the build/ directory
#
# Source scripts live in tools/; everything generated goes to build/ (which is
# git-ignored). `make html` needs Docker; `make docx` needs pandoc and a Python
# with tomllib (3.11+, for the converter).

SRCDIR   := draft
DOC      := digital-credentials-harmonized-presentation
SRC      := $(SRCDIR)/$(DOC).md

TOOLS    := tools
BUILD    := build

# The mmark->pandoc converter needs tomllib (Python 3.11+). Auto-pick the first
# available interpreter that has it, so `make docx` works even where the default
# python3 is older; override explicitly with `make docx PYTHON=/path/to/python`.
PYTHON   ?= $(shell for p in python3 python3.13 python3.12 python3.11; do \
	command -v $$p >/dev/null 2>&1 && $$p -c 'import tomllib' >/dev/null 2>&1 \
	  && { echo $$p; exit 0; }; \
	done)

# Pinned by digest so the HTML rendering is reproducible: an untagged/:latest
# image could silently change the output between identical commits. Regenerate
# the digest with `docker inspect --format '{{index .RepoDigests 0}}' <image>`.
MD2RFC_IMAGE := danielfett/markdown2rfc@sha256:7b4412559d6ba5db45a14174a28da5b240512e7c2a886a5e4adb44e5e67f34ca

# Reference document with the ISO styles/layout, committed to the repo (derived
# once from the ISO template by tools/make-iso-reference.py; not regenerated per
# build). The ISO template itself is not committed — see that script's docstring.
REFDOC   := template/iso-reference.docx

HTML_OUT := $(BUILD)/$(DOC)-editors-copy.html

.PHONY: all html docx test clean need-python

all: html docx

# The converter and the tests need $(PYTHON); fail with guidance if none found.
need-python:
	@test -n "$(strip $(PYTHON))" || { \
	  echo "error: no Python with tomllib (3.11+) found;"; \
	  echo "       install one or run: make <target> PYTHON=/path/to/python3.11+"; \
	  exit 1; }

## HTML Editor's Copy (markdown2rfc / mmark) -> build/
html: $(SRC)
	# Clean stale intermediates first so the copy below is unambiguous even if a
	# previous run was interrupted.
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
	docker run --rm -v "$(CURDIR)/$(SRCDIR):/data" $(MD2RFC_IMAGE) $(DOC).md
	mkdir -p $(BUILD)
	# Cleaned above, so this glob now matches exactly the fresh output whatever
	# markdown2rfc names it (it may add a draft-version suffix).
	cp $(SRCDIR)/$(DOC)*.html $(HTML_OUT)
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
	@echo "HTML Editor's Copy -> $(HTML_OUT)"

## ISO-styled Word document (pandoc) -> build/
docx: need-python $(SRC) $(REFDOC) $(TOOLS)/mmark-to-pandoc.py $(TOOLS)/iso-styles.lua
	mkdir -p $(BUILD)
	$(PYTHON) $(TOOLS)/mmark-to-pandoc.py < $(SRC) > $(BUILD)/$(DOC).pandoc.md
	pandoc $(BUILD)/$(DOC).pandoc.md \
		--reference-doc=$(REFDOC) \
		--lua-filter=$(TOOLS)/iso-styles.lua \
		-o $(BUILD)/$(DOC).docx
	rm -f $(BUILD)/$(DOC).pandoc.md
	@echo "ISO Word document -> $(BUILD)/$(DOC).docx"

## Test suite (every tests/test_*.py, so new tests run without editing this)
test: need-python
	@for t in tests/test_*.py; do $(PYTHON) $$t || exit 1; done

clean:
	rm -rf $(BUILD)
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
