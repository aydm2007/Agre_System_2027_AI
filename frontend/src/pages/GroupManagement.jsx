import { useCallback, useEffect, useMemo, useState } from 'react'
import { Auth } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import ar from '../i18n/ar'
import { resolveDisplayName, resolveSecondaryIdentity } from '../utils/displayName'

const TEXT = ar.groupManagement
const messageTimer = 4000

const PERMISSION_PRESET_DEFINITIONS = [
  {
    key: 'مدير المزرعة',
    codenames: [
      'add_farm',
      'change_farm',
      'delete_farm',
      'view_farm',
      'add_location',
      'change_location',
      'delete_location',
      'view_location',
      'add_asset',
      'change_asset',
      'delete_asset',
      'view_asset',
      'add_supervisor',
      'change_supervisor',
      'delete_supervisor',
      'view_supervisor',
      'add_farmmembership',
      'change_farmmembership',
      'delete_farmmembership',
      'view_farmmembership',
      'add_item',
      'change_item',
      'delete_item',
      'view_item',
      'add_category',
      'change_category',
      'delete_category',
      'view_category',
      'add_crop',
      'change_crop',
      'delete_crop',
      'view_crop',
      'add_farmcrop',
      'change_farmcrop',
      'delete_farmcrop',
      'view_farmcrop',
      'add_employee',
      'change_employee',
      'delete_employee',
      'view_employee',
      'add_dailylog',
      'change_dailylog',
      'view_dailylog',
      'delete_dailylog',
      'add_activity',
      'change_activity',
      'view_activity',
      'delete_activity',
      'add_stockmovement',
      'change_stockmovement',
      'view_stockmovement',
      'add_harvestlot',
      'change_harvestlot',
      'view_harvestlot',
      'view_auditlog',
      'add_attachment',
      'change_attachment',
      'view_attachment',
      'delete_attachment',
      'view_user',
      'view_group',
      'view_permission',
    ],
  },
  {
    key: 'المهندس الزراعي',
    codenames: [
      'add_farmcrop',
      'change_farmcrop',
      'view_farmcrop',
      'add_dailylog',
      'change_dailylog',
      'view_dailylog',
      'add_activity',
      'change_activity',
      'view_activity',
      'add_harvestlot',
      'change_harvestlot',
      'view_harvestlot',
      'view_location',
      'view_asset',
      'view_item',
      'view_crop',
      'add_attachment',
      'change_attachment',
      'view_attachment',
    ],
  },
  {
    key: 'مشرف ميداني',
    codenames: [
      'add_dailylog',
      'change_dailylog',
      'view_dailylog',
      'add_activity',
      'change_activity',
      'view_activity',
      'add_attachment',
      'change_attachment',
      'view_attachment',
      'view_location',
      'view_asset',
      'view_farmcrop',
      'view_employee',
    ],
  },
  {
    key: 'فني زراعي',
    codenames: [
      'add_dailylog',
      'change_dailylog',
      'view_dailylog',
      'add_activity',
      'change_activity',
      'view_activity',
      'add_attachment',
      'change_attachment',
      'view_attachment',
      'view_location',
      'view_asset',
      'view_farmcrop',
      'view_item',
    ],
  },
  {
    key: 'مزارع',
    codenames: ['view_dailylog', 'view_activity', 'view_location', 'view_farmcrop'],
  },
  {
    key: 'أمين مخزن',
    codenames: [
      'add_stockmovement',
      'change_stockmovement',
      'view_stockmovement',
      'add_item',
      'change_item',
      'view_item',
      'add_category',
      'change_category',
      'view_category',
      'add_unit',
      'change_unit',
      'view_unit',
      'add_supplier',
      'change_supplier',
      'view_supplier',
      'add_attachment',
      'change_attachment',
      'view_attachment',
      'view_location',
      'view_farm',
    ],
  },
  {
    key: 'أمين صندوق',
    codenames: [
      'view_dailylog',
      'view_activity',
      'view_stockmovement',
      'view_harvestlot',
      'view_employee',
      'view_farm',
      'view_location',
    ],
  },
  {
    key: 'محاسب المزرعة',
    codenames: [
      'view_farm',
      'view_location',
      'view_asset',
      'view_item',
      'view_crop',
      'view_farmcrop',
      'view_dailylog',
      'view_activity',
      'view_stockmovement',
      'view_harvestlot',
      'view_employee',
      'view_auditlog',
      'view_attachment',
    ],
  },
  {
    key: 'رئيس الحسابات',
    codenames: [
      'view_farm',
      'view_location',
      'view_asset',
      'view_item',
      'view_crop',
      'view_farmcrop',
      'view_dailylog',
      'view_activity',
      'view_stockmovement',
      'view_harvestlot',
      'view_employee',
      'view_auditlog',
      'view_attachment',
      'view_group',
      'view_permission',
      'view_user',
    ],
  },
  {
    key: 'المدير المالي للمزرعة',
    codenames: [
      'view_farm','view_location','view_asset','view_item','view_crop','view_farmcrop','view_dailylog','view_activity','view_stockmovement','view_harvestlot','view_employee','view_auditlog','view_attachment','view_group','view_permission','view_user'
    ],
  },
  {
    key: 'محاسب القطاع',
    codenames: [
      'view_farm','view_location','view_asset','view_item','view_crop','view_farmcrop','view_dailylog','view_activity','view_stockmovement','view_harvestlot','view_employee','view_auditlog','view_attachment'
    ],
  },
  {
    key: 'مراجع القطاع',
    codenames: [
      'view_farm','view_location','view_asset','view_item','view_crop','view_farmcrop','view_dailylog','view_activity','view_stockmovement','view_harvestlot','view_employee','view_auditlog','view_attachment'
    ],
  },
  {
    key: 'رئيس حسابات القطاع',
    codenames: [
      'view_farm','view_location','view_asset','view_item','view_crop','view_farmcrop','view_dailylog','view_activity','view_stockmovement','view_harvestlot','view_employee','view_auditlog','view_attachment','view_group','view_permission','view_user'
    ],
  },
  {
    key: 'مدير القطاع',
    codenames: [
      'view_farm','view_location','view_asset','view_item','view_crop','view_farmcrop','view_dailylog','view_activity','view_stockmovement','view_harvestlot','view_employee','view_auditlog','view_attachment','view_group','view_permission','view_user'
    ],
  },
  {
    key: 'المدير المالي لقطاع المزارع',
    codenames: [
      'view_farm',
      'view_location',
      'view_asset',
      'view_item',
      'view_crop',
      'view_farmcrop',
      'view_dailylog',
      'view_activity',
      'view_stockmovement',
      'view_harvestlot',
      'view_employee',
      'view_auditlog',
      'view_attachment',
      'view_group',
      'view_permission',
      'view_user',
    ],
  },
  {
    key: 'مدخل بيانات',
    codenames: [
      'add_dailylog',
      'change_dailylog',
      'view_dailylog',
      'add_activity',
      'change_activity',
      'view_activity',
      'add_attachment',
      'change_attachment',
      'view_attachment',
      'add_stockmovement',
      'change_stockmovement',
      'view_stockmovement',
      'view_location',
      'view_asset',
      'view_employee',
      'view_item',
    ],
  },
  {
    key: 'مشاهد',
    codenames: [
      'view_farm',
      'view_location',
      'view_asset',
      'view_item',
      'view_crop',
      'view_farmcrop',
      'view_dailylog',
      'view_activity',
      'view_stockmovement',
      'view_harvestlot',
      'view_employee',
      'view_auditlog',
      'view_attachment',
      'view_supervisor',
      'view_farmmembership',
    ],
  },
]

export default function GroupManagement() {
  const auth = useAuth()
  const { is_superuser, canViewModel, canAddModel, canChangeModel, canDeleteModel } = auth
  const canModifyGroups = canChangeModel('group') || is_superuser

  const [groups, setGroups] = useState([])
  const [permissions, setPermissions] = useState([])
  const [users, setUsers] = useState([])
  const [selectedGroupId, setSelectedGroupId] = useState(null)
  const [groupPermissionIds, setGroupPermissionIds] = useState([])
  const [showAddGroup, setShowAddGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [bulkUpdating, setBulkUpdating] = useState(false)

  const selectedGroup = useMemo(
    () => groups.find((group) => group.id === selectedGroupId) || null,
    [groups, selectedGroupId],
  )

  const permissionMap = useMemo(() => {
    return permissions.reduce((acc, permission) => {
      acc[permission.codename] = permission
      return acc
    }, {})
  }, [permissions])

  const allPermissionIds = useMemo(
    () => permissions.map((permission) => permission.id),
    [permissions],
  )

  const resolvedPresets = useMemo(() => {
    if (!TEXT?.presets) {
      return []
    }
    return PERMISSION_PRESET_DEFINITIONS.map((preset) => {
      const meta = TEXT.presets[preset.key] || { name: preset.key, description: '' }
      const ids = preset.codenames
        .map((codename) => permissionMap[codename]?.id)
        .filter((id) => typeof id === 'number')
      return {
        key: preset.key,
        label: meta.name,
        description: meta.description,
        ids,
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [permissionMap])

  const groupMembers = useMemo(() => {
    if (!selectedGroupId) return []
    return users.filter((user) => (user.groups || []).some((group) => group.id === selectedGroupId))
  }, [users, selectedGroupId])

  const showError = useCallback((message) => {
    setError(message)
    setTimeout(() => setError(''), messageTimer)
  }, [])

  const showSuccess = useCallback((message) => {
    setSuccess(message)
    setTimeout(() => setSuccess(''), messageTimer)
  }, [])

  const loadGroups = useCallback(async () => {
    try {
      setLoading(true)
      const response = await Auth.getGroups()
      const data = response.data?.results ?? response.data ?? []
      setGroups(data)
      return data
    } catch (err) {
      console.error(TEXT.loadGroupsFailed, err)
      showError(TEXT.loadGroupsFailed)
      return []
    } finally {
      setLoading(false)
    }
  }, [showError])

  const loadPermissions = useCallback(async () => {
    try {
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
    }
  }, [showError])

  const loadUsers = useCallback(async () => {
    try {
      const response = await Auth.getUsers()
      setUsers(response.data?.results ?? response.data ?? [])
    } catch (err) {
      console.error(TEXT.loadUsersFailed, err)
      showError(TEXT.loadUsersFailed)
    }
  }, [showError])

  const loadGroupDetails = useCallback(
    async (groupId) => {
      if (!groupId) return
      try {
        const response = await Auth.getGroup(groupId)
        const permissionsResponse = response.data?.permissions ?? []
        const ids = permissionsResponse.map((id) => Number(id)).filter((id) => !Number.isNaN(id))
        setGroupPermissionIds(ids)
      } catch (err) {
        console.error(TEXT.loadGroupFailed, err)
        showError(TEXT.loadGroupFailed)
        setGroupPermissionIds([])
      }
    },
    [showError],
  )

  useEffect(() => {
    if (!canViewModel('group') && !is_superuser) {
      setLoading(false)
      setError(TEXT.noAccess)
      return
    }

    const initialise = async () => {
      setLoading(true)
      await Promise.all([loadGroups(), loadPermissions(), loadUsers()])
      setLoading(false)
    }

    initialise()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canViewModel, is_superuser, loadGroups, loadPermissions, loadUsers])

  const handleGroupSelect = async (group) => {
    setSelectedGroupId(group.id)
    await loadGroupDetails(group.id)
  }

  const bulkUpdatePermissions = useCallback(
    async (permissionIds, enabled) => {
      if (!selectedGroup || !canModifyGroups || permissionIds.length === 0) {
        return
      }
      const uniqueIds = Array.from(new Set(permissionIds.filter((id) => typeof id === 'number')))
      const currentIds = new Set(groupPermissionIds)
      const targetIds = enabled
        ? uniqueIds.filter((id) => !currentIds.has(id))
        : uniqueIds.filter((id) => currentIds.has(id))
      if (targetIds.length === 0) {
        return
      }
      try {
        setBulkUpdating(true)
        const requests = targetIds.map((id) =>
          enabled
            ? Auth.assignGroupPermission(selectedGroup.id, id)
            : Auth.removeGroupPermission(selectedGroup.id, id),
        )
        await Promise.all(requests)
        setGroupPermissionIds((prev) => {
          const next = new Set(prev)
          if (enabled) {
            targetIds.forEach((id) => next.add(id))
          } else {
            targetIds.forEach((id) => next.delete(id))
          }
          return Array.from(next)
        })
        showSuccess(TEXT.permissionUpdateSuccess)
      } catch (err) {
        console.error(TEXT.permissionUpdateFailed, err)
        showError(TEXT.permissionUpdateFailed)
      } finally {
        setBulkUpdating(false)
      }
    },
    [selectedGroup, canModifyGroups, groupPermissionIds, showError, showSuccess],
  )

  const handlePermissionToggle = async (permissionId, enabled) => {
    await bulkUpdatePermissions([permissionId], enabled)
  }

  const handlePresetToggle = async (presetKey, enabled) => {
    const preset = resolvedPresets.find((item) => item.key === presetKey)
    if (!preset) return
    await bulkUpdatePermissions(preset.ids, enabled)
  }

  const handleToggleAllPermissions = async (enabled) => {
    await bulkUpdatePermissions(allPermissionIds, enabled)
  }

  const handleGroupMembershipToggle = async (userId, enabled) => {
    if (!selectedGroup || !canModifyGroups) return

    try {
      if (enabled) {
        await Auth.addUserToGroup(userId, selectedGroup.id)
      } else {
        await Auth.removeUserFromGroup(userId, selectedGroup.id)
      }
      await loadUsers()
      showSuccess(TEXT.groupUserUpdateSuccess)
    } catch (err) {
      console.error(TEXT.groupUserUpdateFailed, err)
      showError(TEXT.groupUserUpdateFailed)
    }
  }

  const handleAddGroup = async () => {
    const trimmedName = newGroupName.trim()
    if (!trimmedName) {
      return
    }
    try {
      await Auth.createGroup({ name: trimmedName })
      showSuccess(TEXT.addGroupSuccess)
      setNewGroupName('')
      setShowAddGroup(false)
      const refreshedGroups = await loadGroups()
      const created = refreshedGroups.find((group) => group.name === trimmedName)
      if (created) {
        handleGroupSelect(created)
      }
    } catch (err) {
      console.error(TEXT.addGroupFailed, err)
      showError(TEXT.addGroupFailed)
    }
  }

  const handleDeleteGroup = async (groupId) => {
    if (!window.confirm(TEXT.deleteGroupConfirm)) {
      return
    }
    try {
      await Auth.deleteGroup(groupId)
      showSuccess(TEXT.deleteGroupSuccess)
      if (selectedGroupId === groupId) {
        setSelectedGroupId(null)
        setGroupPermissionIds([])
      }
      await loadGroups()
      await loadUsers()
    } catch (err) {
      console.error(TEXT.deleteGroupFailed, err)
      showError(TEXT.deleteGroupFailed)
    }
  }

  if (!canViewModel('group') && !is_superuser) {
    return (
      <div className="text-red-600 dark:text-red-400 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
        {TEXT.noAccess}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center gap-4 flex-wrap">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{TEXT.title}</h2>
        {(canAddModel('group') || is_superuser) && (
          <button
            type="button"
            onClick={() => setShowAddGroup((prev) => !prev)}
            className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors"
          >
            {showAddGroup ? TEXT.hideForm : TEXT.addGroupButton}
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

      {showAddGroup && (
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-4">
          <div>
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
              htmlFor="new-group-name"
            >
              {TEXT.groupName}
            </label>
            <input
              id="new-group-name"
              type="text"
              value={newGroupName}
              onChange={(event) => setNewGroupName(event.target.value)}
              className="w-full border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleAddGroup}
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            >
              {TEXT.save}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddGroup(false)
                setNewGroupName('')
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
            <h3 className="font-bold mb-3 text-gray-800 dark:text-white">{TEXT.groupsList}</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {groups.length === 0 && (
                <div className="text-sm text-gray-500 dark:text-slate-400">{TEXT.noGroupsHint}</div>
              )}
              {groups.map((group) => (
                <button
                  key={group.id}
                  type="button"
                  onClick={() => handleGroupSelect(group)}
                  className={`w-full text-start p-2 rounded border transition ${selectedGroupId === group.id ? 'bg-primary text-white border-primary' : 'hover:bg-gray-100 dark:hover:bg-slate-700 border-transparent text-gray-800 dark:text-slate-200'}`}
                >
                  {group.name}
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2">
            {selectedGroup ? (
              <div className="space-y-6">
                <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-5">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold text-gray-900 dark:text-white">
                      {TEXT.groupDetails}: {selectedGroup.name}
                    </h3>
                    {(canDeleteModel('group') || is_superuser) && (
                      <button
                        type="button"
                        onClick={() => handleDeleteGroup(selectedGroup.id)}
                        className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      >
                        {TEXT.deleteGroup}
                      </button>
                    )}
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                      {TEXT.members}
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                      {users.map((user) => {
                        const isMember = groupMembers.some((member) => member.id === user.id)
                        return (
                          <label
                            key={user.id}
                            className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300"
                          >
                            <input
                              type="checkbox"
                              className="h-4 w-4 text-primary border-gray-300 rounded"
                              checked={isMember}
                              onChange={(event) =>
                                handleGroupMembershipToggle(user.id, event.target.checked)
                              }
                              disabled={!canModifyGroups}
                            />
                            <span>
                              {resolveDisplayName(user)}
                              <span className="ms-2 text-xs text-slate-500 dark:text-slate-400">
                                {resolveSecondaryIdentity(user)}
                              </span>
                            </span>
                          </label>
                        )
                      })}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div>
                        <h4 className="font-semibold text-gray-800 dark:text-white">
                          {TEXT.permissionPresetsTitle}
                        </h4>
                        <p className="text-sm text-gray-500 dark:text-slate-400">
                          {TEXT.permissionPresetsHint}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => handleToggleAllPermissions(true)}
                          className="px-3 py-1 text-sm rounded bg-primary text-white hover:bg-primary-dark disabled:bg-gray-200 dark:disabled:bg-slate-600 disabled:text-gray-500 dark:disabled:text-slate-400"
                          disabled={!canModifyGroups || bulkUpdating || permissions.length === 0}
                        >
                          {TEXT.selectAllPermissions}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleAllPermissions(false)}
                          className="px-3 py-1 text-sm rounded bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-300 dark:hover:bg-slate-600 disabled:bg-gray-100 dark:disabled:bg-slate-800"
                          disabled={!canModifyGroups || bulkUpdating || permissions.length === 0}
                        >
                          {TEXT.clearAllPermissions}
                        </button>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {resolvedPresets.map((preset) => {
                        const isChecked =
                          preset.ids.length > 0 &&
                          preset.ids.every((id) => groupPermissionIds.includes(id))
                        const isPartial =
                          !isChecked && preset.ids.some((id) => groupPermissionIds.includes(id))
                        return (
                          <label
                            key={preset.key}
                            className="flex items-start gap-2 p-3 border dark:border-slate-600 rounded-lg bg-gray-50 dark:bg-slate-700"
                          >
                            <input
                              type="checkbox"
                              className="mt-1 h-4 w-4 text-primary border-gray-300 rounded"
                              checked={isChecked}
                              ref={(element) => {
                                if (element) {
                                  element.indeterminate = isPartial
                                }
                              }}
                              onChange={(event) =>
                                handlePresetToggle(preset.key, event.target.checked)
                              }
                              disabled={!canModifyGroups || bulkUpdating || preset.ids.length === 0}
                            />
                            <div className="space-y-1">
                              <p className="font-semibold text-sm text-gray-800 dark:text-white">
                                {preset.label}
                              </p>
                              <p className="text-xs text-gray-600 dark:text-slate-400 leading-relaxed">
                                {preset.description}
                              </p>
                            </div>
                          </label>
                        )
                      })}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                      {TEXT.permissions}
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2 max-h-80 overflow-y-auto">
                      {permissions.map((permission) => {
                        const isChecked = groupPermissionIds.includes(permission.id)
                        const label = permission.name_arabic || permission.name
                        return (
                          <label
                            key={permission.id}
                            className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300"
                          >
                            <input
                              type="checkbox"
                              className="h-4 w-4 text-primary border-gray-300 rounded"
                              checked={isChecked}
                              onChange={(event) =>
                                handlePermissionToggle(permission.id, event.target.checked)
                              }
                              disabled={!canModifyGroups || bulkUpdating}
                            />
                            <span>{label}</span>
                          </label>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border dark:border-slate-700 text-center text-gray-500 dark:text-slate-400">
                {TEXT.selectGroupHint}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
