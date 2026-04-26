import { useCallback, useEffect, useMemo, useState } from 'react'
import { Memberships } from '../../api/client'
import FeedbackRegion from '../../components/FeedbackRegion'
import useFeedback from '../../hooks/useFeedback'
import ar from '../../i18n/ar'
import { resolveDisplayName, resolveSecondaryIdentity } from '../../utils/displayName'

const TEXT = ar.settings

export default function MembershipsTab({ hasFarms, selectedFarmId, selectedFarmName }) {
  const [roles, setRoles] = useState([])
  const [members, setMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [canManageMembers, setCanManageMembers] = useState(false)
  const [memberSearchTerm, setMemberSearchTerm] = useState('')
  const [memberOptions, setMemberOptions] = useState([])
  const [selectedOptionId, setSelectedOptionId] = useState('')
  const [newMemberRole, setNewMemberRole] = useState('')

  const { message, error, showMessage, showError } = useFeedback()

  const hasMemberOptions = useMemo(() => memberOptions.length > 0, [memberOptions.length])

  const loadRoles = useCallback(async () => {
    try {
      const response = await Memberships.roles()
      const data = response.data?.results ?? response.data ?? []
      setRoles(data)
      if (data.length > 0) {
        setNewMemberRole((prev) => prev || data[0].value)
      }
    } catch (err) {
      console.error('Failed to load roles', err)
      showError(TEXT.rolesError)
    }
  }, [showError])

  const loadMembers = useCallback(
    async (farmId) => {
      if (!farmId) {
        setMembers([])
        setCanManageMembers(false)
        return
      }
      setMembersLoading(true)
      try {
        const response = await Memberships.list({ farm: farmId })
        const payload = response.data || {}
        const results = payload.results ?? payload
        setMembers(Array.isArray(results) ? results : [])
        setCanManageMembers(Boolean(payload.meta?.can_manage))
      } catch (err) {
        console.error('Failed to load members', err)
        showError(TEXT.membersError)
        setMembers([])
        setCanManageMembers(false)
      } finally {
        setMembersLoading(false)
      }
    },
    [showError],
  )

  useEffect(() => {
    loadRoles()
  }, [loadRoles])

  useEffect(() => {
    setMemberOptions([])
    setSelectedOptionId('')
    setMemberSearchTerm('')
    loadMembers(selectedFarmId)
  }, [loadMembers, selectedFarmId])

  const handleSearchMembers = useCallback(async () => {
    const term = memberSearchTerm.trim()
    if (!term) {
      setMemberOptions([])
      setSelectedOptionId('')
      return
    }
    try {
      const response = await Memberships.available({ farm: selectedFarmId, q: term })
      const data = response.data?.results ?? response.data ?? []
      const safeOptions = Array.isArray(data) ? data : []
      setMemberOptions(safeOptions)
      if (safeOptions.length > 0) {
        setSelectedOptionId(String(safeOptions[0].id))
      } else {
        showError(TEXT.noSearchResults)
      }
    } catch (err) {
      console.error('Failed to search users', err)
      showError(TEXT.searchError)
    }
  }, [memberSearchTerm, selectedFarmId, showError])

  const handleAddMember = useCallback(async () => {
    if (!selectedOptionId || !newMemberRole) {
      showError(TEXT.addMemberError)
      return
    }
    try {
      await Memberships.create({
        farm: selectedFarmId,
        user: selectedOptionId,
        role: newMemberRole,
      })
      showMessage(TEXT.memberAdded)
      setMemberSearchTerm('')
      setMemberOptions([])
      setSelectedOptionId('')
      loadMembers(selectedFarmId)
    } catch (err) {
      console.error('Failed to add member', err)
      showError(TEXT.addMemberError)
    }
  }, [loadMembers, newMemberRole, selectedFarmId, selectedOptionId, showError, showMessage])

  const handleRoleChange = useCallback(
    async (memberId, role) => {
      try {
        await Memberships.update(memberId, { role })
        showMessage(TEXT.roleUpdated)
        setMembers((prev) =>
          prev.map((member) => (member.id === memberId ? { ...member, role } : member)),
        )
      } catch (err) {
        console.error('Failed to update member role', err)
        showError(TEXT.roleUpdateError)
      }
    },
    [showError, showMessage],
  )

  const handleRemoveMember = useCallback(
    async (memberId) => {
      if (!window.confirm(TEXT.confirmRemoveMember)) {
        return
      }
      try {
        await Memberships.remove(memberId)
        showMessage(TEXT.memberRemoved)
        setMembers((prev) => prev.filter((member) => member.id !== memberId))
      } catch (err) {
        console.error('Failed to remove member', err)
        showError(TEXT.removeMemberError)
      }
    },
    [showError, showMessage],
  )

  const handleClearSearch = useCallback(() => {
    setMemberSearchTerm('')
    setMemberOptions([])
    setSelectedOptionId('')
  }, [])

  const handleRefresh = useCallback(() => {
    loadMembers(selectedFarmId)
  }, [loadMembers, selectedFarmId])

  return (
    <section className="space-y-4" key="memberships">
      <FeedbackRegion error={error} message={message} />

      {!hasFarms ? (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border dark:border-slate-700 text-center text-gray-600 dark:text-slate-400">
          {TEXT.noFarms}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-3">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-slate-200">
                  {TEXT.selectFarmLabel}
                </p>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  {selectedFarmName || TEXT.fallback}
                </p>
              </div>
              <button
                type="button"
                onClick={handleRefresh}
                className="px-3 py-2 text-sm bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded shadow-sm hover:bg-gray-50 dark:hover:bg-slate-600 dark:text-white"
                disabled={!selectedFarmId}
              >
                {TEXT.refreshButton}
              </button>
            </div>

            <div className="flex flex-col gap-3 md:flex-row md:items-end">
              <div className="flex-1">
                <label
                  className="block text-sm font-medium text-gray-700 dark:text-slate-200"
                  htmlFor="member-search"
                >
                  {TEXT.searchPlaceholder}
                </label>
                <div className="mt-1 flex gap-2">
                  <input
                    id="member-search"
                    type="text"
                    value={memberSearchTerm}
                    onChange={(event) => setMemberSearchTerm(event.target.value)}
                    placeholder={TEXT.searchPlaceholder}
                    className="flex-1 border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
                    disabled={!selectedFarmId || !canManageMembers}
                  />
                  <button
                    type="button"
                    onClick={handleSearchMembers}
                    className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
                    disabled={!selectedFarmId || !canManageMembers}
                  >
                    {TEXT.searchButton}
                  </button>
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded hover:bg-gray-300 dark:hover:bg-slate-600"
                    disabled={!selectedFarmId || !canManageMembers || !hasMemberOptions}
                  >
                    {TEXT.clearButton}
                  </button>
                </div>
              </div>
              <div className="flex-1">
                <label
                  className="block text-sm font-medium text-gray-700 dark:text-slate-200"
                  htmlFor="member-select"
                >
                  {TEXT.addMember}
                </label>
                <select
                  id="member-select"
                  value={selectedOptionId}
                  onChange={(event) => setSelectedOptionId(event.target.value)}
                  className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
                  disabled={!canManageMembers || !selectedFarmId || memberOptions.length === 0}
                >
                  <option value="">?</option>
                  {memberOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {resolveDisplayName(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label
                  className="block text-sm font-medium text-gray-700 dark:text-slate-200"
                  htmlFor="member-role"
                >
                  {TEXT.columnRole}
                </label>
                <select
                  id="member-role"
                  value={newMemberRole}
                  onChange={(event) => setNewMemberRole(event.target.value)}
                  className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
                  disabled={!canManageMembers || !selectedFarmId || roles.length === 0}
                >
                  {roles.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="md:self-end">
                <button
                  type="button"
                  onClick={handleAddMember}
                  className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark disabled:opacity-60"
                  disabled={!canManageMembers || !selectedFarmId}
                >
                  {TEXT.addMember}
                </button>
              </div>
            </div>
            {!canManageMembers && selectedFarmId && (
              <div className="text-sm text-gray-500 dark:text-slate-400">
                {TEXT.cannotManageFarm}
              </div>
            )}
          </div>

          <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700">
            {membersLoading ? (
              <div className="text-center text-gray-600 dark:text-slate-400">{TEXT.loading}</div>
            ) : members.length === 0 ? (
              <div className="text-center text-gray-500 dark:text-slate-400">
                {TEXT.membersEmpty}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50 dark:bg-slate-700">
                    <tr>
                      <th className="px-4 py-2 text-end text-gray-600 dark:text-slate-300">
                        {TEXT.columnUser}
                      </th>
                      <th className="px-4 py-2 text-end text-gray-600 dark:text-slate-300">
                        {TEXT.columnEmail}
                      </th>
                      <th className="px-4 py-2 text-end text-gray-600 dark:text-slate-300">
                        {TEXT.columnRole}
                      </th>
                      <th className="px-4 py-2 text-end text-gray-600 dark:text-slate-300">
                        {TEXT.columnActions}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {members.map((member) => (
                      <tr key={member.id}>
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                          <div>{resolveDisplayName(member)}</div>
                          <div className="text-xs text-gray-500 dark:text-slate-400">
                            {resolveSecondaryIdentity(member)}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-300">
                          {member.email || TEXT.fallback}
                        </td>
                        <td className="px-4 py-3">
                          {canManageMembers ? (
                            <select
                              value={member.role}
                              onChange={(event) => handleRoleChange(member.id, event.target.value)}
                              className="border dark:border-slate-600 rounded p-1 text-sm bg-white dark:bg-slate-700 dark:text-white"
                              disabled={!selectedFarmId}
                            >
                              {roles.map((role) => (
                                <option key={role.value} value={role.value}>
                                  {role.label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <span className="text-gray-700 dark:text-slate-300">{member.role}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-end">
                          {canManageMembers && (
                            <button
                              type="button"
                              onClick={() => handleRemoveMember(member.id)}
                              className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                              disabled={!selectedFarmId}
                            >
                              {TEXT.remove}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
