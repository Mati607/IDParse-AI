import { API_BASE } from '../config'

/**
 * Normalize FastAPI error payloads (string detail or validation_errors object).
 */
export function formatApiError(err) {
  const d = err?.detail
  if (typeof d === 'string') return d
  if (d && typeof d === 'object' && d.validation_errors) {
    const parts = []
    if (d.validation_errors.passport) parts.push(`Passport: ${d.validation_errors.passport}`)
    if (d.validation_errors.g28) parts.push(`G-28: ${d.validation_errors.g28}`)
    if (parts.length) return `The uploaded document(s) are not valid. ${parts.join(' ')}`
    return d.detail || 'Document validation failed. Please upload a valid passport and/or G-28 form.'
  }
  return (d && d.detail) || (typeof d === 'string' ? d : null) || JSON.stringify(err?.detail ?? err) || 'Request failed'
}

async function parseJsonOrThrow(res) {
  if (res.ok) {
    if (res.status === 204) return null
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) return res.json()
    return res.text()
  }
  const err = await res.json().catch(() => ({ detail: res.statusText }))
  throw new Error(formatApiError(err))
}

export async function fetchExtractionReadiness(extracted, { catalog = false } = {}) {
  const q = catalog ? '?catalog=true' : ''
  const res = await fetch(`${API_BASE}/extraction-readiness${q}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(extracted),
  })
  return parseJsonOrThrow(res)
}

export async function fetchExtractionQualityRules() {
  const res = await fetch(`${API_BASE}/extraction-quality/rules`)
  return parseJsonOrThrow(res)
}

export async function compareExtractions(payload) {
  const res = await fetch(`${API_BASE}/compare-extractions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJsonOrThrow(res)
}

export async function listComparePresets() {
  const res = await fetch(`${API_BASE}/compare-extractions/presets`)
  return parseJsonOrThrow(res)
}

export async function runComparePreset(presetId) {
  const res = await fetch(`${API_BASE}/compare-extractions/run-preset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset_id: presetId }),
  })
  return parseJsonOrThrow(res)
}

export async function recomputeSessionReadiness(sessionId, { catalog = true } = {}) {
  const q = catalog ? '?catalog=true' : ''
  const res = await fetch(`${API_BASE}/extraction-sessions/${sessionId}/recompute-readiness${q}`, {
    method: 'POST',
  })
  return parseJsonOrThrow(res)
}

export async function previewFill(extracted) {
  const res = await fetch(`${API_BASE}/preview-fill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(extracted),
  })
  return parseJsonOrThrow(res)
}

/**
 * @param {object} [opts]
 * @param {number} [opts.limit]
 * @param {number} [opts.offset]
 * @param {string} [opts.q] - search title, notes, filenames, extraction JSON
 * @param {string[]} [opts.tag] - match any of these normalized tags
 * @param {number} [opts.minScore] - minimum readiness score
 * @param {string[]} [opts.grade] - readiness grades (e.g. A, B)
 * @param {boolean|null} [opts.hasFill] - true / false to filter on last fill
 */
export async function listExtractionSessions(opts = {}, legacyOffset = 0) {
  const o =
    typeof opts === 'number'
      ? { limit: opts, offset: legacyOffset }
      : opts
  const {
    limit = 50,
    offset = 0,
    q,
    tag = [],
    minScore,
    grade = [],
    hasFill,
  } = o

  const sp = new URLSearchParams()
  sp.set('limit', String(limit))
  sp.set('offset', String(offset))
  if (q != null && String(q).trim()) sp.set('q', String(q).trim())
  if (Array.isArray(tag)) {
    tag.forEach((t) => {
      const s = String(t).trim()
      if (s) sp.append('tag', s)
    })
  }
  if (minScore != null && minScore !== '' && !Number.isNaN(Number(minScore))) {
    sp.set('min_score', String(Number(minScore)))
  }
  if (Array.isArray(grade)) {
    grade.forEach((g) => {
      const s = String(g).trim().toUpperCase()
      if (s) sp.append('grade', s)
    })
  }
  if (hasFill === true) sp.set('has_fill', 'true')
  if (hasFill === false) sp.set('has_fill', 'false')

  const res = await fetch(`${API_BASE}/extraction-sessions?${sp.toString()}`)
  return parseJsonOrThrow(res)
}

export async function patchExtractionSession(id, body) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrow(res)
}

export async function createExtractionSession(payload) {
  const res = await fetch(`${API_BASE}/extraction-sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJsonOrThrow(res)
}

export async function getExtractionSession(id) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}`)
  return parseJsonOrThrow(res)
}

export async function deleteExtractionSession(id) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}`, { method: 'DELETE' })
  return parseJsonOrThrow(res)
}

export function extractionSessionExportUrl(id) {
  return `${API_BASE}/extraction-sessions/${id}/export`
}

export function extractionSessionCsvUrl(id) {
  return `${API_BASE}/extraction-sessions/${id}/export.csv`
}

export function extractionSessionHtmlUrl(id) {
  return `${API_BASE}/extraction-sessions/${id}/export.html`
}

export function extractionSessionReadinessMdUrl(id) {
  return `${API_BASE}/extraction-sessions/${id}/readiness.md`
}

export function extractionSessionsSchemaUrl() {
  return `${API_BASE}/extraction-sessions/export-schema`
}

export async function fillFormFromSession(id, formUrl) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}/fill-form`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ form_url: formUrl.trim() }),
  })
  return parseJsonOrThrow(res)
}
