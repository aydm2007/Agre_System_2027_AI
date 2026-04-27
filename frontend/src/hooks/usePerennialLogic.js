import { useCallback, useEffect, useMemo } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { getAvailableVarietiesForLocation } from '../utils/agronomyUtils'

const UNKNOWN_LOCATION_LABEL = (locationId) => `الموقع ${locationId}`
const UNKNOWN_VARIETY_LABEL = 'الصنف غير معروف في ملخص المواقع المختارة'

function resolveEffectiveAvailableCount(currentCount, cohortAliveCount) {
  const normalizedCurrent = Number(currentCount || 0)
  const normalizedCohortAlive = Number(cohortAliveCount || 0)
  return normalizedCurrent > 0 ? normalizedCurrent : normalizedCohortAlive
}

export function usePerennialLogic(
  form,
  setForm,
  lookups,
  strictErpMode = true,
  taskContext = null,
) {
  const selectedLocationIds = useMemo(
    () =>
      Array.isArray(form?.locations)
        ? form.locations.map((locationId) => String(locationId))
        : [],
    [form?.locations],
  )

  const hasSelectedLocations = selectedLocationIds.length > 0

  const locationNameMap = useMemo(
    () =>
      Object.fromEntries(
        (Array.isArray(lookups?.locations) ? lookups.locations : []).map((location) => [
          String(location.id),
          location.name || UNKNOWN_LOCATION_LABEL(location.id),
        ]),
      ),
    [lookups?.locations],
  )

  const varietiesMeta = useMemo(
    () =>
      lookups?.varietiesMeta || {
        usedFallback: false,
        emptyReason: '',
        diagnostics: null,
      },
    [lookups?.varietiesMeta],
  )

  const treeVarietySummaryRaw = useMemo(
    () => (Array.isArray(lookups?.treeVarietySummary) ? lookups.treeVarietySummary : []),
    [lookups?.treeVarietySummary],
  )

  const perennialVarietySummary = useMemo(() => {
    if (treeVarietySummaryRaw.length > 0) {
      return treeVarietySummaryRaw
        .map((entry) => {
          const byLocation =
            entry?.by_location && typeof entry.by_location === 'object' ? entry.by_location : {}
          let locationIds = Array.isArray(entry?.location_ids)
            ? entry.location_ids.map((locationId) => String(locationId))
            : Object.keys(byLocation).map((locationId) => String(locationId))
          const rawCurrentTreeCountByLocation = Object.fromEntries(
            Object.entries(byLocation).map(([locationId, row]) => [
              String(locationId),
              Number(row?.current_tree_count || 0),
            ]),
          )
          const cohortAliveByLocation = Object.fromEntries(
            Object.entries(byLocation).map(([locationId, row]) => [
              String(locationId),
              Number(row?.cohort_alive_total || 0),
            ]),
          )
          const effectiveCurrentTreeCountByLocation = Object.fromEntries(
            Object.keys({ ...rawCurrentTreeCountByLocation, ...cohortAliveByLocation }).map(
              (locationId) => [
                String(locationId),
                resolveEffectiveAvailableCount(
                  rawCurrentTreeCountByLocation[locationId],
                  cohortAliveByLocation[locationId],
                ),
              ],
            ),
          )
          const hasLocationAwareCoverage =
            locationIds.length > 0 &&
            Object.keys({ ...effectiveCurrentTreeCountByLocation, ...cohortAliveByLocation }).length >
              0

          if (hasSelectedLocations && !hasLocationAwareCoverage) {
            locationIds = []
          }

          return {
            varietyId: String(entry.variety_id),
            varietyName: entry.variety_name || UNKNOWN_VARIETY_LABEL,
            locationIds,
            availableInAllLocations: Boolean(entry.available_in_all_locations),
            currentTreeCountTotal: Number(
              resolveEffectiveAvailableCount(
                entry.current_tree_count_total,
                entry.cohort_alive_total,
              ) || 0,
            ),
            currentTreeCountByLocation: effectiveCurrentTreeCountByLocation,
            rawCurrentTreeCountTotal: Number(entry.current_tree_count_total || 0),
            rawCurrentTreeCountByLocation,
            cohortAliveTotal: Number(entry.cohort_alive_total || 0),
            cohortAliveByLocation,
            cohortStatusBreakdown: entry.cohort_status_breakdown || {},
            cohortStatusBreakdownByLocation: Object.fromEntries(
              Object.entries(byLocation).map(([locationId, row]) => [
                String(locationId),
                row?.cohort_status_breakdown || {},
              ]),
            ),
            cohortStockDelta: Number(entry.cohort_stock_delta || 0),
            hasReconciliationGap: Boolean(entry.has_reconciliation_gap),
            usedCohortFallback:
              Number(entry.current_tree_count_total || 0) <= 0 &&
              Number(entry.cohort_alive_total || 0) > 0,
          }
        })
        .filter(Boolean)
    }

    return Array.isArray(lookups?.varieties)
      ? lookups.varieties
          .map((variety) => {
            let locationIds = Array.isArray(variety.location_ids)
              ? variety.location_ids.map((locationId) => String(locationId))
              : []
            const currentTreeCountByLocation =
              variety.current_tree_count_by_location &&
              typeof variety.current_tree_count_by_location === 'object'
                ? Object.fromEntries(
                    Object.entries(variety.current_tree_count_by_location).map(
                      ([locationId, count]) => [String(locationId), Number(count || 0)],
                    ),
                  )
                : {}
            const hasLocationAwareCoverage =
              locationIds.length > 0 && Object.keys(currentTreeCountByLocation).length > 0

            if (hasSelectedLocations && !hasLocationAwareCoverage) {
              locationIds = []
            }

            return {
              varietyId: String(variety.id),
              varietyName: variety.name || UNKNOWN_VARIETY_LABEL,
              locationIds,
              availableInAllLocations: Boolean(variety.available_in_all_locations),
              currentTreeCountTotal: Number(variety.current_tree_count_total || 0),
              currentTreeCountByLocation,
              rawCurrentTreeCountTotal: Number(variety.current_tree_count_total || 0),
              rawCurrentTreeCountByLocation: currentTreeCountByLocation,
              cohortAliveTotal: 0,
              cohortAliveByLocation: {},
              cohortStatusBreakdown: {},
              cohortStatusBreakdownByLocation: {},
              cohortStockDelta: 0,
              hasReconciliationGap: false,
              usedCohortFallback: false,
            }
          })
          .filter(Boolean)
      : []
  }, [hasSelectedLocations, lookups?.varieties, treeVarietySummaryRaw])

  const getVarietySummary = useCallback(
    (varietyId) =>
      perennialVarietySummary.find((entry) => String(entry.varietyId) === String(varietyId)) ||
      null,
    [perennialVarietySummary],
  )

  const getVarietyLocationNames = useCallback(
    (varietyId, locationIds = null) => {
      const summary = getVarietySummary(varietyId)
      if (!summary) return []
      const sourceLocationIds = Array.isArray(locationIds) ? locationIds : summary.locationIds
      return sourceLocationIds
        .map((locationId) => String(locationId))
        .filter((locationId) => summary.locationIds.includes(locationId))
        .map((locationId) => locationNameMap[locationId] || UNKNOWN_LOCATION_LABEL(locationId))
    },
    [getVarietySummary, locationNameMap],
  )

  const isVarietyAvailableInLocation = useCallback(
    (varietyId, locationId) => {
      if (!varietyId || !locationId) return false
      
      const universalVarieties = getAvailableVarietiesForLocation(locationId, {
         cropPlans: lookups?.cropPlans || [],
         tree_census: lookups?.treeVarietySummary || [],
         varieties: lookups?.varieties || []
      })
      if (universalVarieties.some(v => String(v?.id) === String(varietyId))) {
          return true
      }

      const summary = getVarietySummary(varietyId)
      if (!summary) {
          const varietyBase = (lookups?.varieties || []).find(v => String(v.id) === String(varietyId));
          if (varietyBase && (varietyBase.available_in_all_locations || !varietyBase.location_ids || varietyBase.location_ids.length === 0)) {
               return true;
          }
          return false;
      }
      if (Number(form?.tree_count_delta || 0) > 0) {
        return true
      }
      if (summary.availableInAllLocations || summary.locationIds.length === 0) {
          return true;
      }
      return summary.locationIds.includes(String(locationId))
    },
    [form?.tree_count_delta, getVarietySummary, lookups],
  )

  const getVarietyCount = useCallback(
    (varietyId, locationId = null) => {
      const summary = getVarietySummary(varietyId)
      if (!summary) return '?'
      if (locationId) {
        const count = summary.currentTreeCountByLocation[String(locationId)]
        return typeof count === 'number' ? count : 0
      }
      return summary.currentTreeCountTotal
    },
    [getVarietySummary],
  )

  const getVarietyAvailability = useCallback(
    (varietyId, locationIds = selectedLocationIds) => {
      const summary = getVarietySummary(varietyId)
      if (!summary) {
        return {
          available: false,
          availableInAllLocations: false,
          matchingLocationIds: [],
        }
      }
      const normalizedLocationIds = Array.isArray(locationIds)
        ? locationIds.map((locationId) => String(locationId))
        : []
      const matchingLocationIds = normalizedLocationIds.filter((locationId) =>
        summary.locationIds.includes(locationId),
      )
      return {
        available: matchingLocationIds.length > 0,
        availableInAllLocations:
          normalizedLocationIds.length > 0 &&
          matchingLocationIds.length === normalizedLocationIds.length,
        matchingLocationIds,
      }
    },
    [getVarietySummary, selectedLocationIds],
  )

  const getMappedCount = useCallback(
    (varietyId, locationId = null) => {
      const rows = Array.isArray(form?.serviceRows) ? form.serviceRows : []
      return rows
        .filter((row) => {
          if (String(row.varietyId || '') !== String(varietyId)) return false
          if (!locationId) return true
          const effectiveLocationId =
            selectedLocationIds.length === 1 ? selectedLocationIds[0] : String(row.locationId || '')
          return String(effectiveLocationId) === String(locationId)
        })
        .reduce((sum, row) => sum + Number(row.serviceCount || 0), 0)
    },
    [form?.serviceRows, selectedLocationIds],
  )

  const getVarietyDisplaySummary = useCallback(
    (varietyId, locationId = null) => {
      const summary = getVarietySummary(varietyId)
      if (!summary) return null
      const effectiveLocationIds = locationId
        ? [String(locationId)]
        : summary.locationIds.filter((candidateId) => selectedLocationIds.includes(candidateId))
      const locationNames = getVarietyLocationNames(varietyId, effectiveLocationIds)
      const mappedCountByLocation = Object.fromEntries(
        effectiveLocationIds.map((candidateId) => [candidateId, getMappedCount(varietyId, candidateId)]),
      )
      return {
        ...summary,
        locationNames,
        locationNamesById: Object.fromEntries(
          summary.locationIds.map((candidateId) => [
            candidateId,
            locationNameMap[candidateId] || UNKNOWN_LOCATION_LABEL(candidateId),
          ]),
        ),
        mappedCountTotal: locationId
          ? getMappedCount(varietyId, locationId)
          : getMappedCount(varietyId),
        mappedCountByLocation,
        coverageLabel:
          summary.availableInAllLocations && selectedLocationIds.length > 1
            ? 'متاح في كل المواقع المختارة'
            : summary.locationIds.length > 0
              ? `متاح في: ${getVarietyLocationNames(varietyId, summary.locationIds).join('، ')}`
              : 'صنف عام غير مرتبط بموقع محدد',
      }
    },
    [
      getMappedCount,
      getVarietyLocationNames,
      getVarietySummary,
      locationNameMap,
      selectedLocationIds,
    ],
  )

  const addServiceRow = useCallback(() => {
    const singleLocationId = selectedLocationIds.length === 1 ? selectedLocationIds[0] : ''

    let autoServiceCount = ''
    if (singleLocationId && treeVarietySummaryRaw.length > 0) {
      const firstEntry = treeVarietySummaryRaw[0]
      const byLocation = firstEntry?.by_location || {}
      const locationData = byLocation[String(singleLocationId)]
      const inventoryCount = Number(
        locationData?.current_tree_count || locationData?.cohort_alive_total || 0
      )
      if (inventoryCount > 0) {
        autoServiceCount = String(inventoryCount)
      }
    }
    if (!autoServiceCount && treeVarietySummaryRaw.length === 1) {
      const total = Number(
        treeVarietySummaryRaw[0]?.current_tree_count_total ||
        treeVarietySummaryRaw[0]?.cohort_alive_total || 0
      )
      if (total > 0) autoServiceCount = String(total)
    }
    if (!autoServiceCount) autoServiceCount = '1'

    let autoVarietyId = ''
    const availableForLocation = singleLocationId
      ? treeVarietySummaryRaw.filter((entry) => {
          const byLocation = entry?.by_location || {}
          return Object.keys(byLocation).some((locId) => String(locId) === String(singleLocationId))
        })
      : treeVarietySummaryRaw
    if (availableForLocation.length === 1) {
      autoVarietyId = String(availableForLocation[0].variety_id || '')
    }

    const newRow = {
      key: uuidv4(),
      varietyId: autoVarietyId,
      locationId: singleLocationId,
      serviceCount: autoServiceCount,
      delta: '',
      harvestQty: '',
      lossReasonId: '',
      notes: '',
    }

    setForm((prev) => ({
      ...prev,
      serviceRows: [...(prev.serviceRows || []), newRow],
    }))
  }, [selectedLocationIds, setForm, treeVarietySummaryRaw])

  const removeServiceRow = useCallback(
    (rowKey) => {
      setForm((prev) => ({
        ...prev,
        serviceRows: (prev.serviceRows || []).filter((row) => row.key !== rowKey),
      }))
    },
    [setForm],
  )

  const updateServiceRow = useCallback(
    (rowKey, field, value) => {
      setForm((prev) => ({
        ...prev,
        serviceRows: (prev.serviceRows || []).map((row) => {
          if (row.key !== rowKey) return row
          const nextRow = { ...row, [field]: value }
          // [ZENITH 11.5] RELAXED POLICY: Do not wipe varietyId automatically if location changes.
          // Let validation handle it with a visible error instead of silent data loss.
          return nextRow
        }),
      }))
    },
    [setForm],
  )

  useEffect(() => {
    if (!Array.isArray(form?.serviceRows) || form.serviceRows.length === 0) return

    const singleLocationId = selectedLocationIds.length === 1 ? selectedLocationIds[0] : ''
    const selectedLocationSet = new Set(selectedLocationIds)

    setForm((prev) => {
      const rows = Array.isArray(prev.serviceRows) ? prev.serviceRows : []
      let changed = false
      const nextRows = rows.map((row) => {
        let nextRow = row
        const currentLocationId = row.locationId ? String(row.locationId) : ''

        if (singleLocationId && currentLocationId !== singleLocationId) {
          nextRow = { ...nextRow, locationId: singleLocationId }
          changed = true
        } else if (!singleLocationId && currentLocationId && !selectedLocationSet.has(currentLocationId)) {
          nextRow = { ...nextRow, locationId: '' }
          changed = true
        }

        // [AGRI-GUARDIAN] Self-Healing is dangerous during re-hydration or lookup race conditions.
        // We will rely on validatePerennialCompliance to show visible errors instead of silent wiping.
        // if (
        //   hasLoadedVarieties &&
        //   nextRow.varietyId &&
        //   effectiveLocationId &&
        //   !isVarietyAvailableInLocation(nextRow.varietyId, effectiveLocationId)
        // ) {
        //   nextRow = { ...nextRow, varietyId: '' }
        //   changed = true
        // }
        return nextRow
      })

      return changed ? { ...prev, serviceRows: nextRows } : prev
    })
  }, [form?.serviceRows, isVarietyAvailableInLocation, lookups, selectedLocationIds, setForm])

  const validatePerennialCompliance = useCallback(() => {
    const errors = {}
    const fallbackTask = Array.isArray(lookups?.tasks)
      ? lookups.tasks.find((task) => String(task.id) === String(form.task))
      : null
    const requiredInputs = taskContext?.requiredInputs || {
      requiresTreeCount: Boolean(fallbackTask?.requires_tree_count),
      isPerennialProcedure: Boolean(fallbackTask?.is_perennial_procedure),
    }
    const enabledCards = taskContext?.enabledCards || {}
    const isTreeTask = Boolean(
      enabledCards.perennial ||
        requiredInputs.requiresTreeCount ||
        requiredInputs.isPerennialProcedure,
    )

    if (!isTreeTask) return null

    const rows = form.serviceRows || []
    if (strictErpMode && rows.length === 0) {
      errors.serviceRows = 'يجب إضافة تفاصيل الخدمة لهذا النشاط الشجري'
    } else {
      rows.forEach((row, idx) => {
        const effectiveLocationId =
          selectedLocationIds.length === 1
            ? selectedLocationIds[0]
            : String(row.locationId || '')

        if (Number(row.delta) < 0 && !row.lossReasonId) {
          errors[`serviceRows[${idx}].lossReasonId`] = 'يجب تحديد سبب الفقد عند النقص'
        }

        if (selectedLocationIds.length > 1 && !effectiveLocationId) {
          errors[`serviceRows[${idx}].location`] = 'يجب تحديد الموقع لكل صف خدمة'
        }
        const parsedCount = Number(row.serviceCount)
        if (row.serviceCount === '' || row.serviceCount === null || row.serviceCount === undefined) {
          errors[`serviceRows[${idx}].count`] = 'يرجى إدخال عدد الأشجار المخدومة'
        } else if (!Number.isFinite(parsedCount) || parsedCount <= 0) {
          errors[`serviceRows[${idx}].count`] = 'عدد الأشجار يجب أن يكون أكبر من الصفر'
        }
        if (!row.varietyId) {
          errors[`serviceRows[${idx}].variety`] = 'يجب تحديد الصنف'
        }
        if (
          row.varietyId &&
          effectiveLocationId &&
          !isVarietyAvailableInLocation(row.varietyId, effectiveLocationId)
        ) {
          errors[`serviceRows[${idx}].variety`] =
            'الصنف المختار غير متاح في الموقع المحدد لهذا الصف'
        }

        if (row.varietyId && effectiveLocationId) {
          const current = getVarietyCount(row.varietyId, effectiveLocationId)
          const mappedCount = getMappedCount(row.varietyId, effectiveLocationId)
          const delta = Number(row.delta || form?.tree_count_delta || 0)

          if (current !== '?' && mappedCount > current && delta <= 0) {
            errors[`serviceRows[${idx}].variety`] =
              `إجمالي المخدوم لهذا الصنف يتجاوز المتوفر في الموقع المحدد (${current})`
          }
        }
      })
    }

    return Object.keys(errors).length > 0 ? errors : null
  }, [
    form,
    getMappedCount,
    getVarietyCount,
    isVarietyAvailableInLocation,
    lookups?.tasks,
    selectedLocationIds,
    strictErpMode,
    taskContext,
  ])

  const stats = useMemo(() => {
    const displaySummaries = perennialVarietySummary
      .map((summary) => getVarietyDisplaySummary(summary.varietyId))
      .filter(Boolean)

    return {
      totalServiced: (form.serviceRows || []).reduce(
        (sum, row) => sum + (Number(row.serviceCount) || 0),
        0,
      ),
      hasRows: (form.serviceRows || []).length > 0,
      perennialVarietySummary: displaySummaries,
      totalTreeCount: perennialVarietySummary.reduce(
        (sum, row) => sum + Number(row.currentTreeCountTotal || 0),
        0,
      ),
      totalCohortAlive: perennialVarietySummary.reduce(
        (sum, row) => sum + Number(row.cohortAliveTotal || 0),
        0,
      ),
      hasLocationAwareVarieties: displaySummaries.length > 0,
      emptyMessage:
        varietiesMeta.emptyReason ||
        (hasSelectedLocations
          ? 'لا توجد أصناف أشجار فعالة مرتبطة بالمواقع المختارة لهذا المحصول.'
          : 'لم يتم العثور على أصناف أشجار مرتبطة بالمواقع المختارة.'),
      usedFallback: Boolean(varietiesMeta.usedFallback),
      payloadDiagnostics: varietiesMeta.diagnostics || null,
      loadingSnapshot: false,
    }
  }, [
    form.serviceRows,
    getVarietyDisplaySummary,
    hasSelectedLocations,
    perennialVarietySummary,
    varietiesMeta,
  ])

  return {
    addServiceRow,
    removeServiceRow,
    updateServiceRow,
    validatePerennialCompliance,
    getVarietyAvailability,
    getVarietyCount,
    getVarietyLocationNames,
    getMappedCount,
    getVarietyDisplaySummary,
    isVarietyAvailableInLocation,
    stats,
  }
}
