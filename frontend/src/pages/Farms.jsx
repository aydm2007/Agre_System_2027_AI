import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import ar from '../i18n/ar'
import { useFarms } from '../hooks/useFarms'
import FarmFilters from '../components/farms/FarmFilters'
import FarmList from '../components/farms/FarmList'
import FarmForm from '../components/farms/FarmForm'
import { Toaster, toast } from 'react-hot-toast'
import { extractApiError } from '../utils/errorUtils'

const TEXT = ar.farms

export default function FarmsPage() {
  const auth = useAuth()
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingFarm, setEditingFarm] = useState(null)

  // Use the new Hook (The Brain)
  const {
    farms,
    isLoading,
    isError,
    errorMessage,
    addFarm,
    updateFarm,
    deleteFarm,
    isAdding,
    isUpdating,
  } = useFarms(query)

  // Permissions
  const canCreate = auth.canAddModel('farm') || auth.isAdmin || auth.isSuperuser

  // Handlers
  const handleCreate = () => {
    setEditingFarm(null)
    setShowForm(true)
  }

  const handleEdit = (farm) => {
    setEditingFarm(farm)
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm(TEXT.confirmDelete)) return

    try {
      await deleteFarm(id)
      toast.success(TEXT.deleteSuccess)
    } catch (err) {
      toast.error(extractApiError(err, TEXT.loadError))
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingFarm) {
        await updateFarm({ id: editingFarm.id, updates: values })
        toast.success(TEXT.updateSuccess)
      } else {
        await addFarm(values)
        toast.success(TEXT.createSuccess)
      }
      setShowForm(false)
      setEditingFarm(null)
    } catch (err) {
      console.error(err)
      toast.error(extractApiError(err, TEXT.loadError))
    }
  }

  return (
    <div className="p-4 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Toast Notification Container (if not global) */}
      <Toaster position="top-left" />

      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            {TEXT.title}
          </h1>
          <p className="text-gray-500 dark:text-slate-400 mt-1">إدارة الأصول الزراعية</p>
        </div>

        {canCreate && !showForm && (
          <button
            type="button"
            onClick={handleCreate}
            className="self-start px-5 py-2.5 rounded-lg bg-primary text-white font-medium hover:bg-primary-dark transition shadow-md hover:shadow-lg flex items-center gap-2"
          >
            <span>+</span> {TEXT.addFarm}
          </button>
        )}
      </header>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 space-y-6">
        {/* Filters */}
        <FarmFilters
          query={query}
          setQuery={setQuery}
          onRefresh={() => {}} // React Query auto-refetches, but we could refetch() if we exposed it
          onClear={() => setQuery('')}
        />

        {/* Form Section (Conditional) */}
        {showForm && (
          <div className="animate-in fade-in slide-in-from-top-4 duration-300">
            <FarmForm
              initialValues={editingFarm}
              onSubmit={handleSubmit}
              onCancel={() => setShowForm(false)}
              isSubmitting={isAdding || isUpdating}
            />
          </div>
        )}

        {/* List Section */}
        <div className="min-h-[300px]">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
              <p className="text-gray-400 dark:text-slate-500">جاري تحميل المزارع...</p>
            </div>
          ) : isError ? (
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-100 dark:border-red-800 flex items-center gap-3">
              <span className="text-xl">⚠️</span>
              {errorMessage}
            </div>
          ) : (
            <FarmList farms={farms} onEdit={handleEdit} onDelete={handleDelete} />
          )}
        </div>
      </div>
    </div>
  )
}
