import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
} from '@tanstack/react-table'
import { format } from 'date-fns'
import { useState, useMemo } from 'react'
import type { EmailTableRow } from '../types'

interface Props {
  rows: EmailTableRow[]
  onChange: (rows: EmailTableRow[]) => void
  activeTab: 'all' | 'duplicates' | 'numbering'
}

const helper = createColumnHelper<EmailTableRow>()

export function EmailTable({ rows, onChange, activeTab }: Props) {
  const [globalFilter, setGlobalFilter] = useState('')

  const updateRow = (item_id: string, patch: Partial<EmailTableRow>) => {
    onChange(rows.map(r => r.item_id === item_id ? { ...r, ...patch } : r))
  }

  const visibleRows = useMemo(() => {
    if (activeTab === 'duplicates') return rows.filter(r => r.is_duplicate)
    if (activeTab === 'numbering') return rows.filter(r => r.proposed_subject && !r.is_duplicate)
    return rows
  }, [rows, activeTab])

  const columns = useMemo<ColumnDef<EmailTableRow, any>[]>(() => [
    helper.display({
      id: 'include',
      header: () => <span className="text-xs">Include</span>,
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.original.include}
          onChange={e => updateRow(row.original.item_id, { include: e.target.checked })}
          className="w-4 h-4 accent-blue-500"
        />
      ),
      size: 60,
    }),
    helper.accessor('subject', {
      header: 'Current Subject',
      cell: ({ row }) => (
        <span className={`text-xs ${row.original.is_numbered ? 'text-green-400' : 'text-gray-200'}`}>
          {row.original.subject}
        </span>
      ),
      size: 280,
    }),
    helper.display({
      id: 'proposed',
      header: 'Proposed Subject',
      cell: ({ row }) => {
        const r = row.original
        if (!r.proposed_subject && r.duplicate_action !== 'delete') return null
        if (r.duplicate_action === 'delete') {
          return <span className="text-xs text-red-400 italic">DELETE (duplicate)</span>
        }
        if (r.override_subject) {
          return (
            <input
              type="text"
              value={r.custom_subject ?? r.proposed_subject ?? ''}
              onChange={e => updateRow(r.item_id, { custom_subject: e.target.value })}
              className="w-full bg-gray-700 border border-blue-500 text-blue-200 rounded px-2 py-1 text-xs focus:outline-none"
            />
          )
        }
        return (
          <span className="text-xs text-blue-300">{r.proposed_subject}</span>
        )
      },
      size: 280,
    }),
    helper.display({
      id: 'override_subject',
      header: () => <span className="text-xs">Override</span>,
      cell: ({ row }) => {
        const r = row.original
        if (!r.proposed_subject || r.duplicate_action === 'delete') return null
        return (
          <input
            type="checkbox"
            checked={r.override_subject}
            onChange={e => updateRow(r.item_id, {
              override_subject: e.target.checked,
              custom_subject: e.target.checked ? (r.custom_subject ?? r.proposed_subject) : null,
            })}
            className="w-4 h-4 accent-yellow-400"
            title="Override proposed subject"
          />
        )
      },
      size: 70,
    }),
    helper.accessor('sender_name', {
      header: 'Sender',
      cell: ({ getValue }) => <span className="text-xs text-gray-400">{getValue()}</span>,
      size: 150,
    }),
    helper.accessor('received_time', {
      header: 'Received',
      cell: ({ getValue }) => (
        <span className="text-xs text-gray-500 whitespace-nowrap">
          {format(new Date(getValue()), 'MM/dd/yy HH:mm')}
        </span>
      ),
      size: 110,
    }),
    helper.display({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const r = row.original
        if (r.duplicate_action === 'delete') return <Badge color="red">Duplicate</Badge>
        if (r.duplicate_action === 'keep') return <Badge color="yellow">Keep (dup grp)</Badge>
        if (r.is_numbered) return <Badge color="green">Numbered</Badge>
        if (r.proposed_subject) return <Badge color="blue">To Number</Badge>
        return null
      },
      size: 120,
    }),
    helper.display({
      id: 'chain',
      header: 'Chain',
      cell: ({ row }) => {
        const r = row.original
        if (!r.chain_base) return null
        return (
          <span className="text-xs text-gray-500" title={r.chain_reason ?? ''}>
            {r.chain_base}
            {r.chain_reason === 'new_chain' && <span className="text-orange-400 ml-1">(new)</span>}
          </span>
        )
      },
      size: 90,
    }),
  ], [rows])

  const table = useReactTable({
    data: visibleRows,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={globalFilter}
          onChange={e => setGlobalFilter(e.target.value)}
          placeholder="Filter by subject, sender..."
          className="bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-1.5 text-sm w-72 focus:outline-none focus:border-blue-500"
        />
        <span className="text-xs text-gray-500">{visibleRows.length} emails</span>
      </div>

      <div className="overflow-auto rounded-lg border border-gray-800">
        <table className="w-full text-left border-collapse">
          <thead>
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id} className="bg-gray-800 border-b border-gray-700">
                {hg.headers.map(h => (
                  <th
                    key={h.id}
                    className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap"
                    style={{ width: h.column.getSize() }}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center text-gray-600 py-8 text-sm">
                  No emails to show
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row, i) => (
                <tr
                  key={row.id}
                  className={`border-b border-gray-800/60 transition-colors
                    ${!row.original.include ? 'opacity-40' : ''}
                    ${row.original.duplicate_action === 'delete' ? 'bg-red-950/20' : ''}
                    ${i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-900/50'}
                    hover:bg-gray-800/50`}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-3 py-2 align-middle" style={{ width: cell.column.getSize() }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  const colors: Record<string, string> = {
    red: 'bg-red-900/50 text-red-300 border-red-800',
    green: 'bg-green-900/50 text-green-300 border-green-800',
    blue: 'bg-blue-900/50 text-blue-300 border-blue-800',
    yellow: 'bg-yellow-900/50 text-yellow-300 border-yellow-800',
    orange: 'bg-orange-900/50 text-orange-300 border-orange-800',
  }
  return (
    <span className={`inline-flex text-xs px-2 py-0.5 rounded-full border font-medium ${colors[color] ?? colors.blue}`}>
      {children}
    </span>
  )
}
