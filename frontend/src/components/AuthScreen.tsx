import { useState } from 'react'
import { LogIn, Mail } from 'lucide-react'
import { auth } from '../lib/api'
import type { AuthStatus } from '../types'

interface Props {
  onAuthenticated: (status: AuthStatus) => void
}

export function AuthScreen({ onAuthenticated }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      const status = await auth.login()
      if (status.authenticated) {
        onAuthenticated(status)
      } else {
        setError(status.error ?? 'Login failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail ?? err.message ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 w-full max-w-md text-center">
        <div className="flex justify-center mb-4">
          <div className="bg-blue-600 rounded-full p-4">
            <Mail className="w-8 h-8 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-white mb-1">Fortis Email Manager</h1>
        <p className="text-gray-400 text-sm mb-8">Sign in with your fortisstructural.com account</p>

        {error && (
          <div className="mb-4 bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <button
          onClick={handleLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-colors"
        >
          <LogIn className="w-4 h-4" />
          {loading ? 'Opening browser login...' : 'Sign in with Microsoft'}
        </button>

        {loading && (
          <p className="mt-4 text-gray-500 text-sm">
            Complete the sign-in in the browser window that opened.
          </p>
        )}
      </div>
    </div>
  )
}
