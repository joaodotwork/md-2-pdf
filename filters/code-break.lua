-- Make long inline code spans (`like-this-filename.json`, `vngrd_woodcut_v3`)
-- wrappable inside narrow table cells.
--
-- Pandoc emits inline code as \texttt{...}, which has no break opportunities
-- inside the word (no spaces, hyphenchar disabled). Long identifiers then
-- overflow their column. We insert a zero-width \allowbreak after each
-- hyphen / underscore / dot / slash, so TeX can break the line there if it
-- needs to. The visible character stays put.

local break_after = { ['-'] = true, ['_'] = true, ['.'] = true, ['/'] = true }

local function latex_escape(c)
  if c == '\\' then return '\\textbackslash{}'
  elseif c == '{'  then return '\\{'
  elseif c == '}'  then return '\\}'
  elseif c == '$'  then return '\\$'
  elseif c == '&'  then return '\\&'
  elseif c == '%'  then return '\\%'
  elseif c == '#'  then return '\\#'
  elseif c == '_'  then return '\\_'
  elseif c == '^'  then return '\\textasciicircum{}'
  elseif c == '~'  then return '\\textasciitilde{}'
  else return c
  end
end

function Code(elem)
  if FORMAT ~= 'latex' and FORMAT ~= 'pdf' then return nil end
  local text = elem.text
  if not text:find('[-_./]') then return nil end
  local out = {}
  for i = 1, #text do
    local c = text:sub(i, i)
    out[#out + 1] = latex_escape(c)
    if break_after[c] then
      out[#out + 1] = '\\allowbreak{}'
    end
  end
  return pandoc.RawInline('latex', '\\texttt{' .. table.concat(out) .. '}')
end
