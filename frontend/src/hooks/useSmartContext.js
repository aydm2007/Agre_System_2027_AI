import { useEffect, useRef } from 'react'
import { get as idbGet, set as idbSet } from 'idb-keyval'

// [Agri-Guardian] Smart Context Key
const CONTEXT_KEY = 'daily-log-smart-context'

/**
 * Hook to handle intelligent defaults and predictive auto-fill
 * Restored from DailyLog.backup.jsx
 */
export function useSmartContext(form, setForm, lookups) {
  const isRestored = useRef(false)

  // 1. Load Context on Mount
  useEffect(() => {
    const loadContext = async () => {
      if (isRestored.current) return

      try {
        const context = await idbGet(CONTEXT_KEY)
        if (!context) return

        // Only apply if form is empty
        if (!form.farm && context.lastFarm) {
          setForm((prev) => ({ ...prev, farm: context.lastFarm }))
        }

        // If single farm available, auto-select
        if (lookups.farms.length === 1) {
          setForm((prev) => ({ ...prev, farm: lookups.farms[0].id }))
        }

        // If context matches current farm, partial fill?
        // For now just farm is enough to save clicks

        isRestored.current = true
      } catch (err) {
        console.warn('Failed to load smart context', err)
      }
    }

    loadContext()
  }, [lookups.farms, setForm, form.farm]) // minimal deps

  // 2. Persist Context on Change
  useEffect(() => {
    if (!form.farm) return

    const saveContext = async () => {
      // Debounce/Throttling handled by the fact that effect runs on change
      // Is it too frequent?
      // We only care about FARM and maybe LOCATION for now.
      try {
        await idbSet(CONTEXT_KEY, {
          lastFarm: form.farm,
          updatedAt: Date.now(),
        })
      } catch (err) {
        // ignore
      }
    }

    const t = setTimeout(saveContext, 2000)
    return () => clearTimeout(t)
  }, [form.farm])

  // 3. Auto-Select Single Option Logic
  useEffect(() => {
    // If Farm is selected, and there is only 1 location, select it?
    // Maybe too aggressive. Let's stick to Farm for now.
  }, [form.farm, lookups.locations])

  // [Agri-Guardian] Phase 10: The Oracle
  const fetchSuggestions = async (date) => {
    if (!navigator.onLine) return []
    // [FIX]: تصحيح التاريخ الفاسد قبل الإرسال — مثال: 60404-02-20
    const dateStr = String(date || '').split('T')[0]
    const [y] = dateStr.split('-').map(Number)
    if (!y || y < 2020 || y > 2099) {
      console.warn('[Oracle] تاريخ فاسد، لن يتم الاستعلام:', date)
      return []
    }
    try {
      const { Suggestions } = await import('../api/client')
      const { data } = await Suggestions.list({ date: dateStr })
      return data.suggestions || []
    } catch (e) {
      console.warn('Oracle failed:', e)
      return []
    }
  }

  return { fetchSuggestions }
}
