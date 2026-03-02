import { useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'

interface Props {
  onLoad: (projectNumbers: string[], limit: number, timeWindow: number) => void
  loading: boolean
}

export function ProjectInput({ onLoad, loading }: Props) {
  const [input, setInput] = useState('')
  const [limit, setLimit] = useState(500)
  const [timeWindow, setTimeWindow] = useState(5)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const numbers = input
      .split(',')
      .map(s => s.trim())
      .filter(s => /^\d{5}$/.test(s))
    if (numbers.length === 0) return
    onLoad(numbers, limit, timeWindow)
  }

  const invalid = input.trim().length > 0 &&
    input.split(',').some(s => s.trim() && !/^\d{5}$/.test(s.trim()))

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Load Project Emails</h2>
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-48">
          <label className="block text-xs text-gray-400 mb-1">Project numbers (5 digits, comma-separated)</label>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="e.g. 19035, 24078"
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
          {invalid && (
            <p className="text-red-400 text-xs mt-1">All project numbers must be exactly 5 digits</p>
          )}
        </div>

        <div className="w-28">
          <label className="block text-xs text-gray-400 mb-1">Email limit</label>
          <input
            type="number"
            value={limit}
            min={1}
            max={500}
            onChange={e => setLimit(Math.min(500, Math.max(1, Number(e.target.value))))}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="w-36">
          <label className="block text-xs text-gray-400 mb-1">Dup. time window (min)</label>
          <input
            type="number"
            value={timeWindow}
            min={1}
            max={60}
            onChange={e => setTimeWindow(Math.max(1, Number(e.target.value)))}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading || invalid || !input.trim()}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? 'Loading...' : 'Load'}
          </button>
        </div>
      </div>
    </form>
  )
}
