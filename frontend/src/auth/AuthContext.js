import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Auth, Farms, api } from '../api/client'
import { setQueueOwnerId } from '../api/offlineQueueStore'
import { setAuthContext } from './contextBridge'

const AuthContext = createContext(null)

const RESTRICTED_FARM_ROLES = new Set(['مدخل بيانات', 'مشاهد'])

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

function toNumber(value) {
  if (value === null || value === undefined) {
    return null
  }
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

function normaliseFarmIds(farms) {
  return farms.map((farm) => toNumber(farm.farm_id ?? farm.id)).filter((id) => id !== null)
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [userFarms, setUserFarms] = useState([])
  const [userFarmIds, setUserFarmIds] = useState([])
  const [userPermissions, setUserPermissions] = useState([])
  const [userGroups, setUserGroups] = useState([])
  const [isAdmin, setIsAdmin] = useState(false)
  const [isSuperuser, setIsSuperuser] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [strictErpMode, setStrictErpMode] = useState(false) // Weak-network default: simplified mode

  const permissionSet = useMemo(
    () => new Set(userPermissions.map((code) => code.toLowerCase())),
    [userPermissions],
  )

  const normalisedFarmRoles = useMemo(
    () =>
      userFarms
        .map((farm) => (farm?.role ? String(farm.role).toLowerCase() : null))
        .filter(Boolean),
    [userFarms],
  )

  const farmRoleSet = useMemo(() => new Set(normalisedFarmRoles), [normalisedFarmRoles])

  const hasNonRestrictedFarmRole = useMemo(
    () => normalisedFarmRoles.some((role) => !RESTRICTED_FARM_ROLES.has(role)),
    [normalisedFarmRoles],
  )

  const isFarmRoleRestricted = useMemo(
    () => !isAdmin && !isSuperuser && normalisedFarmRoles.length > 0 && !hasNonRestrictedFarmRole,
    [hasNonRestrictedFarmRole, isAdmin, isSuperuser, normalisedFarmRoles],
  )

  const clearState = useCallback(() => {
    setUser(null)
    setUserFarms([])
    setUserFarmIds([])
    setUserPermissions([])
    setUserGroups([])
    setIsAdmin(false)
    setIsSuperuser(false)
    setIsAuthenticated(false)
  }, [])

  const applyProfile = useCallback(
    (profile) => {
      if (!profile) {
        clearState()
        return
      }

      const {
        user: profileUser,
        farms = [],
        permissions = [],
        groups = [],
        is_admin,
        is_superuser,
      } = profile

      setUser(profileUser || null)
      setUserFarms(farms)
      setUserFarmIds(normaliseFarmIds(farms))
      setUserPermissions(Array.isArray(permissions) ? permissions : [])
      setUserGroups(groups)
      setIsAdmin(Boolean(is_admin))
      setIsSuperuser(Boolean(is_superuser))
      setIsAuthenticated(Boolean(profileUser))
    },
    [clearState],
  )

  const fetchProfile = useCallback(async () => {
    try {
      const response = await Auth.getCurrentUser()
      applyProfile(response.data)
      return response.data
    } catch (error) {
      console.error('Failed to load user profile:', error)
      clearState()
      return null
    }
  }, [applyProfile, clearState])

  const fetchSystemMode = useCallback(async (farmId = null) => {
    try {
      const query = farmId ? `?farm=${farmId}` : ''
      const { data } = await api.get(`/system-mode/${query}`)
      setStrictErpMode(Boolean(data.strict_erp_mode))
    } catch (err) {
      console.warn('Failed to fetch system mode, defaulting to simplified mode:', err)
      setStrictErpMode(false)
    }
  }, [])

  const setStrictErpModeValue = useCallback((value) => {
    setStrictErpMode(Boolean(value))
  }, [])

  const bootstrap = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = Auth.getToken()
      if (!token) {
        clearState()
        return
      }
      const profile = await fetchProfile()
      const initialFarmId = profile?.farms?.[0]?.farm_id ?? profile?.farms?.[0]?.id ?? null
      await fetchSystemMode(initialFarmId)
    } finally {
      setIsLoading(false)
    }
  }, [clearState, fetchProfile, fetchSystemMode])

  // Sync with client
  useEffect(() => {
    try {
      setQueueOwnerId(user?.id ?? null)
    } catch (e) {
      console.error('Failed to sync queue owner', e)
    }
  }, [user])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  const login = useCallback(
    async (username, password) => {
      setIsLoading(true)
      try {
        const { data } = await Auth.login(username, password)
        Auth.setTokens(data.access, data.refresh)
        await fetchProfile()
        return true
      } finally {
        setIsLoading(false)
      }
    },
    [fetchProfile],
  )

  const logout = useCallback(() => {
    Auth.logout()
    clearState()
  }, [clearState])

  const refreshFarms = useCallback(
    async (forceRefresh = false) => {
      if (!forceRefresh && userFarms.length > 0) {
        return userFarms
      }

      try {
        const { data } = await Farms.list()
        const farms = data.results || data || []
        setUserFarms(farms)
        setUserFarmIds(normaliseFarmIds(farms))
        return farms
      } catch (error) {
        console.error('Error fetching user farms:', error)
        setUserFarms([])
        setUserFarmIds([])
        return []
      }
    },
    [userFarms],
  )

  const refreshProfile = useCallback(async () => {
    await fetchProfile()
  }, [fetchProfile])

  const hasFarmAccess = useCallback(
    (farmId) => {
      if (!farmId) {
        return false
      }
      if (isAdmin || isSuperuser) {
        return true
      }
      const numericId = toNumber(farmId)
      if (numericId === null) {
        return false
      }
      return (
        userFarmIds.includes(numericId) ||
        userFarmIds.includes(Number.parseInt(String(numericId), 10))
      )
    },
    [isAdmin, isSuperuser, userFarmIds],
  )

  const hasPermission = useCallback(
    (permissionCodename) => {
      if (!permissionCodename) {
        return false
      }
      if (isSuperuser) {
        return true
      }
      return permissionSet.has(permissionCodename.toLowerCase())
    },
    [isSuperuser, permissionSet],
  )

  const canAddModel = useCallback(
    (modelName) => hasPermission(`add_${modelName.toLowerCase()}`),
    [hasPermission],
  )
  const canChangeModel = useCallback(
    (modelName) => hasPermission(`change_${modelName.toLowerCase()}`),
    [hasPermission],
  )
  const canDeleteModel = useCallback(
    (modelName) => hasPermission(`delete_${modelName.toLowerCase()}`),
    [hasPermission],
  )
  const canViewModel = useCallback(
    (modelName) => hasPermission(`view_${modelName.toLowerCase()}`),
    [hasPermission],
  )
  const hasFarmRole = useCallback(
    (roleName) => {
      if (!roleName) {
        return false
      }
      return farmRoleSet.has(String(roleName).toLowerCase())
    },
    [farmRoleSet],
  )

  const contextValue = useMemo(
    () => ({
      user,
      userFarms,
      userFarmIds,
      userPermissions,
      userGroups,
      isAdmin,
      is_superuser: isSuperuser,
      isSuperuser,
      isAuthenticated,
      isLoading,
      strictErpMode,
      setStrictErpModeValue,
      refreshSystemMode: fetchSystemMode,
      login,
      logout,
      refreshFarms,
      refreshProfile,
      hasFarmAccess,
      hasPermission,
      hasFarmRole,
      isFarmRoleRestricted,
      canAddModel,
      canChangeModel,
      canDeleteModel,
      canViewModel,
    }),
    [
      canAddModel,
      canChangeModel,
      canDeleteModel,
      canViewModel,
      hasFarmRole,
      hasFarmAccess,
      hasPermission,
      isAdmin,
      isAuthenticated,
      isLoading,
      isSuperuser,
      isFarmRoleRestricted,
      strictErpMode,
      setStrictErpModeValue,
      login,
      logout,
      refreshFarms,
      refreshProfile,
      fetchSystemMode,
      user,
      userFarms,
      userFarmIds,
      userGroups,
      userPermissions,
    ],
  )

  setAuthContext(contextValue)

  return React.createElement(AuthContext.Provider, { value: contextValue }, children)
}

export default AuthContext
