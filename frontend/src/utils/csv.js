export function downloadCSV(filename, rows, headers) {
  const headerLine = headers.map((h) => csvEscape(h.label)).join(',')
  const lines = rows.map((row) =>
    headers.map((h) => csvEscape(row[h.key] ?? '')).join(',')
  )
  const csv = [headerLine, ...lines].join('\r\n')
  const bom = '\uFEFF'
  const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function csvEscape(value) {
  const str = value === null || value === undefined ? '' : String(value)
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}
