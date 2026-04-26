import { useCallback, useEffect, useState } from 'react'
import { Supervisors } from '../../api/client'
import FeedbackRegion from '../../components/FeedbackRegion'
import useFeedback from '../../hooks/useFeedback'
import ar from '../../i18n/ar'

const TEXT = ar.settings

const INITIAL_FORM = { name: '', code: '' }

export default function SupervisorsTab({ selectedFarmId }) {
  const [supervisors, setSupervisors] = useState([])
  const [supervisorsLoading, setSupervisorsLoading] = useState(false)
  const [supervisorForm, setSupervisorForm] = useState(INITIAL_FORM)
  const [editingSupervisorId, setEditingSupervisorId] = useState(null)
  const [savingSupervisor, setSavingSupervisor] = useState(false)

  const { message, error, showMessage, showError } = useFeedback()

  const loadSupervisors = useCallback(
    async (farmId) => {
      if (!farmId) {
        setSupervisors([])
        return
      }
      setSupervisorsLoading(true)
      try {
        const response = await Supervisors.list({ farm_id: farmId })
        const data = response.data?.results ?? response.data ?? []
        setSupervisors(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('Failed to load supervisors', err)
        showError(TEXT.supervisorsError)
        setSupervisors([])
      } finally {
        setSupervisorsLoading(false)
      }
    },
    [showError],
  )

  useEffect(() => {
    setSupervisorForm(INITIAL_FORM)
    setEditingSupervisorId(null)
    loadSupervisors(selectedFarmId)
  }, [loadSupervisors, selectedFarmId])

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault()
      if (!supervisorForm.name.trim()) {
        showError(TEXT.supervisorFormError)
        return
      }
      setSavingSupervisor(true)
      try {
        if (editingSupervisorId) {
          await Supervisors.update(editingSupervisorId, {
            name: supervisorForm.name.trim(),
            code: supervisorForm.code.trim() || null,
          })
          showMessage(TEXT.supervisorUpdated)
        } else {
          await Supervisors.create({
            farm: selectedFarmId,
            name: supervisorForm.name.trim(),
            code: supervisorForm.code.trim() || null,
          })
          showMessage(TEXT.supervisorAdded)
        }
        setSupervisorForm(INITIAL_FORM)
        setEditingSupervisorId(null)
        loadSupervisors(selectedFarmId)
      } catch (err) {
        console.error('Failed to save supervisor', err)
        showError(TEXT.supervisorActionError)
      } finally {
        setSavingSupervisor(false)
      }
    },
    [
      editingSupervisorId,
      loadSupervisors,
      selectedFarmId,
      showError,
      showMessage,
      supervisorForm.code,
      supervisorForm.name,
    ],
  )

  const handleEdit = useCallback((supervisor) => {
    setEditingSupervisorId(supervisor.id)
    setSupervisorForm({ name: supervisor.name, code: supervisor.code || '' })
  }, [])

  const handleCancelEdit = useCallback(() => {
    setEditingSupervisorId(null)
    setSupervisorForm(INITIAL_FORM)
  }, [])

  const handleRemove = useCallback(
    async (supervisorId) => {
      if (!window.confirm(TEXT.confirmRemoveSupervisor)) {
        return
      }
      try {
        await Supervisors.remove(supervisorId)
        showMessage(TEXT.supervisorDeleted)
        setSupervisors((prev) => prev.filter((supervisor) => supervisor.id !== supervisorId))
      } catch (err) {
        console.error('Failed to remove supervisor', err)
        showError(TEXT.supervisorActionError)
      }
    },
    [showError, showMessage],
  )

  return (
    <section className="space-y-4" key="supervisors">
      <FeedbackRegion error={error} message={message} />

      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-3"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-200"
              htmlFor="supervisor-name"
            >
              {TEXT.supervisorName}
            </label>
            <input
              id="supervisor-name"
              type="text"
              value={supervisorForm.name}
              onChange={(event) =>
                setSupervisorForm((prev) => ({ ...prev, name: event.target.value }))
              }
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
              disabled={!selectedFarmId}
            />
          </div>
          <div>
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-200"
              htmlFor="supervisor-code"
            >
              {TEXT.supervisorCode}
            </label>
            <input
              id="supervisor-code"
              type="text"
              value={supervisorForm.code}
              onChange={(event) =>
                setSupervisorForm((prev) => ({ ...prev, code: event.target.value }))
              }
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
              disabled={!selectedFarmId}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          {editingSupervisorId && (
            <button
              type="button"
              onClick={handleCancelEdit}
              className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded hover:bg-gray-300 dark:hover:bg-slate-600"
            >
              {TEXT.cancel}
            </button>
          )}
          <button
            type="submit"
            disabled={savingSupervisor || !selectedFarmId}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark disabled:opacity-60"
          >
            {savingSupervisor ? TEXT.loading : TEXT.save}
          </button>
        </div>
      </form>

      <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700">
        {supervisorsLoading ? (
          <div className="text-center text-gray-600 dark:text-slate-400">{TEXT.loading}</div>
        ) : supervisors.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-slate-400">
            {TEXT.supervisorsEmpty}
          </div>
        ) : (
          <div className="space-y-3">
            {supervisors.map((supervisor) => (
              <div
                key={supervisor.id}
                className="flex items-center justify-between border dark:border-slate-700 rounded p-3"
              >
                <div>
                  <h4 className="font-semibold text-gray-900 dark:text-white">{supervisor.name}</h4>
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    {supervisor.code || '?'}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleEdit(supervisor)}
                    className="px-3 py-1 text-sm bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded hover:bg-gray-300 dark:hover:bg-slate-600"
                  >
                    {TEXT.edit}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemove(supervisor.id)}
                    className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    {TEXT.remove}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
