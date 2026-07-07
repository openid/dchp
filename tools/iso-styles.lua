--[[
  ISO front/back-matter formatting for the pandoc -> Word build.

  1. Title block. mmark-to-pandoc.py carries the title across as two pandoc
     metadata fields (`title` and an optional `subtitle` holding the document
     status); here we render them as a centred title plus a status subtitle at
     the very top. Without this, pandoc + the ISO reference document produce a
     Word document with no title at all.

  2. Foreword / Introduction / Bibliography. These are ISO headings that must NOT
     be auto-numbered, so they use the template's ForewordTitle / IntroTitle /
     BiblioTitle paragraph styles instead of Heading1 (so the first real
     Heading1, Scope, still numbers as clause 1). Some docx viewers apply a
     custom style's paragraph properties but not its run properties, so the text
     falls back to plain body formatting. To render correctly in every viewer
     (not just Microsoft Word) we also set bold + size (14 pt) directly on the
     run, in addition to referencing the ISO style.
]]--

local title_style = {
  ["Foreword"] = "ForewordTitle",
  ["Introduction"] = "IntroTitle",
  ["Bibliography"] = "BiblioTitle",
}
local HEADING_SIZE = "28" -- half-points (14 pt)

local function xml_escape(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"))
end

-- Unnumbered ISO heading: ISO paragraph style + explicit bold/size on the run.
local function heading_block(text, style)
  local xml = table.concat({
    '<w:p><w:pPr><w:pStyle w:val="', style, '"/></w:pPr>',
    '<w:r><w:rPr><w:b/><w:sz w:val="', HEADING_SIZE, '"/>',
    '<w:szCs w:val="', HEADING_SIZE, '"/></w:rPr>',
    '<w:t xml:space="preserve">', xml_escape(text), '</w:t></w:r></w:p>',
  })
  return pandoc.RawBlock("openxml", xml)
end

-- A centred paragraph (used for the title and status subtitle).
local function centred_block(text, size, bold, after)
  local xml = table.concat({
    '<w:p><w:pPr><w:jc w:val="center"/>',
    '<w:spacing w:before="240" w:after="', after, '"/></w:pPr>',
    '<w:r><w:rPr>', bold and "<w:b/>" or "",
    '<w:sz w:val="', size, '"/><w:szCs w:val="', size, '"/></w:rPr>',
    '<w:t xml:space="preserve">', xml_escape(text), '</w:t></w:r></w:p>',
  })
  return pandoc.RawBlock("openxml", xml)
end

function Header(el)
  if el.level == 1 then
    local text = pandoc.utils.stringify(el)
    local style = title_style[text]
    if style then
      return heading_block(text, style)
    end
  end
  return nil
end

function Pandoc(doc)
  local meta_title = doc.meta.title
  if meta_title then
    local main = pandoc.utils.stringify(meta_title)
    local sub = doc.meta.subtitle and pandoc.utils.stringify(doc.meta.subtitle) or nil
    doc.meta.title = nil    -- suppress pandoc's own (unstyled) title block
    doc.meta.subtitle = nil
    local head = { centred_block(main, "36", true, "120") } -- 18 pt bold
    if sub and sub ~= "" then
      head[#head + 1] = centred_block(sub, "26", false, "360") -- 13 pt
    end
    for _, b in ipairs(doc.blocks) do
      head[#head + 1] = b
    end
    doc.blocks = head
  end
  return doc
end
