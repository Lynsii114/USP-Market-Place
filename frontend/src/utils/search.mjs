export function normalizeSearch(value) {
  return String(value ?? "").normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

export function matchesSearch(query, ...fields) {
  const terms = normalizeSearch(query).split(/\s+/).filter(Boolean);
  const values = fields.flat().map(normalizeSearch);
  return terms.every((term) => values.some((value) => value.includes(term)));
}

export function searchRecords(records, query, getFields) {
  if (!normalizeSearch(query)) return records;
  const normalized = normalizeSearch(query);
  return records.map((record, index) => {
    const fields = getFields(record).map(normalizeSearch);
    const score = fields.reduce((total, value, fieldIndex) => total + (value === normalized ? 100 : value.startsWith(normalized) ? 40 : value.includes(normalized) ? 10 : 0) / (fieldIndex + 1), 0);
    return { record, index, score, matches: matchesSearch(query, fields) };
  }).filter((entry) => entry.matches).sort((a, b) => b.score - a.score || a.index - b.index).map((entry) => entry.record);
}
