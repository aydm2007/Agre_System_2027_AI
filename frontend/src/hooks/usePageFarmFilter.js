import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useFarmContext } from '../api/farmContext'

const normalizeId = (value) => {
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

export function usePageFarmFilter({
  storageKey,
  allowAllForAdmin = false,
  defaultPolicy = 'first',
} = {}) {
  const { farms, loading } = useFarmContext()
  const { isAdmin, is_superuser } = useAuth()
  const canUseAll = Boolean(allowAllForAdmin && (isAdmin || is_superuser))

  const [farmId, setFarmId] = useState(() => {
    const persisted = localStorage.getItem(storageKey)
    return normalizeId(persisted)
  })

  useEffect(() => {
    if (!storageKey) return
    const persisted = normalizeId(localStorage.getItem(storageKey))
    if (persisted && persisted !== farmId) {
      setFarmId(persisted)
      return
    }
    if (!persisted && farms.length > 0 && defaultPolicy === 'first') {
      const first = normalizeId(farms[0]?.id)
      if (first) {
        setFarmId(first)
        localStorage.setItem(storageKey, first)
      }
    }
  }, [storageKey, farms, defaultPolicy, farmId])

  const setAndPersistFarmId = (nextFarmId) => {
    const normalized = normalizeId(nextFarmId)
    setFarmId(normalized)
    if (storageKey) {
      localStorage.setItem(storageKey, normalized)
    }
  }

  const effectiveFarmScope = useMemo(() => {
    if (canUseAll && farmId === 'all') return null
    return farmId || null
  }, [canUseAll, farmId])

  return {
    loading,
    farmId,
    setFarmId: setAndPersistFarmId,
    farmOptions: farms,
    canUseAll,
    isAll: canUseAll && farmId === 'all',
    effectiveFarmScope,
  }
}
