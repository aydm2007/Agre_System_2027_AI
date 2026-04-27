import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { get, set, del } from 'idb-keyval'
import { Crops, Locations, Assets, LocationWells, CropVarieties, Activities, Farms } from './client'
import { useAuth } from '../auth/AuthContext'
import { getAuthContext } from '../auth/contextBridge'

// ... (existing constants) ...

const LEGACY_SELECTED_FARM_KEY = 'selected_farm_id'
const PAGE_FARM_PREFIX = 'page_farm.'

export const resolvePageFarmStorageKey = (pathname) => {
  const normalized = String(pathname || '/').split('?')[0]
  const parts = normalized.split('/').filter(Boolean)
  const page = parts[0] || 'dashboard'
  return `${PAGE_FARM_PREFIX}${page}`
}

const readPageFarm = (pathname) => {
  const pageKey = resolvePageFarmStorageKey(pathname)
  const pageScoped = localStorage.getItem(pageKey)
  if (pageScoped) return pageScoped
  const legacy = localStorage.getItem(LEGACY_SELECTED_FARM_KEY)
  return legacy || ''
}

const writePageFarm = (pathname, farmId) => {
  const pageKey = resolvePageFarmStorageKey(pathname)
  const normalizedFarmId = String(farmId)
  localStorage.setItem(pageKey, normalizedFarmId)
  localStorage.setItem(LEGACY_SELECTED_FARM_KEY, normalizedFarmId)
}

const clearPageFarm = (pathname) => {
  const pageKey = resolvePageFarmStorageKey(pathname)
  localStorage.removeItem(pageKey)
}

const normalizeFarm = (farm) => ({
  ...farm,
  id: String(farm?.farm_id ?? farm?.id ?? ''),
  name: farm?.farm_name ?? farm?.name ?? '',
})

const areFarmListsEqual = (left, right) => {
  if (left === right) return true
  if (!Array.isArray(left) || !Array.isArray(right)) return false
  if (left.length !== right.length) return false
  return left.every((farm, index) => {
    const candidate = right[index]
    return (
      String(farm?.id ?? '') === String(candidate?.id ?? '') &&
      String(farm?.name ?? '') === String(candidate?.name ?? '')
    )
  })
}

const setFarmListState = (setFarms, nextFarmList) => {
  setFarms((previous) => (areFarmListsEqual(previous, nextFarmList) ? previous : nextFarmList))
}

const resolveNextSelection = (pathname, farmList, currentSelectedFarmId) => {
  const normalizedList = farmList.filter((farm) => String(farm.id || '').length > 0)
  const pageFarmId = String(readPageFarm(pathname) || '')
  const hasStoredFarm = normalizedList.some((farm) => String(farm.id) === pageFarmId)
  const fallbackId = String(currentSelectedFarmId || '')
  const hasCurrentFarm = normalizedList.some((farm) => String(farm.id) === fallbackId)

  if (normalizedList.length === 0) {
    return { selectedFarmId: '', shouldPersist: false, shouldClear: true }
  }

  if (pageFarmId && hasStoredFarm) {
    return {
      selectedFarmId: pageFarmId,
      shouldPersist: false,
      shouldClear: false,
    }
  }

  if (fallbackId && hasCurrentFarm) {
    return {
      selectedFarmId: fallbackId,
      shouldPersist: true,
      shouldClear: false,
    }
  }

  return {
    selectedFarmId: String(normalizedList[0].id),
    shouldPersist: true,
    shouldClear: false,
  }
}

const applyFarmSelection = (pathname, farmList, currentSelectedFarmId, setSelection) => {
  const selection = resolveNextSelection(pathname, farmList, currentSelectedFarmId)
  setSelection((previous) =>
    previous === selection.selectedFarmId ? previous : selection.selectedFarmId,
  )
  if (selection.shouldClear) {
    clearPageFarm(pathname)
  } else if (selection.shouldPersist) {
    writePageFarm(pathname, selection.selectedFarmId)
  }
}

// [AGRI-GUARDIAN] Farm Context Implementation (per-page scope)
export const FarmContext = createContext()

export const FarmProvider = ({ children }) => {
  const location = useLocation()
  const { userFarms, isLoading: isAuthLoading, isAuthenticated } = useAuth()
  const [farms, setFarms] = useState([])
  const [selectedFarmId, setSelectedFarmId] = useState(() => readPageFarm(location.pathname))
  const [loading, setLoading] = useState(true)

  const pageFarmKey = useMemo(
    () => resolvePageFarmStorageKey(location.pathname),
    [location.pathname],
  )

  useEffect(() => {
    if (isAuthLoading) {
      setLoading(true)
      return
    }

    const loadFarms = async () => {
      const profileFarms = safeArray(userFarms).map(normalizeFarm)
      if (!isAuthenticated) {
        setFarmListState(setFarms, [])
        setSelectedFarmId((previous) => (previous === '' ? previous : ''))
        clearPageFarm(location.pathname)
        setLoading(false)
        return
      }

      if (profileFarms.length > 0) {
        setFarmListState(setFarms, profileFarms)
        applyFarmSelection(location.pathname, profileFarms, selectedFarmId, setSelectedFarmId)
        setLoading(false)
        return
      }

      if (farms.length > 0) {
        applyFarmSelection(location.pathname, farms, selectedFarmId, setSelectedFarmId)
        setLoading(false)
        return
      }

      try {
        const response = await Farms.list()
        const farmList = safeArray(response).map(normalizeFarm)
        setFarmListState(setFarms, farmList)
        applyFarmSelection(location.pathname, farmList, selectedFarmId, setSelectedFarmId)
      } catch (error) {
        const status = error?.response?.status
        if ((status === 403 || status === 404) && profileFarms.length > 0) {
          console.warn('Falling back to profile-scoped farms for context selection.')
          setFarmListState(setFarms, profileFarms)
          applyFarmSelection(location.pathname, profileFarms, selectedFarmId, setSelectedFarmId)
        } else if (isAuthenticated && profileFarms.length > 0) {
          console.warn(
            'Farms endpoint failed; using authenticated profile farms as fallback.',
            error,
          )
          setFarmListState(setFarms, profileFarms)
          applyFarmSelection(location.pathname, profileFarms, selectedFarmId, setSelectedFarmId)
        } else {
          console.warn(
            'Failed to load farms for context; continuing without farm selection.',
            error,
          )
          setFarmListState(setFarms, [])
          setSelectedFarmId((previous) => (previous === '' ? previous : ''))
          clearPageFarm(location.pathname)
        }
      } finally {
        setLoading(false)
      }
    }

    loadFarms()
  }, [farms, isAuthLoading, isAuthenticated, location.pathname, selectedFarmId, userFarms])

  useEffect(() => {
    applyFarmSelection(location.pathname, farms, selectedFarmId, setSelectedFarmId)
  }, [location.pathname, farms, selectedFarmId])

  const handleSelectFarm = useCallback(
    (id) => {
      const strId = String(id)
      setSelectedFarmId(strId)
      writePageFarm(location.pathname, strId)
    },
    [location.pathname],
  )

  return (
    <FarmContext.Provider
      value={{
        farms,
        selectedFarmId,
        selectFarm: handleSelectFarm,
        loading,
        pageFarmKey,
      }}
    >
      {children}
    </FarmContext.Provider>
  )
}

export const useFarmContext = () => {
  const context = useContext(FarmContext)
  if (!context) {
    throw new Error('useFarmContext must be used within a FarmProvider')
  }
  return context
}

const FARM_CONTEXT_PREFIX = 'farm-context'
const MAX_CONTEXT_AGE_MS = 6 * 60 * 60 * 1000

const safeArray = (payload) => {
  if (!payload) return []
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload?.data?.results)) return payload.data.results
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

const safeListRequest = async (factory) => {
  try {
    const response = await factory()
    return safeArray(response)
  } catch (error) {
    if (error?.response?.status === 404) {
      return []
    }
    console.warn(`⚠️ Warning: Failed to load list data`, error.message)
    return []
  }
}

const resolveUserScope = () => {
  try {
    const context = getAuthContext()
    const user = context?.user || {}
    const candidates = [
      user.id,
      user.pk,
      context?.user_id,
      user.uuid,
      user.username ? `name:${user.username}` : null,
    ]
    const identifier = candidates.find(
      (value) => value !== null && value !== undefined && value !== '',
    )
    return identifier ? `user:${identifier}` : 'user:anonymous'
  } catch (error) {
    console.warn('Failed to resolve farm context scope', error)
    return 'user:anonymous'
  }
}

const buildContextKey = (farmId) => {
  const scope = resolveUserScope()
  return `${FARM_CONTEXT_PREFIX}::${scope}::${farmId}`
}

const readCachedContext = async (farmId) => {
  const raw = await get(buildContextKey(farmId))
  if (!raw || typeof raw !== 'object') {
    return null
  }
  return raw
}

const writeCachedContext = async (farmId, payload) => {
  await set(buildContextKey(farmId), payload)
}

const isStale = (context) => {
  if (!context?.fetchedAt) return true
  const fetched = new Date(context.fetchedAt).getTime()
  if (!Number.isFinite(fetched)) return true
  return Date.now() - fetched > MAX_CONTEXT_AGE_MS
}

const fetchFarmContextFromServer = async (farmId) => {
  const [locations, crops, assets] = await Promise.all([
    safeListRequest(() => Locations.list({ farm_id: farmId })),
    safeListRequest(() => Crops.list({ farm_id: farmId })),
    safeListRequest(() => Assets.list({ farm_id: farmId })),
  ])

  const tasksEntries = await Promise.all(
    crops.map(async (crop) => {
      const tasks = await safeListRequest(() => Crops.tasks(crop.id, { farm_id: farmId }))
      return [String(crop.id), tasks]
    }),
  )

  const varietiesEntries = await Promise.all(
    crops.map(async (crop) => {
      const varieties = await safeListRequest(() =>
        CropVarieties.list({ crop: crop.id, farm_id: farmId }),
      )
      return [String(crop.id), varieties]
    }),
  )

  const wellsEntries = await Promise.all(
    locations.map(async (location) => {
      const wells = await safeListRequest(() => LocationWells.list({ location_id: location.id }))
      return [String(location.id), wells]
    }),
  )

  const teamNames = await safeListRequest(() => Activities.teamSuggestions({ farm_id: farmId }))

  const context = {
    farmId: String(farmId),
    fetchedAt: new Date().toISOString(),
    crops,
    varietiesByCrop: Object.fromEntries(varietiesEntries),
    tasksByCrop: Object.fromEntries(tasksEntries),
    locations,
    assets,
    wellsByLocation: Object.fromEntries(wellsEntries),
    teamNames,
  }

  await writeCachedContext(farmId, context)
  return context
}

export async function getFarmContext(farmId, options = {}) {
  if (!farmId) {
    return null
  }
  const normalizedId = String(farmId)
  const { refresh = false, forceRefresh = false } = options
  const cached = await readCachedContext(normalizedId)
  const online = typeof navigator === 'undefined' ? true : navigator.onLine

  const shouldRefresh = forceRefresh || (refresh && online)
  const stale = cached ? isStale(cached) : true

  if (shouldRefresh || !cached) {
    try {
      if (!online && !cached && !forceRefresh) {
        throw new Error('offline-without-cache')
      }
      if (!online && stale && cached) {
        return cached
      }
      return await fetchFarmContextFromServer(normalizedId)
    } catch (error) {
      if (cached) {
        console.warn('Using cached farm context after refresh failure', error)
        return cached
      }
      throw error
    }
  }

  if (refresh && online && stale) {
    fetchFarmContextFromServer(normalizedId).catch((error) => {
      console.warn('Background refresh of farm context failed', error)
    })
  }

  return cached
}

export async function prefetchFarmContext(farmId) {
  if (!farmId) return null
  try {
    return await fetchFarmContextFromServer(String(farmId))
  } catch (error) {
    console.warn('Failed to prefetch farm context', error)
    return null
  }
}

export async function persistFarmContext(farmId, context) {
  if (!farmId || !context) {
    return
  }
  await writeCachedContext(String(farmId), context)
}

export async function clearFarmContextCache(farmId) {
  if (!farmId) return
  await del(buildContextKey(farmId))
}
