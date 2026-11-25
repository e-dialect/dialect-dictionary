// A shared search link may contain a missing, malformed or outdated page number.
export function resultPage (value, total, pageSize) {
  const page = typeof value === 'string' || typeof value === 'number' ? Number(value) : NaN
  if (!Number.isSafeInteger(page) || page < 1) return 1
  return Math.min(page, Math.max(1, Math.ceil(total / pageSize)))
}
