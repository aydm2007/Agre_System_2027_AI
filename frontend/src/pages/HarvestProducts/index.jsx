import { TEXT } from './constants'
import { useHarvestCatalog } from './hooks/useHarvestCatalog'
import ProductForm from './components/ProductForm'
import ProductTable from './components/ProductTable'
import { Sprout } from 'lucide-react'
import { useFarmContext } from '../../api/farmContext.jsx' // [AGRI-GUARDIAN] Tenant Isolation

export default function HarvestProductsPage() {
  const { selectedFarmId, farms } = useFarmContext()
  const {
    // Data
    catalog,
    loadingCatalog,
    crops,
    loadingCrops,
    cropOptions,
    itemOptions,
    units,

    // Filters & Selection
    selectedFarm,
    setSelectedFarm,
    selectedCrop,
    setSelectedCrop,

    // Form
    form,
    setForm,
    submitting,
    handleSubmit,
    resetForm,
    addFormUnit,
    removeFormUnit,
    updateFormUnit,
    markFormDefaultUnit,

    // Actions
    handleDelete,

    // Edit
    editingProduct,
    startEditingProduct,
    cancelEditingProduct,
    handleEditingProductChange,
    saveEditingProduct,
    editingProductSaving,
    addEditingUnit,
    removeEditingUnit,
    updateEditingUnit,
    markEditingDefaultUnit,
  } = useHarvestCatalog(selectedFarmId)

  const clearFilters = () => {
    setSelectedFarm('')
    setSelectedCrop('')
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 p-6 md:p-8 dark:bg-slate-900">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* Header */}
        <header className="flex items-start gap-4">
          <div className="rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 p-3 shadow-sm dark:from-emerald-900/40 dark:to-teal-900/40">
            <Sprout className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
              {TEXT.title}
            </h1>
            <p className="mt-2 text-lg text-gray-600 dark:text-slate-400">{TEXT.description}</p>
          </div>
        </header>

        {/* Create Form */}
        <ProductForm
          form={{ ...form, handleSubmit }} // Pass submit handler
          setForm={setForm}
          submitting={submitting}
          loadingCrops={loadingCrops}
          crops={crops}
          farmOptions={farms || []}
          cropOptions={cropOptions}
          itemOptions={itemOptions}
          units={units}
          addFormUnit={addFormUnit}
          removeFormUnit={removeFormUnit}
          updateFormUnit={updateFormUnit}
          markFormDefaultUnit={markFormDefaultUnit}
          resetForm={resetForm}
        />

        {/* Catalog Table */}
        <ProductTable
          catalog={catalog}
          loadingCatalog={loadingCatalog}
          loadingCrops={loadingCrops}
          farmOptions={farms || []}
          cropOptions={cropOptions}
          selectedFarm={selectedFarm}
          selectedCrop={selectedCrop}
          handleFarmChange={setSelectedFarm}
          setSelectedCrop={setSelectedCrop}
          clearFilters={clearFilters}
          editingProduct={editingProduct}
          startEditingProduct={startEditingProduct}
          cancelEditingProduct={cancelEditingProduct}
          handleEditingProductChange={handleEditingProductChange}
          saveEditingProduct={saveEditingProduct}
          editingProductSaving={editingProductSaving}
          handleDelete={handleDelete}
          addEditingUnit={addEditingUnit}
          removeEditingUnit={removeEditingUnit}
          updateEditingUnit={updateEditingUnit}
          markEditingDefaultUnit={markEditingDefaultUnit}
          units={units}
        />
      </div>
    </div>
  )
}
