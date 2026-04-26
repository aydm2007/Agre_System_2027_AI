import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import ar from '../i18n/ar'
import { LogIn, User, Lock, AlertCircle } from 'lucide-react'

const TEXT = ar.login

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      console.error('Login error:', err)
      if (err.response) {
        const detail = err.response.data?.detail
        setError(detail || TEXT.invalid)
      } else if (err.request) {
        setError(TEXT.network)
      } else {
        setError(TEXT.unexpected)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      dir="rtl"
      className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"
    >
      <div className="max-w-md w-full p-8 bg-white dark:bg-slate-800 rounded-3xl shadow-2xl border border-gray-100 dark:border-slate-700/50 backdrop-blur-xl relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -me-32 -mt-32 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -ms-32 -mb-32 pointer-events-none" />

        <div className="relative">
          <div className="text-center mb-10">
            <div className="mb-6">
              <img 
                src="/assets/logo_ye.png" 
                alt="Logo" 
                className="w-32 h-32 mx-auto object-contain drop-shadow-xl animate-pulse-slow"
                onError={(e) => { e.target.src = "https://via.placeholder.com/150?text=YE+LOGO"; }}
              />
            </div>
            <h2 className="text-xl font-bold text-emerald-800 dark:text-emerald-400 mb-4 font-cairo leading-relaxed">
              المؤسسة الاقتصادية اليمنية<br/>
              قطاع الانتاج الزراعي والحيواني<br/>
              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">النظام الفني الرقابي</span>
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 block">
                {TEXT.username}
              </label>
              <div className="relative group">
                <User className="absolute right-4 top-3.5 w-5 h-5 text-gray-400 group-focus-within:text-emerald-500 transition-colors" />
                <input
                  id="username"
                  data-testid="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pr-12 pl-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all outline-none font-medium dark:text-white"
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 block">
                {TEXT.password}
              </label>
              <div className="relative group">
                <Lock className="absolute right-4 top-3.5 w-5 h-5 text-gray-400 group-focus-within:text-emerald-500 transition-colors" />
                <input
                  id="password"
                  data-testid="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pr-12 pl-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all outline-none font-medium dark:text-white"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                <p className="text-sm font-bold text-rose-600 dark:text-rose-400">{error}</p>
              </div>
            )}

            <button
              data-testid="login-submit"
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/25 transform transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{TEXT.loading}</span>
                </>
              ) : (
                <span>{TEXT.submit}</span>
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-xs text-gray-400 dark:text-gray-500 font-medium">
              Agri-Guardian System © 2026
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
