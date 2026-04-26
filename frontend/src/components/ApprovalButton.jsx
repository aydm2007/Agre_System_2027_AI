import { useAuth } from '../auth/AuthContext'

export default function ApprovalButton({ creatorId, logId: _logId, onApprove, disabled }) {
  const { user } = useAuth()

  // Strict Security Check (Frontend Proactive State)
  const isCreator = user?.id === creatorId

  // If user is creator, FORCE disable and override onClick
  const isBlocked = isCreator

  const handleClick = (e) => {
    if (isBlocked) return
    onApprove(e)
  }

  if (isBlocked) {
    return (
      <div className="group relative inline-block">
        <button
          type="button"
          disabled
          className="cursor-not-allowed rounded-lg bg-gray-300 px-4 py-2 text-gray-500 opacity-70 grayscale transition-all"
        >
          اعتماد السجل 🔒
        </button>
        {/* Tooltip */}
        <div className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-red-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:block group-hover:opacity-100">
          لا يمكنك اعتماد سجلك الخاص (مبدأ العيون الأربع)
        </div>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      className={`rounded-lg bg-gradient-to-r from-green-600 to-green-500 px-4 py-2 text-white shadow-lg transition-all hover:scale-105 hover:from-green-500 hover:to-green-400 disabled:opacity-50 ${disabled ? 'cursor-not-allowed' : ''}`}
    >
      اعتماد السجل ✅
    </button>
  )
}
