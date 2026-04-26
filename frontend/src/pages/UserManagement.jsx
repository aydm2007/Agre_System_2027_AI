import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Auth } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import ar from '../i18n/ar'
import { resolveDisplayName, resolveSecondaryIdentity } from '../utils/displayName'

const TEXT = ar.userManagement
const INITIAL_NEW_USER = {
  username: '',
  password: '',
  email: '',
  first_name: '',
  last_name: '',
  is_staff: false,
  is_superuser: false,
}

const messageTimer = 4000

export default function UserManagement() {
  const auth = useAuth()
  const { is_superuser, canViewModel, canAddModel, canChangeModel, canDeleteModel, hasFarmRole } =
    auth

  const [users, setUsers] = useState([])
  const [permissions, setPermissions] = useState([])
  const [groups, setGroups] = useState([])
  const [permissionsLoading, setPermissionsLoading] = useState(false)
  const [groupsLoading, setGroupsLoading] = useState(false)
  const [pendingPermissionIds, setPendingPermissionIds] = useState([])
  const [pendingGroupIds, setPendingGroupIds] = useState([])
  const [bulkPermissionsLoading, setBulkPermissionsLoading] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [userPermissionIds, setUserPermissionIds] = useState([])
  const [userGroupIds, setUserGroupIds] = useState([])
  const [newUser, setNewUser] = useState(INITIAL_NEW_USER)
  const [showAddUser, setShowAddUser] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const selectAllPermissionsRef = useRef(null)

  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) || null,
    [users, selectedUserId],
  )

  const permissionIds = useMemo(
    () => permissions.map((permission) => Number(permission.id)),
    [permissions],
  )
  const permissionLabelByCode = useMemo(
    () =>
      permissions.reduce((acc, permission) => {
        if (permission?.codename) {
          acc[permission.codename] = permission.name_arabic || permission.name || permission.codename
        }
        return acc
      }, {}),
    [permissions],
  )

  const pendingPermissionIdSet = useMemo(
    () => new Set(pendingPermissionIds),
    [pendingPermissionIds],
  )
  const pendingGroupIdSet = useMemo(() => new Set(pendingGroupIds), [pendingGroupIds])

  const canManagePermissions = canChangeModel('user') || is_superuser || hasFarmRole('Admin')
  const canManageSuperuser = useMemo(
    () => is_superuser || hasFarmRole('Admin'),
    [hasFarmRole, is_superuser],
  )

  const allPermissionsSelected = useMemo(
    () => permissionIds.length > 0 && permissionIds.every((id) => userPermissionIds.includes(id)),
    [permissionIds, userPermissionIds],
  )

  const somePermissionsSelected = useMemo(
    () => !allPermissionsSelected && permissionIds.some((id) => userPermissionIds.includes(id)),
    [allPermissionsSelected, permissionIds, userPermissionIds],
  )

  useEffect(() => {
    if (!selectAllPermissionsRef.current) return
    selectAllPermissionsRef.current.indeterminate = somePermissionsSelected
  }, [somePermissionsSelected])

  const addPendingPermission = useCallback((permissionId) => {
    setPendingPermissionIds((prev) =>
      prev.includes(permissionId) ? prev : [...prev, permissionId],
    )
  }, [])

  const removePendingPermission = useCallback((permissionId) => {
    setPendingPermissionIds((prev) => prev.filter((id) => id !== permissionId))
  }, [])

  const addPendingGroup = useCallback((groupId) => {
    setPendingGroupIds((prev) => (prev.includes(groupId) ? prev : [...prev, groupId]))
  }, [])

  const removePendingGroup = useCallback((groupId) => {
    setPendingGroupIds((prev) => prev.filter((id) => id !== groupId))
  }, [])

  const showError = useCallback((message) => {
    setError(message)
    setTimeout(() => setError(''), messageTimer)
  }, [])

  const showSuccess = useCallback((message) => {
    setSuccess(message)
    setTimeout(() => setSuccess(''), messageTimer)
  }, [])

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true)
      const response = await Auth.getUsers()
      const data = response.data?.results ?? response.data ?? []
      setUsers(data)
      return data
    } catch (err) {
      console.error(TEXT.loadUsersFailed, err)
      showError(TEXT.loadUsersFailed)
      return []
    } finally {
      setLoading(false)
    }
  }, [showError])

  const loadPermissions = useCallback(async () => {
    try {
      setPermissionsLoading(true)
      const response = await Auth.getPermissions()
      const data = response.data?.results ?? response.data ?? []
      const normalised = data.map((permission) => ({
        ...permission,
        displayName: permission.name_arabic || permission.name,
      }))
      normalised.sort((a, b) =>
        a.displayName.localeCompare(b.displayName, 'ar', { sensitivity: 'base' }),
      )
      setPermissions(normalised)
    } catch (err) {
      console.error(TEXT.loadPermissionsFailed, err)
      showError(TEXT.loadPermissionsFailed)
    } finally {
      setPermissionsLoading(false)
    }
  }, [showError])

  const loadGroups = useCallback(async () => {
    try {
      setGroupsLoading(true)
      const response = await Auth.getGroups()
      setGroups(response.data?.results ?? response.data ?? [])
    } catch (err) {
      console.error(TEXT.loadGroupsFailed, err)
      showError(TEXT.loadGroupsFailed)
    } finally {
      setGroupsLoading(false)
    }
  }, [showError])

  const loadUserPermissions = useCallback(
    async (userId) => {
      try {
        const response = await Auth.getUserPermissions(userId)
        const data = response.data?.permissions ?? []
        setUserPermissionIds(data.map((permission) => Number(permission.id)))
      } catch (err) {
        console.error(TEXT.loadUserPermissionsFailed, err)
        showError(TEXT.loadUserPermissionsFailed)
        setUserPermissionIds([])
      }
    },
    [showError],
  )

  const loadUserGroups = useCallback(
    async (userId) => {
      try {
        const response = await Auth.getUserGroups(userId)
        const data = response.data?.groups ?? []
        setUserGroupIds(data.map((group) => Number(group.id)))
      } catch (err) {
        console.error(TEXT.loadUserGroupsFailed, err)
        showError(TEXT.loadUserGroupsFailed)
        setUserGroupIds([])
      }
    },
    [showError],
  )

  useEffect(() => {
    if (!canViewModel('user') && !is_superuser) {
      setLoading(false)
      setError(TEXT.noAccess)
      return
    }

    const initialise = async () => {
      setLoading(true)
      await Promise.all([loadUsers(), loadPermissions(), loadGroups()])
      setLoading(false)
    }

    initialise()
  }, [canViewModel, is_superuser, loadUsers, loadPermissions, loadGroups, showError])

  useEffect(() => {
    if (!canManageSuperuser) {
      setNewUser((prev) => (prev.is_superuser ? { ...prev, is_superuser: false } : prev))
    }
  }, [canManageSuperuser])

  const handleSelectUser = async (userId) => {
    setSelectedUserId(userId)
    setPendingPermissionIds([])
    setPendingGroupIds([])
    setBulkPermissionsLoading(false)
    if (userId) {
      await Promise.all([loadUserPermissions(userId), loadUserGroups(userId)])
    }
  }

  const handlePermissionToggle = async (permissionId, enabled) => {
    if (!selectedUser || bulkPermissionsLoading || pendingPermissionIdSet.has(permissionId)) return

    addPendingPermission(permissionId)

    try {
      if (enabled) {
        const resp = await Auth.assignPermission(selectedUser.id, permissionId)
        // [AGRI-GUARDIAN Axis 6] Handle strict-mode warning from backend
        if (resp.data?.strict_mode_warning) {
          const ok = window.confirm(
            `⚠️ تنبيه المود الصارم\n\n${resp.data.message}\n\nهل تريد المتابعة؟`,
          )
          if (!ok) {
            removePendingPermission(permissionId)
            return
          }
          // Re-send with confirmed=true
          await Auth.assignPermission(selectedUser.id, permissionId, true)
        }
        setUserPermissionIds((prev) => [...new Set([...prev, permissionId])])
      } else {
        await Auth.removePermission(selectedUser.id, permissionId)
        setUserPermissionIds((prev) => prev.filter((id) => id !== permissionId))
      }
      showSuccess(TEXT.permissionUpdateSuccess)
    } catch (err) {
      console.error(TEXT.permissionUpdateFailed, err)
      showError(TEXT.permissionUpdateFailed)
    } finally {
      removePendingPermission(permissionId)
    }
  }

  const handleToggleAllPermissions = useCallback(
    async (enabled) => {
      if (!selectedUser || !canManagePermissions || bulkPermissionsLoading) return

      const availableIds = permissions.map((permission) => Number(permission.id))

      if (availableIds.length === 0) return

      setBulkPermissionsLoading(true)
      setPendingPermissionIds((prev) => Array.from(new Set([...prev, ...availableIds])))

      try {
        if (enabled) {
          const missingIds = availableIds.filter((id) => !userPermissionIds.includes(id))
          if (missingIds.length > 0) {
            await Promise.all(missingIds.map((id) => Auth.assignPermission(selectedUser.id, id)))
          }
          setUserPermissionIds((prev) =>
            Array.from(
              new Set([...prev.filter((id) => !availableIds.includes(id)), ...availableIds]),
            ),
          )
        } else {
          const assignedIds = userPermissionIds.filter((id) => availableIds.includes(id))
          if (assignedIds.length > 0) {
            await Promise.all(assignedIds.map((id) => Auth.removePermission(selectedUser.id, id)))
          }
          setUserPermissionIds((prev) => prev.filter((id) => !availableIds.includes(id)))
        }
        showSuccess(TEXT.permissionUpdateSuccess)
      } catch (err) {
        console.error(TEXT.permissionUpdateFailed, err)
        showError(TEXT.permissionUpdateFailed)
      } finally {
        setPendingPermissionIds((prev) => prev.filter((id) => !availableIds.includes(id)))
        setBulkPermissionsLoading(false)
      }
    },
    [
      bulkPermissionsLoading,
      canManagePermissions,
      permissions,
      selectedUser,
      showError,
      showSuccess,
      userPermissionIds,
    ],
  )

  const handleGroupToggle = async (groupId, enabled) => {
    if (!selectedUser || pendingGroupIdSet.has(groupId)) return

    addPendingGroup(groupId)

    try {
      if (enabled) {
        const resp = await Auth.addUserToGroup(selectedUser.id, groupId)
        // [AGRI-GUARDIAN Axis 6] Handle strict-mode warning from backend
        if (resp.data?.strict_mode_warning) {
          const strictLabels = (resp.data.strict_permissions || []).map(
            (code) => permissionLabelByCode[code] || code,
          )
          const ok = window.confirm(
            `⚠️ تنبيه المود الصارم\n\n${resp.data.message}\n\nالصلاحيات: ${strictLabels.join('، ')}\n\nهل تريد المتابعة؟`,
          )
          if (!ok) {
            removePendingGroup(groupId)
            return
          }
          await Auth.addUserToGroup(selectedUser.id, groupId, true)
        }
        setUserGroupIds((prev) => [...new Set([...prev, groupId])])
      } else {
        await Auth.removeUserFromGroup(selectedUser.id, groupId)
        setUserGroupIds((prev) => prev.filter((id) => id !== groupId))
      }
      showSuccess(TEXT.groupUpdateSuccess)
    } catch (err) {
      console.error(TEXT.groupUpdateFailed, err)
      showError(TEXT.groupUpdateFailed)
    } finally {
      removePendingGroup(groupId)
    }
  }

  const handleAddUser = async () => {
    if (!newUser.username.trim() || !newUser.password.trim()) {
      showError(TEXT.addUserMissingData)
      return
    }

    try {
      const trimmed = newUser.username.trim()
      const payload = {
        ...newUser,
        username: trimmed,
        is_superuser: canManageSuperuser ? newUser.is_superuser : false,
      }
      await Auth.createUser(payload)
      showSuccess(TEXT.addUserSuccess)
      setNewUser(INITIAL_NEW_USER)
      setShowAddUser(false)
      const refreshedUsers = await loadUsers()
      const created = refreshedUsers.find((u) => u.username === trimmed)
      if (created) {
        handleSelectUser(created.id)
      }
    } catch (err) {
      console.error(TEXT.addUserFailed, err)
      showError(TEXT.addUserFailed)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!window.confirm(TEXT.deleteUserConfirm)) {
      return
    }

    try {
      await Auth.deleteUser(userId)
      showSuccess(TEXT.deleteUserSuccess)
      if (selectedUserId === userId) {
        setSelectedUserId(null)
        setUserPermissionIds([])
        setUserGroupIds([])
      }
      loadUsers()
    } catch (err) {
      console.error(TEXT.deleteUserFailed, err)
      showError(TEXT.deleteUserFailed)
    }
  }

  const handleToggleSuperuser = async (userId, enabled) => {
    if (!canManageSuperuser) {
      showError(TEXT.noAccess)
      return
    }
    try {
      await Auth.updateUser(userId, { is_superuser: enabled })
      showSuccess(TEXT.toggleSuperuserSuccess)
      const refreshedUsers = await loadUsers()
      const refreshedSelected = refreshedUsers.find((u) => u.id === selectedUserId)
      if (!refreshedSelected) {
        setSelectedUserId(null)
      }
    } catch (err) {
      console.error(TEXT.toggleSuperuserFailed, err)
      showError(TEXT.toggleSuperuserFailed)
    }
  }

  if (!canViewModel('user') && !is_superuser) {
    return (
      <div className="text-red-600 dark:text-red-400 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
        {TEXT.noAccess}
      </div>
    )
  }

  return (
    <div data-testid="user-management-page" className="space-y-6">
      <div className="flex justify-between items-center gap-4 flex-wrap">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{TEXT.title}</h2>
        {(canAddModel('user') || is_superuser) && (
          <button
            type="button"
            onClick={() => setShowAddUser((prev) => !prev)}
            className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors"
          >
            {showAddUser ? TEXT.hideForm : TEXT.addUserButton}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 p-3 rounded">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 p-3 rounded">
          {success}
        </div>
      )}

      {showAddUser && (
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                htmlFor="new-username"
              >
                {TEXT.username}
              </label>
              <input
                id="new-username"
                type="text"
                value={newUser.username}
                onChange={(event) =>
                  setNewUser((prev) => ({ ...prev, username: event.target.value }))
                }
                className="w-full border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
              />
            </div>
            <div>
              <label
                className="block text-sm font-medium text-gray-700 mb-1"
                htmlFor="new-password"
              >
                {TEXT.password}
              </label>
              <input
                id="new-password"
                type="password"
                value={newUser.password}
                onChange={(event) =>
                  setNewUser((prev) => ({ ...prev, password: event.target.value }))
                }
                className="w-full border rounded p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="new-email">
                {TEXT.email}
              </label>
              <input
                id="new-email"
                type="email"
                value={newUser.email}
                onChange={(event) => setNewUser((prev) => ({ ...prev, email: event.target.value }))}
                className="w-full border rounded p-2"
              />
            </div>
            <div>
              <label
                className="block text-sm font-medium text-gray-700 mb-1"
                htmlFor="new-first-name"
              >
                {TEXT.firstName}
              </label>
              <input
                id="new-first-name"
                type="text"
                value={newUser.first_name}
                onChange={(event) =>
                  setNewUser((prev) => ({ ...prev, first_name: event.target.value }))
                }
                className="w-full border rounded p-2"
              />
            </div>
            <div>
              <label
                className="block text-sm font-medium text-gray-700 mb-1"
                htmlFor="new-last-name"
              >
                {TEXT.lastName}
              </label>
              <input
                id="new-last-name"
                type="text"
                value={newUser.last_name}
                onChange={(event) =>
                  setNewUser((prev) => ({ ...prev, last_name: event.target.value }))
                }
                className="w-full border rounded p-2"
              />
            </div>
            {canManageSuperuser && (
              <div className="flex items-center space-x-2 space-x-reverse">
                <input
                  id="new-superuser"
                  type="checkbox"
                  checked={newUser.is_superuser}
                  onChange={(event) =>
                    setNewUser((prev) => ({ ...prev, is_superuser: event.target.checked }))
                  }
                  className="h-4 w-4 text-primary border-gray-300 rounded"
                />
                <label htmlFor="new-superuser" className="text-sm font-medium text-gray-700">
                  {TEXT.isSuperuser}
                </label>
              </div>
            )}
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={handleAddUser}
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            >
              {TEXT.save}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddUser(false)
                setNewUser(INITIAL_NEW_USER)
              }}
              className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded hover:bg-gray-300 dark:hover:bg-slate-600"
            >
              {TEXT.cancel}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border dark:border-slate-700 text-center text-gray-600 dark:text-slate-400">
          {TEXT.loading}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700">
            <h3 className="font-bold mb-3 text-gray-800 dark:text-white">{TEXT.usersList}</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {users.length === 0 && (
                <div className="text-sm text-gray-500 dark:text-slate-400">{TEXT.noUsersHint}</div>
              )}
              {users.map((user) => (
                <button
                  key={user.id}
                  data-testid={`user-entry-${user.id}`}
                  type="button"
                  onClick={() => handleSelectUser(user.id)}
                  className={`w-full text-start p-2 rounded border transition ${selectedUserId === user.id ? 'bg-primary text-white border-primary' : 'hover:bg-gray-100 dark:hover:bg-slate-700 border-transparent text-gray-800 dark:text-slate-200'}`}
                >
                  <div className="font-semibold flex items-center justify-between">
                    <span>
                      {resolveDisplayName(user)}
                    </span>
                    {user.is_superuser && (
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full">
                        {TEXT.superuserBadge}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-slate-400">
                    {resolveSecondaryIdentity(user)}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {selectedUser ? (
              <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white">
                      <span data-testid="selected-user-heading">
                      {TEXT.userDetails}: {resolveDisplayName(selectedUser)}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-slate-400">
                      {resolveSecondaryIdentity(selectedUser)}
                      {selectedUser.email ? ` - ${selectedUser.email}` : ''}
                    </p>
                  </div>
                  {canManageSuperuser && (
                    <button
                      type="button"
                      onClick={() =>
                        handleToggleSuperuser(selectedUser.id, !selectedUser.is_superuser)
                      }
                      className={`px-3 py-1 rounded ${selectedUser.is_superuser ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                    >
                      {selectedUser.is_superuser ? TEXT.revokeSuperuser : TEXT.grantSuperuser}
                    </button>
                  )}
                </div>

                {(canDeleteModel('user') || is_superuser) && (
                  <button
                    type="button"
                    onClick={() => handleDeleteUser(selectedUser.id)}
                    className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    {TEXT.deleteUser}
                  </button>
                )}

                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">{TEXT.groups}</h4>
                  {groupsLoading ? (
                    <div className="text-sm text-gray-500">{TEXT.loading}</div>
                  ) : groups.length === 0 ? (
                    <div className="text-sm text-gray-500">{TEXT.groupsEmpty}</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {groups.map((group) => (
                        <label
                          key={group.id}
                          className="flex items-center gap-2 text-sm text-gray-700"
                        >
                          <input
                            type="checkbox"
                            className="h-4 w-4 text-primary border-gray-300 rounded"
                            checked={userGroupIds.includes(group.id)}
                            onChange={(event) => handleGroupToggle(group.id, event.target.checked)}
                            disabled={
                              !canManagePermissions ||
                              !selectedUser ||
                              pendingGroupIdSet.has(group.id)
                            }
                          />
                          {group.name}
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-800">{TEXT.permissions}</h4>
                    {permissions.length > 0 && (
                      <label className="flex items-center gap-2 text-sm text-gray-700">
                        <input
                          ref={selectAllPermissionsRef}
                          type="checkbox"
                          className="h-4 w-4 text-primary border-gray-300 rounded"
                          checked={allPermissionsSelected}
                          onChange={(event) => handleToggleAllPermissions(event.target.checked)}
                          disabled={
                            !canManagePermissions ||
                            !selectedUser ||
                            permissionsLoading ||
                            bulkPermissionsLoading
                          }
                        />
                        <span>
                          {allPermissionsSelected
                            ? TEXT.deselectAllPermissions
                            : TEXT.selectAllPermissions}
                        </span>
                      </label>
                    )}
                  </div>
                  {permissionsLoading ? (
                    <div className="text-sm text-gray-500">{TEXT.loading}</div>
                  ) : permissions.length === 0 ? (
                    <div className="text-sm text-gray-500">{TEXT.permissionsEmpty}</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2 max-h-80 overflow-y-auto">
                      {/* General Permissions */}
                      {permissions.filter((p) => !p.is_strict).length > 0 && (
                        <div className="col-span-full text-xs font-semibold text-gray-500 dark:text-slate-400 mt-1 mb-0.5">
                          📋 صلاحيات عامة
                        </div>
                      )}
                      {permissions
                        .filter((p) => !p.is_strict)
                        .map((permission) => (
                          <label
                            key={permission.id}
                            className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300"
                          >
                            <input
                              type="checkbox"
                              className="h-4 w-4 text-primary border-gray-300 rounded"
                              checked={userPermissionIds.includes(permission.id)}
                              onChange={(event) =>
                                handlePermissionToggle(permission.id, event.target.checked)
                              }
                              disabled={
                                !canManagePermissions ||
                                !selectedUser ||
                                pendingPermissionIdSet.has(permission.id) ||
                                bulkPermissionsLoading
                              }
                            />
                            <span>{permission.name_arabic || permission.name}</span>
                          </label>
                        ))}
                      {/* Strict Mode Permissions */}
                      {permissions.filter((p) => p.is_strict).length > 0 && (
                        <div className="col-span-full text-xs font-semibold text-amber-600 dark:text-amber-400 mt-3 mb-0.5 flex items-center gap-1">
                          🔒 صلاحيات المود الصارم (الإدارة المالية)
                        </div>
                      )}
                      {permissions
                        .filter((p) => p.is_strict)
                        .map((permission) => (
                          <label
                            key={permission.id}
                            className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 rounded px-1.5 py-0.5"
                          >
                            <input
                              type="checkbox"
                              className="h-4 w-4 text-amber-600 border-amber-300 rounded"
                              checked={userPermissionIds.includes(permission.id)}
                              onChange={(event) =>
                                handlePermissionToggle(permission.id, event.target.checked)
                              }
                              disabled={
                                !canManagePermissions ||
                                !selectedUser ||
                                pendingPermissionIdSet.has(permission.id) ||
                                bulkPermissionsLoading
                              }
                            />
                            <span>🔒 {permission.name_arabic || permission.name}</span>
                          </label>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border dark:border-slate-700 text-center text-gray-500 dark:text-slate-400">
                {TEXT.selectUserHint}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
