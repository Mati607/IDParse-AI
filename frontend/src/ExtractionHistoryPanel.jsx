import { useCallback, useEffect, useState } from 'react'
import {
  deleteExtractionSession,
  extractionSessionCsvUrl,
  extractionSessionExportUrl,
  extractionSessionHtmlUrl,
  extractionSessionReadinessMdUrl,
  fillFormFromSession,
  getExtractionSession,
  listExtractionSessions,
  patchExtractionSession,
} from './api/extractionApi'
import './ExtractionHistoryPanel.css'

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function splitTagsInput(s) {
  return String(s || '')
    .split(/[,]+/)
    .map((x) => x.trim())
    .filter(Boolean)
}

const GRADE_OPTIONS = ['A', 'B', 'C', 'D', 'F']

/**
 * Sidebar list of server-stored extraction sessions: load, export, delete, re-fill.
 */
export function ExtractionHistoryPanel({
  refreshToken,
  formUrl,
  onLoadExtracted,
  onFillResult,
  onError,
  onBusy,
}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState(null)

  const emptyFilters = () => ({
    q: '',
    tagStr: '',
    minScore: '',
    grades: [],
    hasFill: 'any',
  })

  const [filterDraft, setFilterDraft] = useState(emptyFilters)
  const [filters, setFilters] = useState(emptyFilters)

  const [tagDrafts, setTagDrafts] = useState({})

  const loadList = useCallback(async () => {
    setLoading(true)
    onBusy?.(true)
    try {
      let hasFill = null
      if (filters.hasFill === 'yes') hasFill = true
      if (filters.hasFill === 'no') hasFill = false
      const minRaw = filters.minScore === '' ? null : Number(filters.minScore)
      const data = await listExtractionSessions({
        limit: 40,
        offset: 0,
        q: filters.q.trim() || undefined,
        tag: splitTagsInput(filters.tagStr),
        minScore: minRaw != null && Number.isFinite(minRaw) ? minRaw : undefined,
        grade: filters.grades,
        hasFill,
      })
      const list = data.items || []
      setItems(list)
      setTotal(data.total ?? 0)
      const drafts = {}
      list.forEach((row) => {
        drafts[row.id] = (row.tags || []).join(', ')
      })
      setTagDrafts(drafts)
    } catch (e) {
      onError?.(e.message || 'Could not load saved sessions.')
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
      onBusy?.(false)
    }
  }, [onBusy, onError, filters])

  useEffect(() => {
    loadList()
  }, [loadList, refreshToken])

  const toggleGrade = (g) => {
    setFilterDraft((prev) => ({
      ...prev,
      grades: prev.grades.includes(g) ? prev.grades.filter((x) => x !== g) : [...prev.grades, g],
    }))
  }

  const applyFilterDraft = () => {
    setFilters({ ...filterDraft })
  }

  const clearFilters = () => {
    const z = emptyFilters()
    setFilterDraft(z)
    setFilters(z)
  }

  const handleLoad = async (id) => {
    setWorkingId(id)
    onBusy?.(true)
    try {
      const row = await getExtractionSession(id)
      onLoadExtracted?.(row.extracted, {
        id: row.id,
        title: row.title,
        default_form_url: row.default_form_url,
        readiness: row.readiness,
      })
    } catch (e) {
      onError?.(e.message || 'Failed to load session.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  const handleSaveTags = async (id) => {
    const raw = tagDrafts[id] ?? ''
    setWorkingId(id)
    onBusy?.(true)
    try {
      const tags = splitTagsInput(raw)
      const row = await patchExtractionSession(id, { tags })
      setTagDrafts((d) => ({ ...d, [id]: (row.tags || []).join(', ') }))
      await loadList()
    } catch (e) {
      onError?.(e.message || 'Could not update tags.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this saved extraction from the server?')) return
    setWorkingId(id)
    onBusy?.(true)
    try {
      await deleteExtractionSession(id)
      await loadList()
    } catch (e) {
      onError?.(e.message || 'Delete failed.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  const handleFill = async (id) => {
    const url = formUrl?.trim()
    if (!url) {
      onError?.('Enter the form URL above before filling from a saved session.')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      onError?.('Form URL must start with http:// or https://')
      return
    }
    setWorkingId(id)
    onBusy?.(true)
    try {
      const data = await fillFormFromSession(id, url)
      onFillResult?.(data)
    } catch (e) {
      onError?.(e.message || 'Fill from session failed.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  return (
    <section className="history-panel" aria-labelledby="history-heading">
      <div className="history-panel-header">
        <h2 id="history-heading">Saved extractions</h2>
        <button type="button" className="history-refresh" onClick={loadList} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      <p className="history-panel-hint">
        Stored on the server (SQLite). Filter by text, tags, readiness, or fill state. Edit comma-separated tags per
        session (saved on the server).
      </p>

      <div className="history-filters" aria-label="Session filters">
        <label className="history-filter-field">
          <span>Search</span>
          <input
            type="search"
            value={filterDraft.q}
            onChange={(e) => setFilterDraft((f) => ({ ...f, q: e.target.value }))}
            placeholder="Title, notes, filenames…"
            autoComplete="off"
          />
        </label>
        <label className="history-filter-field">
          <span>Has tag (any)</span>
          <input
            type="text"
            value={filterDraft.tagStr}
            onChange={(e) => setFilterDraft((f) => ({ ...f, tagStr: e.target.value }))}
            placeholder="e.g. review, urgent"
            autoComplete="off"
          />
        </label>
        <label className="history-filter-field history-filter-narrow">
          <span>Min score</span>
          <input
            type="number"
            min={0}
            max={100}
            step={1}
            value={filterDraft.minScore}
            onChange={(e) => setFilterDraft((f) => ({ ...f, minScore: e.target.value }))}
            placeholder="—"
          />
        </label>
        <label className="history-filter-field">
          <span>Grades</span>
          <span className="history-grade-toggles">
            {GRADE_OPTIONS.map((g) => (
              <label key={g} className="history-grade-chip">
                <input
                  type="checkbox"
                  checked={filterDraft.grades.includes(g)}
                  onChange={() => toggleGrade(g)}
                />
                {g}
              </label>
            ))}
          </span>
        </label>
        <label className="history-filter-field history-filter-narrow">
          <span>Last fill</span>
          <select
            value={filterDraft.hasFill}
            onChange={(e) => setFilterDraft((f) => ({ ...f, hasFill: e.target.value }))}
          >
            <option value="any">Any</option>
            <option value="yes">Saved</option>
            <option value="no">None</option>
          </select>
        </label>
        <div className="history-filter-actions">
          <button type="button" className="history-filter-apply" onClick={applyFilterDraft} disabled={loading}>
            Apply filters
          </button>
          <button type="button" className="history-filter-clear" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </div>

      {loading && items.length === 0 ? (
        <p className="history-empty">Loading sessions…</p>
      ) : items.length === 0 ? (
        <p className="history-empty">
          No sessions match. Clear filters or use &quot;Save extraction&quot; after a successful extract.
        </p>
      ) : (
        <ul className="history-list">
          {items.map((row) => (
            <li key={row.id} className="history-item">
              <div className="history-item-top">
                <span className="history-title">{row.title || 'Untitled session'}</span>
                <span className="history-date">{formatWhen(row.created_at)}</span>
              </div>
              <div className="history-tags-row">
                {(row.tags || []).length > 0 && (
                  <ul className="history-tag-chips" aria-label="Tags">
                    {(row.tags || []).map((t) => (
                      <li key={t}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="history-meta">
                P:{row.field_counts?.passport ?? 0} · A:{row.field_counts?.attorney ?? 0}
                {row.readiness_grade != null && row.readiness_score != null
                  ? ` · readiness ${row.readiness_grade} (${row.readiness_score})`
                  : ''}
                {row.has_last_fill ? ' · last fill saved' : ''}
              </div>
              <label className="history-tags-edit">
                <span className="sr-only">Tags for this session</span>
                <input
                  type="text"
                  value={tagDrafts[row.id] ?? ''}
                  onChange={(e) => setTagDrafts((d) => ({ ...d, [row.id]: e.target.value }))}
                  placeholder="Tags: comma-separated"
                  autoComplete="off"
                />
                <button
                  type="button"
                  className="history-tags-save"
                  onClick={() => handleSaveTags(row.id)}
                  disabled={workingId === row.id}
                >
                  Save tags
                </button>
              </label>
              <div className="history-actions">
                <button
                  type="button"
                  onClick={() => handleLoad(row.id)}
                  disabled={workingId === row.id}
                >
                  Load
                </button>
                <button
                  type="button"
                  onClick={() => handleFill(row.id)}
                  disabled={workingId === row.id}
                  className="history-primary"
                >
                  Fill form
                </button>
                <a
                  className="history-link"
                  href={extractionSessionExportUrl(row.id)}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  JSON
                </a>
                <a
                  className="history-link"
                  href={extractionSessionCsvUrl(row.id)}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  CSV
                </a>
                <a
                  className="history-link"
                  href={extractionSessionHtmlUrl(row.id)}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  HTML
                </a>
                <a
                  className="history-link"
                  href={extractionSessionReadinessMdUrl(row.id)}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  Readiness.md
                </a>
                <button
                  type="button"
                  className="history-danger"
                  onClick={() => handleDelete(row.id)}
                  disabled={workingId === row.id}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="history-footer">{total} session(s) total</p>
    </section>
  )
}
