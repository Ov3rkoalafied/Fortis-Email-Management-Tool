import { useState } from 'react'
import { Trash2, Hash, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { EmailTable } from './EmailTable'
import { apply } from '../lib/api'
import type { ProjectEmailData, EmailTableRow, ApplyResult } from '../types'

interface Props {
  data: ProjectEmailData
}

type Tab = 'all' | 'duplicates' | 'numbering'

export function ProjectPanel({ data: initial }: Props) {
  const [rows, setRows] = useState<EmailTableRow[]>(initial.rows)
  const [activeTab, setActiveTab] = useState<Tab>('all')
  const [applying, setApplying] = useState<'duplicates' | 'numbering' | null>(null)
  const [result, setResult] = useState<ApplyResult | null>(null)

  const dupCount = rows.filter(r => r.include && r.duplicate_action === 'delete').length
  const numberCount = rows.filter(r => r.include && r.proposed_subject && !r.is_numbered && r.duplicate_action !== 'delete').length

  const handleApplyDuplicates = async () => {
    if (!confirm(`Delete ${dupCount} duplicate email(s) from "${initial.folder_name}"?\n\nThey will be moved to Deleted Items.`)) return
    setApplying('duplicates')
    setResult(null)
    try {
      const res = await apply.duplicates(initial.project_number, rows)
      setResult(res)
      if (res.success) {
        // Mark deleted rows as no longer included
        setRows(r => r.map(row =>
          row.include && row.duplicate_action === 'delete'
            ? { ...row, include: false }
            : row
        ))
      }
    } finally {
      setApplying(null)
    }
  }

  const handleApplyNumbering = async () => {
    if (!confirm(`Rename ${numberCount} email(s) in "${initial.folder_name}"?`)) return
    setApplying('numbering')
    setResult(null)
    try {
      const res = await apply.numbering(initial.project_number, rows)
      setResult(res)
      if (res.success) {
        // Mark renamed rows as numbered
        setRows(r => r.map(row => {
          if (row.include && row.proposed_subject && !row.is_numbered && row.duplicate_action !== 'delete') {
            const newSubject = row.override_subject ? (row.custom_subject ?? row.proposed_subject) : row.proposed_subject
            return { ...row, is_numbered: true, subject: newSubject ?? row.subject, proposed_subject: null }
          }
          return row
        }))
      }
    } finally {
      setApplying(null)
    }
  }

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'all', label: 'All', count: rows.length },
    { id: 'duplicates', label: 'Duplicates', count: rows.filter(r => r.is_duplicate).length },
    { id: 'numbering', label: 'To Number', count: rows.filter(r => r.proposed_subject && !r.is_duplicate).length },
  ]

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-800 flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-white">{initial.folder_name || initial.project_number}</h3>
          <div className="flex gap-3 mt-1 text-xs text-gray-500">
            <span>{rows.length} emails loaded</span>
            {initial.duplicate_count > 0 && <span className="text-red-400">{initial.duplicate_count} duplicates</span>}
            {initial.numbering_count > 0 && <span className="text-blue-400">{initial.numbering_count} to number</span>}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 shrink-0">
          <button
            onClick={handleApplyDuplicates}
            disabled={dupCount === 0 || applying !== null}
            className="flex items-center gap-1.5 bg-red-800 hover:bg-red-700 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {applying === 'duplicates' ? 'Deleting...' : `Delete ${dupCount} dup${dupCount !== 1 ? 's' : ''}`}
          </button>
          <button
            onClick={handleApplyNumbering}
            disabled={numberCount === 0 || applying !== null}
            className="flex items-center gap-1.5 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
          >
            <Hash className="w-3.5 h-3.5" />
            {applying === 'numbering' ? 'Renaming...' : `Number ${numberCount} email${numberCount !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>

      {/* Result banner */}
      {result && (
        <div className={`px-5 py-3 flex items-center gap-2 text-sm border-b border-gray-800
          ${result.success ? 'bg-green-950/50 text-green-300' : 'bg-red-950/50 text-red-300'}`}>
          {result.success ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          <span>
            {result.success
              ? `Done — ${result.processed} processed${result.undo_id ? ` (undo ID: ${result.undo_id})` : ''}`
              : `Completed with errors: ${result.errors.join('; ')}`}
          </span>
          <button onClick={() => setResult(null)} className="ml-auto text-gray-500 hover:text-gray-300">✕</button>
        </div>
      )}

      {/* Error banner */}
      {initial.error && (
        <div className="px-5 py-3 flex items-center gap-2 text-sm bg-red-950/50 text-red-300 border-b border-gray-800">
          <AlertCircle className="w-4 h-4" />
          {initial.error}
        </div>
      )}

      {/* Tabs */}
      <div className="px-5 border-b border-gray-800 flex gap-1">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors
              ${activeTab === tab.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'}`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1.5 bg-gray-700 text-gray-300 rounded-full px-1.5 py-0.5 text-xs">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="p-4">
        <EmailTable rows={rows} onChange={setRows} activeTab={activeTab} />
      </div>
    </div>
  )
}
