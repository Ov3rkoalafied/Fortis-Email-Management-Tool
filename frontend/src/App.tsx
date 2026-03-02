import { useState, useEffect } from 'react'
import { LogOut, Wifi } from 'lucide-react'
import { AuthScreen } from './components/AuthScreen'
import { ProjectInput } from './components/ProjectInput'
import { ProjectPanel } from './components/ProjectPanel'
import { auth, emails } from './lib/api'
import type { AuthStatus, ProjectEmailData } from './types'

export default function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingEmails, setLoadingEmails] = useState(false)
  const [projects, setProjects] = useState<ProjectEmailData[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    auth.status()
      .then(s => setAuthStatus(s))
      .catch(() => setAuthStatus({ authenticated: false, error: 'Cannot reach backend. Is it running on :8000?' }))
      .finally(() => setLoading(false))
  }, [])

  const handleLogout = async () => {
    await auth.logout()
    setAuthStatus({ authenticated: false })
    setProjects([])
  }

  const handleLoad = async (projectNumbers: string[], limit: number, timeWindow: number) => {
    setLoadingEmails(true)
    setLoadError(null)
    setProjects([])
    try {
      const data = await emails.load(projectNumbers, limit, timeWindow)
      setProjects(data)
    } catch (err: any) {
      setLoadError(err.response?.data?.detail ?? err.message ?? 'Failed to load emails')
    } finally {
      setLoadingEmails(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <span className="text-gray-500 text-sm">Connecting to backend...</span>
      </div>
    )
  }

  if (!authStatus?.authenticated) {
    return (
      <>
        {authStatus?.error && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-red-900 border border-red-700 text-red-200 text-sm px-4 py-2 rounded-lg z-50">
            {authStatus.error}
          </div>
        )}
        <AuthScreen onAuthenticated={s => setAuthStatus(s)} />
      </>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold text-white">Fortis Email Manager</h1>
          <p className="text-xs text-gray-500">Outlook Public Folder Tools</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-green-400">
            <Wifi className="w-3.5 h-3.5" />
            <span>{authStatus.email}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-6 flex flex-col gap-5">
        <ProjectInput onLoad={handleLoad} loading={loadingEmails} />

        {loadError && (
          <div className="bg-red-950/40 border border-red-800 text-red-300 rounded-lg px-4 py-3 text-sm">
            {loadError}
          </div>
        )}

        {loadingEmails && (
          <div className="text-center text-gray-500 py-12 text-sm">
            Loading emails — fetching metadata, then bodies only for potential duplicates...
          </div>
        )}

        {projects.map(project => (
          <ProjectPanel key={project.project_number} data={project} />
        ))}
      </main>
    </div>
  )
}
