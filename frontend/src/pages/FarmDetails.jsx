import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { Farms, Locations, Assets, FarmCrops } from '../api/client'
import { getFarmContext } from '../api/farmContext'
import { generateLocationCode } from '../utils/helpers'
import { useAuth } from '../auth/AuthContext'

export default function FarmDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasFarmAccess, isAdmin, is_superuser, canChangeModel } = useAuth()
  const [farm, setFarm] = useState(null)
  const [locs, setLocs] = useState([])
  const [assets, setAssets] = useState([])
  const [crops, setCrops] = useState([])
  const [editingFarm, setEditingFarm] = useState(null)
  const [showAddLocation, setShowAddLocation] = useState(false)
  const [showAddAsset, setShowAddAsset] = useState(false)
  const [newLocation, setNewLocation] = useState({ name: '', type: 'Field' })
  const [newAsset, setNewAsset] = useState({ name: '', category: 'Machinery' })
  const [newCrop, setNewCrop] = useState('')
  const [editingLocation, setEditingLocation] = useState(null)
  const [editingAsset, setEditingAsset] = useState(null)

  const load = useCallback(async (forceRefresh = false) => {
    try {
      const { data } = await Farms.retrieve(id)
      setFarm(data)

      const context = await getFarmContext(id, { forceRefresh })
      setLocs(context.locations || [])
      setAssets(context.assets || [])
      setCrops(context.crops || [])
    } catch (error) {
      console.error('Error loading farm details:', error)
    }
  }, [id])

  useEffect(() => {
    if (!hasFarmAccess(id)) {
      alert('لا تملك صلاحية للوصول إلى هذه المزرعة.')
      return
    }
    load()
  }, [id, hasFarmAccess, load])

  async function handleUpdateFarm() {
    if (!editingFarm.name.trim()) return

    try {
      await Farms.update(editingFarm.id, editingFarm)
      setEditingFarm(null)
      load(true)
    } catch (error) {
      console.error('Error updating farm:', error)
      alert('حدث خطأ أثناء تحديث بيانات المزرعة.')
    }
  }

  async function handleAddLocation() {
    if (!newLocation.name.trim()) return

    try {
      const code = generateLocationCode(newLocation.type, id)
      
      const locLat = newLocation.latitude ? parseFloat(newLocation.latitude) : null
      const locLng = newLocation.longitude ? parseFloat(newLocation.longitude) : null

      const locationData = { ...newLocation, farm: parseInt(id, 10), code }
      if (locLat !== null) locationData.latitude = locLat
      else delete locationData.latitude
      if (locLng !== null) locationData.longitude = locLng
      else delete locationData.longitude

      await Locations.create(locationData)
      setNewLocation({ name: '', type: 'Field', latitude: '', longitude: '' })
      setShowAddLocation(false)
      load(true)
    } catch (error) {
      console.error('Error adding location:', error)
      const errDetail = error.response?.data ? JSON.stringify(error.response.data) : error.message
      alert(`حدث خطأ أثناء إضافة الموقع:\n${errDetail}`)
    }
  }

  async function handleUpdateLocation() {
    if (!editingLocation.name.trim()) return

    try {
      await Locations.update(editingLocation.id, editingLocation)
      setEditingLocation(null)
      load(true)
    } catch (error) {
      console.error('Error updating location:', error)
      alert('حدث خطأ أثناء تحديث الموقع.')
    }
  }

  async function handleDeleteLocation(locationId) {
    if (!window.confirm('هل أنت متأكد من حذف هذا الموقع؟')) return

    try {
      await Locations.delete(locationId)
      load(true)
    } catch (error) {
      console.error('Error deleting location:', error)
      alert('حدث خطأ أثناء حذف الموقع.')
    }
  }

  async function handleAddAsset() {
    if (!newAsset.name.trim()) return

    try {
      await Assets.create({ ...newAsset, farm: parseInt(id, 10) })
      setNewAsset({ name: '', category: 'Machinery' })
      setShowAddAsset(false)
      load(true)
    } catch (error) {
      console.error('Error adding asset:', error)
      const errDetail = error.response?.data ? JSON.stringify(error.response.data) : error.message
      alert(`حدث خطأ أثناء إضافة الأصل:\n${errDetail}`)
    }
  }

  async function handleUpdateAsset() {
    if (!editingAsset.name.trim()) return

    try {
      await Assets.update(editingAsset.id, editingAsset)
      setEditingAsset(null)
      load(true)
    } catch (error) {
      console.error('Error updating asset:', error)
      alert('حدث خطأ أثناء تحديث الأصل.')
    }
  }

  async function handleDeleteAsset(assetId) {
    if (!window.confirm('هل أنت متأكد من حذف هذا الأصل؟')) return

    try {
      await Assets.delete(assetId)
      load(true)
    } catch (error) {
      console.error('Error deleting asset:', error)
      alert('حدث خطأ أثناء حذف الأصل.')
    }
  }

  async function _handleAddCrop() {
    if (!newCrop || newCrop === 'new') return

    try {
      await FarmCrops.create({ farm: parseInt(id, 10), crop: parseInt(newCrop, 10) })
      setNewCrop('')
      load(true)
    } catch (error) {
      console.error('Error adding crop to farm:', error)
      const errDetail = error.response?.data ? JSON.stringify(error.response.data) : error.message
      alert(`حدث خطأ أثناء ربط المحصول بالمزرعة:\n${errDetail}`)
    }
  }

  async function handleRemoveCrop(cropId) {
    if (!window.confirm('هل أنت متأكد من إزالة هذا المحصول من المزرعة؟')) return

    try {
      const farmCrop = farm.farm_crops?.find((fc) => fc.crop === parseInt(cropId, 10))
      if (farmCrop) {
        await FarmCrops.delete(farmCrop.id)
        load(true)
      }
    } catch (error) {
      console.error('Error removing crop from farm:', error)
      alert('حدث خطأ أثناء إزالة المحصول من المزرعة.')
    }
  }

  if (!farm) return <div>جار التحميل...</div>

  return (
    <section className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold dark:text-white">تفاصيل المزرعة: {farm.name}</h2>
        {(canChangeModel('farm') || isAdmin || is_superuser) && (
          <button
            onClick={() => setEditingFarm(farm)}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            تعديل بيانات المزرعة
          </button>
        )}
      </div>

      {editingFarm && (
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700">
          <h3 className="font-bold mb-3 dark:text-white">تعديل بيانات المزرعة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                اسم المزرعة
              </label>
              <input
                type="text"
                value={editingFarm.name}
                onChange={(e) => setEditingFarm({ ...editingFarm, name: e.target.value })}
                className="w-full border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                المنطقة / الموقع
              </label>
              <input
                type="text"
                value={editingFarm.region || ''}
                onChange={(e) => setEditingFarm({ ...editingFarm, region: e.target.value })}
                className="w-full border rounded p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المساحة (فدان)</label>
              <input
                type="text"
                value={editingFarm.area || ''}
                onChange={(e) => setEditingFarm({ ...editingFarm, area: e.target.value })}
                className="w-full border rounded p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
              <input
                type="text"
                value={editingFarm.description || ''}
                onChange={(e) => setEditingFarm({ ...editingFarm, description: e.target.value })}
                className="w-full border rounded p-2"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleUpdateFarm}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
            >
              حفظ
            </button>
            <button
              onClick={() => setEditingFarm(null)}
              className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-600 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-3">
        <div className="p-3 bg-white dark:bg-slate-800 rounded-xl shadow border dark:border-slate-700">
          <div className="text-gray-500 dark:text-slate-400 text-sm">المنطقة</div>
          <div className="font-bold dark:text-white">{farm.region || '-'}</div>
        </div>
        <div className="p-3 bg-white dark:bg-slate-800 rounded-xl shadow border dark:border-slate-700">
          <div className="text-gray-500 dark:text-slate-400 text-sm">عدد المواقع</div>
          <div className="font-bold dark:text-white">{locs.length}</div>
        </div>
        <div className="p-3 bg-white dark:bg-slate-800 rounded-xl shadow border dark:border-slate-700">
          <div className="text-gray-500 dark:text-slate-400 text-sm">عدد الأصول</div>
          <div className="font-bold dark:text-white">{assets.length}</div>
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-bold dark:text-white">المحاصيل</h3>
          {(canChangeModel('farm') || isAdmin || is_superuser) && (
            <button
              onClick={() => navigate(`/crops?farmId=${id}&addCrop=true`)}
              className="px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary-dark transition-colors"
            >
              إضافة محصول
            </button>
          )}
        </div>


        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
          {farm.farm_crops?.map((fc) => {
            const crop = crops.find((c) => c.id === fc.crop)
            const cropName = crop?.name || fc.crop_name || 'محصول'
            const cropMode = crop?.mode || ''
            return (
              <div
                key={fc.id}
                className="p-3 bg-white dark:bg-slate-800 rounded border dark:border-slate-700 shadow-sm relative"
              >
                <div className="font-bold dark:text-white">
                  {cropName}{' '}
                  {cropMode ? (
                    <span className="text-xs text-gray-500 dark:text-slate-400">({cropMode})</span>
                  ) : null}
                </div>
                {crop?.id ? (
                  <Link
                    to={`/crops/${crop.id}/tasks`}
                    className="inline-block mt-1 px-2 py-1 bg-primary text-white rounded text-xs"
                  >
                    عرض المهام
                  </Link>
                ) : null}
                {(canChangeModel('farm') || isAdmin || is_superuser) && (
                  <button
                    onClick={() => handleRemoveCrop(crop?.id || fc.crop)}
                    className="absolute top-1 left-1 p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors"
                    title="حذف"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>
            )
          })}
          {(!farm.farm_crops || farm.farm_crops.length === 0) && (
            <div className="text-gray-500 dark:text-slate-400">لا توجد محاصيل مرتبطة.</div>
          )}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-bold dark:text-white">المواقع</h3>
          {(canChangeModel('farm') || isAdmin || is_superuser) && (
            <button
              onClick={() => setShowAddLocation(!showAddLocation)}
              className="px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary-dark transition-colors"
            >
              {showAddLocation ? 'إلغاء' : 'إضافة موقع جديد'}
            </button>
          )}
        </div>

        {showAddLocation && (
          <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow border dark:border-slate-700 mb-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <input
                type="text"
                value={newLocation.name}
                onChange={(e) => setNewLocation({ ...newLocation, name: e.target.value })}
                className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
                placeholder="اسم الموقع"
              />
              <select
                value={newLocation.type}
                onChange={(e) => setNewLocation({ ...newLocation, type: e.target.value })}
                className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
              >
                <option value="Field">حقل</option>
                <option value="Protected">بيت محمي</option>
                <option value="Orchard">بستان</option>
                <option value="Grain">حبوب</option>
                <option value="Service">خدمة</option>
                <option value="Store">مخزن</option>
                <option value="Warehouse">مستودع مركزي</option>
                <option value="other">أخرى</option>
              </select>
              <input
                type="number"
                step="0.000001"
                value={newLocation.latitude || ''}
                onChange={(e) => setNewLocation({ ...newLocation, latitude: e.target.value })}
                className="border rounded p-2"
                placeholder="خط العرض (Latitude)"
              />
              <input
                type="number"
                step="0.000001"
                value={newLocation.longitude || ''}
                onChange={(e) => setNewLocation({ ...newLocation, longitude: e.target.value })}
                className="border rounded p-2"
                placeholder="خط الطول (Longitude)"
              />
            </div>
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleAddLocation}
                className="px-3 py-1 bg-primary text-white rounded"
              >
                إضافة
              </button>
              <button
                onClick={() => {
                  setShowAddLocation(false)
                  setNewLocation({ name: '', type: 'Field' })
                }}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded"
              >
                إلغاء
              </button>
            </div>
          </div>
        )}

        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
          {locs.map((l) => (
            <div
              key={l.id}
              className="p-3 bg-white dark:bg-slate-800 rounded border dark:border-slate-700 shadow-sm relative"
            >
              {editingLocation?.id === l.id ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editingLocation.name}
                    onChange={(e) =>
                      setEditingLocation({ ...editingLocation, name: e.target.value })
                    }
                    className="w-full border rounded p-1 font-bold"
                    placeholder="الاسم"
                  />
                  <select
                    value={editingLocation.type}
                    onChange={(e) =>
                      setEditingLocation({ ...editingLocation, type: e.target.value })
                    }
                    className="w-full border rounded p-1 text-xs"
                  >
                    <option value="Field">حقل</option>
                    <option value="Protected">بيت محمي</option>
                    <option value="Orchard">بستان</option>
                    <option value="Grain">حبوب</option>
                    <option value="Service">خدمة</option>
                  </select>
                  <div className="grid grid-cols-2 gap-1">
                    <input
                      type="number"
                      step="0.000001"
                      value={editingLocation.latitude || ''}
                      onChange={(e) =>
                        setEditingLocation({ ...editingLocation, latitude: e.target.value })
                      }
                      className="w-full border rounded p-1 text-xs"
                      placeholder="Lat"
                    />
                    <input
                      type="number"
                      step="0.000001"
                      value={editingLocation.longitude || ''}
                      onChange={(e) =>
                        setEditingLocation({ ...editingLocation, longitude: e.target.value })
                      }
                      className="w-full border rounded p-1 text-xs"
                      placeholder="Long"
                    />
                  </div>
                  <div className="flex gap-1 mt-1">
                    <button
                      onClick={handleUpdateLocation}
                      className="px-2 py-1 bg-primary text-white rounded text-xs"
                    >
                      حفظ
                    </button>
                    <button
                      onClick={() => setEditingLocation(null)}
                      className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs"
                    >
                      إلغاء
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="font-bold dark:text-white">
                    {l.name}{' '}
                    <span className="text-xs text-gray-500 dark:text-slate-400">
                      ({l.type || l.kind || '-'})
                    </span>
                  </div>
                  {l.latitude && l.longitude && (
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${l.latitude},${l.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1 mt-1"
                    >
                      📍 عرض على الخريطة
                    </a>
                  )}
                  {(canChangeModel('farm') || isAdmin || is_superuser) && (
                    <div className="absolute top-1 left-1 flex gap-1">
                      <button
                        onClick={() => setEditingLocation(l)}
                        className="p-1 bg-blue-100 text-blue-600 rounded-full hover:bg-blue-200 transition-colors"
                        title="تعديل"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteLocation(l.id)}
                        className="p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors"
                        title="حذف"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          {locs.length === 0 && (
            <div className="text-gray-500 dark:text-slate-400">لا يوجد مواقع مسجلة.</div>
          )}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-bold dark:text-white">الأصول</h3>
          {(canChangeModel('farm') || isAdmin || is_superuser) && (
            <button
              onClick={() => setShowAddAsset(!showAddAsset)}
              className="px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary-dark transition-colors"
            >
              {showAddAsset ? 'إلغاء' : 'إضافة أصل'}
            </button>
          )}
        </div>

        {showAddAsset && (
          <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow border dark:border-slate-700 mb-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <input
                type="text"
                value={newAsset.name}
                onChange={(e) => setNewAsset({ ...newAsset, name: e.target.value })}
                className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
                placeholder="اسم الأصل"
              />
              <select
                value={newAsset.category}
                onChange={(e) => setNewAsset({ ...newAsset, category: e.target.value })}
                className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
              >
                <option value="Machinery">معدات</option>
                <option value="Well">بئر</option>
              </select>
            </div>
            <div className="flex gap-2 mt-2">
              <button onClick={handleAddAsset} className="px-3 py-1 bg-primary text-white rounded">
                إضافة
              </button>
              <button
                onClick={() => {
                  setShowAddAsset(false)
                  setNewAsset({ name: '', category: 'Machinery' })
                }}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded"
              >
                إلغاء
              </button>
            </div>
          </div>
        )}

        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
          {assets.map((a) => (
            <div
              key={a.id}
              className="p-3 bg-white dark:bg-slate-800 rounded border dark:border-slate-700 shadow-sm relative"
            >
              {editingAsset?.id === a.id ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editingAsset.name}
                    onChange={(e) => setEditingAsset({ ...editingAsset, name: e.target.value })}
                    className="w-full border rounded p-1 font-bold"
                  />
                  <select
                    value={editingAsset.category}
                    onChange={(e) => setEditingAsset({ ...editingAsset, category: e.target.value })}
                    className="w-full border rounded p-1 text-xs"
                  >
                    <option value="Machinery">معدات</option>
                    <option value="Well">بئر</option>
                  </select>
                  <div className="flex gap-1">
                    <button
                      onClick={handleUpdateAsset}
                      className="px-2 py-1 bg-primary text-white rounded text-xs"
                    >
                      حفظ
                    </button>
                    <button
                      onClick={() => setEditingAsset(null)}
                      className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs"
                    >
                      إلغاء
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="font-bold dark:text-white">
                    {a.name}{' '}
                    <span className="text-xs text-gray-500 dark:text-slate-400">
                      ({a.category || '-'})
                    </span>
                  </div>
                  {(canChangeModel('farm') || isAdmin || is_superuser) && (
                    <div className="absolute top-1 left-1 flex gap-1">
                      <button
                        onClick={() => setEditingAsset(a)}
                        className="p-1 bg-blue-100 text-blue-600 rounded-full hover:bg-blue-200 transition-colors"
                        title="تعديل"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteAsset(a.id)}
                        className="p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors"
                        title="حذف"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          {assets.length === 0 && (
            <div className="text-gray-500 dark:text-slate-400">لا يوجد أصول مسجلة.</div>
          )}
        </div>
      </div>
    </section>
  )
}
