import { useState, useEffect } from 'react'

/**
 * [AGRI-GUARDIAN] Autosave Indicator
 * Shows user that their draft is being saved automatically.
 */

export const AutosaveIndicator = ({ lastSaved, isSaving = false }) => {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (isSaving || lastSaved) {
      setVisible(true)
      const timer = setTimeout(() => setVisible(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [isSaving, lastSaved])

  if (!visible && !isSaving) return null

  const formatTime = (date) => {
    if (!date) return ''
    const d = new Date(date)
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div
      className={`fixed bottom-24 left-4 z-50 transition-all duration-300 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
    >
      <div className="bg-gray-800 text-white text-xs px-3 py-2 rounded-lg shadow-lg flex items-center gap-2">
        {isSaving ? (
          <>
            <span className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></span>
            <span>جاري الحفظ...</span>
          </>
        ) : (
          <>
            <span className="text-green-400">✓</span>
            <span>المسودة محفوظة {lastSaved && `(${formatTime(lastSaved)})`}</span>
          </>
        )}
      </div>
    </div>
  )
}
