# Build the DCHP specification.
#
#   make html   - render the HTML Working Group Draft with markdown2rfc (Docker)
#   make docx   - render the ISO-styled Word document with pandoc
#   make all    - build both
#   make clean  - remove the build/ directory
#
# Source scripts live in tools/; everything generated goes to build/ (which is
# git-ignored). `make html` needs Docker; `make docx` needs pandoc and python3.

SRCDIR   := draft
DOC      := digital-credentials-harmonized-presentation
SRC      := $(SRCDIR)/$(DOC).md
TEMPLATE := template/Word_template_for_ISO_standards.dotx

TOOLS    := tools
BUILD    := build

.PHONY: all html docx clean

all: html docx

## HTML Working Group Draft (markdown2rfc / mmark) -> build/
html: $(SRC)
	docker run --rm -v "$(CURDIR)/$(SRCDIR):/data" danielfett/markdown2rfc $(DOC).md
	mkdir -p $(BUILD)
	cp $(SRCDIR)/$(DOC)*.html $(BUILD)/$(DOC)-wg-draft.html
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
	@echo "HTML Working Group Draft -> $(BUILD)/$(DOC)-wg-draft.html"

## ISO-styled Word document (pandoc) -> build/
docx: $(SRC) $(TEMPLATE) $(TOOLS)/make-iso-reference.py $(TOOLS)/mmark-to-pandoc.py $(TOOLS)/iso-styles.lua
	mkdir -p $(BUILD)
	python3 $(TOOLS)/make-iso-reference.py "$(TEMPLATE)" "$(BUILD)/iso-reference.docx"
	python3 $(TOOLS)/mmark-to-pandoc.py < $(SRC) > $(BUILD)/$(DOC).pandoc.md
	pandoc $(BUILD)/$(DOC).pandoc.md \
		--reference-doc=$(BUILD)/iso-reference.docx \
		--lua-filter=$(TOOLS)/iso-styles.lua \
		-o $(BUILD)/$(DOC).docx
	rm -f $(BUILD)/iso-reference.docx $(BUILD)/$(DOC).pandoc.md
	@echo "ISO Word document -> $(BUILD)/$(DOC).docx"

clean:
	rm -rf $(BUILD)
	rm -f $(SRCDIR)/$(DOC)*.html $(SRCDIR)/$(DOC)*.xml $(SRCDIR)/$(DOC)*.txt
