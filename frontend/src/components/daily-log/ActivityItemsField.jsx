import { useState, useEffect, useMemo } from 'react'
import { MaterialCatalog, Items } from '../../api/client'
import { extractApiError } from '../../utils/errorUtils.js'
import { db } from '../../offline/dexie_db.js'
import { MATERIAL_TYPES } from '../../pages/daily-log/constants.js'

export const ActivityItemsField = ({
  items = [],
  onUpdate, // Rename to match DailyLogDetails usage
  onChange: legacyOnChange,
  farmId = null,
  cropId = null,
  materials = [], // New prop for external lookup
  sourceHint = '',
}) => {
  const onChange = onUpdate || legacyOnChange || (() => {}) // Bridge
  const [availableItems, setAvailableItems] = useState(materials)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!Array.isArray(materials) || materials.length === 0) return
    const normalizedMaterials = materials.map((entry) => ({
      id: entry?.item_id ?? entry?.id,
      name: entry?.item_name ?? entry?.name,
      group: entry?.item_group ?? entry?.group ?? '',
      material_type: entry?.item_material_type ?? entry?.material_type ?? '',
      uom:
        entry?.recommended_uom ||
        entry?.on_hand_uom ||
        entry?.item_uom ||
        entry?.uom ||
        entry?.recommended_unit_detail?.symbol ||
        '',
      unit: entry?.recommended_unit || entry?.unit || entry?.recommended_unit_detail || null,
      recommended_qty: entry?.recommended_qty,
      on_hand_qty: entry?.on_hand_qty,
      low_stock: entry?.low_stock,
    })).filter((entry) => entry.id != null)

    setAvailableItems((previous) => {
      const merged = new Map(previous.map((entry) => [String(entry.id), entry]))
      normalizedMaterials.forEach((entry) => {
        const key = String(entry.id)
        merged.set(key, { ...merged.get(key), ...entry })
      })
      return Array.from(merged.values())
    })
  }, [materials])

  useEffect(() => {
    let isMounted = true
    const fetchItems = async () => {
      try {
        setLoading(true)
        let data = []

        if (farmId && cropId) {
          try {
            // [ZENITH 11.5 FIX] Reverting back to farm_id and crop_id for MaterialCatalog which requires exact ID routing
            const res = await MaterialCatalog.list({ farm_id: farmId, crop_id: cropId })
            // MaterialCatalog يُرجع: { item_id, item_name, ... }
            data = (res.data || []).map((cm) => ({
              id: cm.item_id,
              name: cm.item_name,
              group: cm.item_group,
              material_type: cm.item_material_type || '',
              uom: cm.recommended_uom || cm.on_hand_uom || cm.uom || '',
              unit: cm.recommended_unit || cm.unit,
              recommended_qty: cm.recommended_qty,
              on_hand_qty: cm.on_hand_qty,
              low_stock: cm.low_stock,
            }))

            // Background sync for offline mode
            setTimeout(async () => {
              try {
                const toAdd = (res.data || []).filter(cm => cm.item_id).map(cm => ({
                  id: cm.crop_material_id || `${farmId}_${cm.crop_id}_${cm.item_id}`,
                  crop_id: Number(cm.crop_id) || Number(cropId),
                  item_id: Number(cm.item_id),
                  farm_id: Number(farmId),
                }))
                if (toAdd.length) {
                  await db.crop_materials.bulkPut(toAdd)
                }
              } catch (e) {
                console.error("Failed to sync crop_materials to Dexie", e)
              }
            }, 0)

          } catch (err) {
            console.warn('MaterialCatalog request failed. Searching offline DB as fallback...', err)
            
            // First fallback: Check if we have crop materials synced
            let offlineCropMaterials = [];
            try {
              offlineCropMaterials = await db.crop_materials.where('[farm_id+crop_id]').equals([Number(farmId), Number(cropId)]).toArray()
            } catch (idxErr) {
              console.warn('Failed Dexie composite index for crop_materials', idxErr)
            }

            let offlineItems = []
            if (offlineCropMaterials && offlineCropMaterials.length > 0) {
              const itemIds = offlineCropMaterials.map(cm => Number(cm.item_id))
              offlineItems = await db.items.where('id').anyOf(itemIds).toArray()
            } else {
              // Ultimate Fallback: all items for the farm
              offlineItems = await db.items.where('farm_id').anyOf([Number(farmId), String(farmId)]).toArray()
            }

            data = offlineItems.map((item) => ({
              id: item.id,
              name: item.name,
              group: item.category || item.group || '',
              material_type: item.material_type || '',
              uom: item.uom || '',
            }))
          }
        } else if (farmId) {
          try {
            // Fallback: جميع مواد المزرعة إن لم يكن محصول محدد
            const res = await Items.list({ limit: 500, exclude_group: 'Produce,Fuel' })
            data = res.data?.results || res.data || []
          } catch (err) {
            console.warn('Items request failed. Searching offline DB as fallback...', err)
            const offlineItems = await db.items.where('farm_id').anyOf([Number(farmId), String(farmId)]).toArray()
            data = offlineItems
          }
        }

        if (isMounted) setAvailableItems(data)
      } catch (err) {
        console.error('Failed to load items', extractApiError(err))
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    fetchItems()
    return () => { isMounted = false }
  }, [farmId, cropId])

  const addItem = () => {
    onChange([...(items || []), { item_id: '', qty: '', uom: '', batch_number: '' }])
  }

  const updateItem = (index, field, value) => {
    const newItems = [...(items || [])]
    newItems[index][field] = value
    if (field === 'item_id') {
      const selected = availableItems.find((i) => String(i.id) === String(value))
      if (selected) {
        newItems[index].uom = selected.unit?.symbol || selected.uom || ''
        // Auto-fill recommended quantity
        if (!newItems[index].qty && selected.recommended_qty) {
          newItems[index].qty = String(selected.recommended_qty)
        }
      }
    }
    onChange(newItems)
  }

  const removeItem = (index) => {
    const newItems = [...(items || [])]
    newItems.splice(index, 1)
    onChange(newItems)
  }

  const getSelectedItem = (itemId) =>
    availableItems.find((candidate) => String(candidate.id) === String(itemId))

  // Group available items by their material type for a cleaner dropdown
  const groupedItems = useMemo(() => {
    const groups = {}
    availableItems.forEach((item) => {
      const g = item.material_type ? (MATERIAL_TYPES[item.material_type] || item.material_type) : (item.group || 'أخرى')
      if (!groups[g]) groups[g] = []
      groups[g].push(item)
    })
    return groups
  }, [availableItems])

  return (
    <div className="space-y-3 mt-4 animate-in fade-in">
      <div className="flex justify-between items-center bg-emerald-50 dark:bg-emerald-900/20 p-3 rounded-lg border border-emerald-100 dark:border-emerald-800">
        <div>
          <label className="block text-sm font-bold text-emerald-800 dark:text-emerald-300">
            🌱 المواد المستهلكة {cropId ? '(محصول مختار)' : '(غير مفلترة)'}
          </label>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
            {cropId
              ? 'تعرض فقط المواد المسجلة لهذا المحصول مع الكميات الموصى بها'
              : 'اختر المحصول أولاً لعرض مواده المحددة'}
          </p>
          {sourceHint ? (
            <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-300">{sourceHint}</p>
          ) : null}
        </div>
        <button type="button" onClick={addItem}
          className="text-sm bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg shadow-sm transition-colors"
        >
          + إضافة مادة
        </button>
      </div>

      {loading && <div className="text-xs text-gray-500 text-center">جاري تحميل قائمة المواد...</div>}
      {!loading && cropId && availableItems.length === 0 && (
        <div className="text-xs text-amber-600 text-center py-2 bg-amber-50 rounded border border-amber-200">
          لا توجد مواد مسجلة لهذا المحصول في كتالوج المزرعة. يمكن إضافتها من إعدادات المحاصيل.
        </div>
      )}

      {items && items.length > 0 && (
        <div className="space-y-2">
          {items.map((it, idx) => {
            const selectedMeta = getSelectedItem(it.item_id)
            const isItemSelected = (id) => items.some((otherIt, otherIdx) => otherIdx !== idx && String(otherIt.item_id) === String(id))
            return (
              <div key={idx}
                className="flex flex-wrap gap-2 items-center bg-white dark:bg-slate-700 p-3 rounded border border-gray-200 dark:border-slate-600 shadow-sm"
              >
                <select
                  data-testid={`activity-item-select-${idx}`}
                  value={it.item_id}
                  onChange={(e) => updateItem(idx, 'item_id', e.target.value)}
                  className="p-2 border border-gray-300 rounded text-sm w-1/3 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-200"
                >
                  <option value="">اختر المادة...</option>
                  {Object.entries(groupedItems).map(([groupName, itemsInGroup]) => (
                    <optgroup key={groupName} label={groupName}>
                      {itemsInGroup.map((a) => (
                        <option key={a.id} value={a.id} disabled={isItemSelected(a.id)}>
                          {a.name}
                          {a.low_stock ? ' ⚠️' : ''}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                <input
                  data-testid={`activity-item-qty-${idx}`}
                  type="number" min="0" max={selectedMeta?.on_hand_qty !== undefined ? selectedMeta.on_hand_qty : ''} step="0.01"
                  placeholder={selectedMeta?.recommended_qty ? `موصى: ${selectedMeta.recommended_qty}` : 'الكمية'}
                  value={it.qty}
                  onChange={(e) => updateItem(idx, 'qty', e.target.value)}
                  className="p-2 border border-gray-300 rounded w-28 text-sm dark:bg-slate-800 focus:ring-2 focus:ring-emerald-200"
                />
                <div className="flex flex-col">
                  <span className="text-[10px] text-gray-400 mb-0.5">وحدة</span>
                  <input
                    data-testid={`activity-item-uom-${idx}`}
                    type="text" readOnly
                    value={it.uom || selectedMeta?.uom || ''}
                    className="p-2 border border-emerald-200 dark:border-emerald-800 rounded w-16 text-[11px] font-extrabold bg-emerald-50/50 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-300 shadow-inner"
                  />
                </div>
                {selectedMeta && selectedMeta.on_hand_qty !== undefined && (
                  <div className="flex flex-col text-[10px] space-y-1">
                    <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100 flex items-center gap-1">
                      📦 {selectedMeta.on_hand_qty}
                    </span>
                    {selectedMeta.low_stock && (
                      <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded border border-amber-200 flex items-center gap-1 font-bold animate-pulse">
                        ⚠️ منخفض
                      </span>
                    )}
                  </div>
                )}
                {selectedMeta?.requires_batch_tracking && (
                  <input type="text" placeholder="رقم الدفعة / GlobalGAP"
                    value={it.batch_number}
                    onChange={(e) => updateItem(idx, 'batch_number', e.target.value)}
                    className="p-2 border rounded flex-1 text-sm border-emerald-300 focus:ring-2 focus:ring-emerald-200"
                  />
                )}
                <button type="button" onClick={() => removeItem(idx)}
                  className="text-red-500 hover:text-red-700 font-bold px-3 py-2 bg-red-50 rounded"
                >X</button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
