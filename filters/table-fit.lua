-- Assign equal column widths to tables that have none set.
--
-- Pandoc's pipe-table reader leaves column widths undefined when the
-- separator-row dashes are short (e.g. `|---|---|`). The LaTeX writer then
-- emits `l` columns, which do not wrap and overflow the page on wide tables.
-- Setting equal widths summing to 1.0 makes the writer emit `p{...}` columns
-- sized to \linewidth, so cells wrap.

function Table(tbl)
  local n = #tbl.colspecs
  if n == 0 then return nil end

  local total = 0
  for _, c in ipairs(tbl.colspecs) do
    local w = c[2]
    if type(w) == "number" then
      total = total + w
    end
  end
  if total > 0 then return nil end

  local equal = 1.0 / n
  for i = 1, n do
    tbl.colspecs[i] = { tbl.colspecs[i][1], equal }
  end
  return tbl
end
