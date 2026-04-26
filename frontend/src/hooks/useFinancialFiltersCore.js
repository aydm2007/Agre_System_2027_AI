import { useState, useEffect, useCallback, useMemo, useRef } from 'react'

export const DIM = {
  farm: 'farm',
  location: 'location',
  costCenter: 'costCenter',
  cropPlan: 'crop_plan',
  activity: 'activity',
  crop: 'crop',
  period: 'period',
}

const CASCADE_ORDER = [
  DIM.farm,
  DIM.location,
  DIM.costCenter,
  DIM.cropPlan,
  DIM.activity,
  DIM.crop,
  DIM.period,
]

const LEGACY_DIM_ALIASES = {
  cropPlan: DIM.cropPlan,
}

const FILTER_OPTION_PAGE_SIZE = 500

export const formatActivityOptionLabel = (activity) => {
  const primaryLabel =
    activity.name || activity.task_name || activity.task?.name || activity.task?.name_ar || ''

  const locationLabel =
    activity.location_name ||
    activity.location?.name ||
    activity.locations?.[0]?.name ||
    activity.locations?.[0]?.name_ar ||
    ''

  const dateLabel = activity.log_date || activity.date || ''
  const secondaryParts = [dateLabel, locationLabel].filter(Boolean)

  if (primaryLabel && secondaryParts.length) return `${primaryLabel} - ${secondaryParts.join(' - ')}`
  if (primaryLabel) return primaryLabel
  if (secondaryParts.length) return secondaryParts.join(' - ')
  return `Activity ${activity.id}`
}

export const normalizeDimensions = (inputDimensions = ['farm']) =>
  inputDimensions.map((dim) => LEGACY_DIM_ALIASES[dim] || dim)

const buildDimensionsKey = (inputDimensions = ['farm']) =>
  normalizeDimensions(inputDimensions).join('|')

const buildListFingerprint = (items = []) =>
  (Array.isArray(items) ? items : [])
    .map((item) => {
      if (item === null || item === undefined) return 'null'
      if (typeof item !== 'object') return String(item)
      return [
        item.id ?? '',
        item.name ?? '',
        item.name_ar ?? '',
        item.code ?? '',
        item.title ?? '',
        item.status ?? '',
        item.updated_at ?? '',
        item.log_date ?? '',
        item.task_name ?? '',
        item.location_name ?? '',
      ].join('::')
    })
    .join('|')

export const buildInitialFilters = ({
  dimensions,
  syncToUrl = false,
  searchParams = null,
  autoSelectFarm = true,
  selectedFarmId = '',
}) => {
  const initial = {}
  for (const dim of CASCADE_ORDER) {
    if (dimensions.includes(dim)) initial[dim] = (syncToUrl && searchParams?.get(dim)) || ''
  }
  if (autoSelectFarm && dimensions.includes(DIM.farm) && selectedFarmId && !initial[DIM.farm]) {
    initial[DIM.farm] = selectedFarmId
  }
  return initial
}

export const cascadeNextFilters = (previous, key, value) => {
  const next = { ...previous, [key]: value }
  const idx = CASCADE_ORDER.indexOf(key)
  if (idx >= 0) {
    for (let i = idx + 1; i < CASCADE_ORDER.length; i += 1) {
      if (next[CASCADE_ORDER[i]] !== undefined) next[CASCADE_ORDER[i]] = ''
    }
  }
  return next
}

export const buildOptions = ({
  farms = [],
  locationOptions = [],
  costCenterOptions = [],
  cropPlanOptions = [],
  activityOptions = [],
  cropOptions = [],
}) => {
  const farmOptions = (farms || []).map((farm) => ({ value: String(farm.id), label: farm.name }))
  return {
    farm: farmOptions,
    location: locationOptions.map((l) => ({
      value: String(l.id),
      label: l.name || l.name_ar || `Location ${l.id}`,
    })),
    costCenter: costCenterOptions.map((cc) => ({
      value: String(cc.id),
      label: cc.name || cc.code || `Cost Center ${cc.id}`,
    })),
    crop_plan: cropPlanOptions.map((p) => ({
      value: String(p.id),
      label: p.name || p.title || `Plan ${p.id}`,
    })),
    cropPlan: cropPlanOptions.map((p) => ({
      value: String(p.id),
      label: p.name || p.title || `Plan ${p.id}`,
    })),
    activity: activityOptions.map((activity) => ({
      value: String(activity.id),
      label: formatActivityOptionLabel(activity),
    })),
    crop: cropOptions.map((c) => ({
      value: String(c.id),
      label: c.name_ar || c.name || `Crop ${c.id}`,
    })),
  }
}

export function createUseFinancialFilters({ api, useFarmContext, useSearchParamsHook }) {
  return function useFinancialFilters({
    dimensions: inputDimensions = ['farm'],
    syncToUrl = false,
    autoSelectFarm = true,
  } = {}) {
    const { farms, selectedFarmId } = useFarmContext()
    const dimensionsKey = useMemo(() => buildDimensionsKey(inputDimensions), [inputDimensions])
    const dimensions = useMemo(
      () => (dimensionsKey ? dimensionsKey.split('|') : []),
      [dimensionsKey],
    )
    const hasFarmDimension = dimensions.includes(DIM.farm)
    const hasLocationDimension = dimensions.includes(DIM.location)
    const hasCostCenterDimension = dimensions.includes(DIM.costCenter)
    const hasCropPlanDimension = dimensions.includes(DIM.cropPlan)
    const hasActivityDimension = dimensions.includes(DIM.activity)
    const hasCropDimension = dimensions.includes(DIM.crop)

    const [urlSearchParams, setUrlSearchParams] = useSearchParamsHook()
    const searchParams = syncToUrl ? urlSearchParams : null
    const setSearchParams = syncToUrl ? setUrlSearchParams : null

    const initFilters = useCallback(
      () =>
        buildInitialFilters({
          dimensions,
          syncToUrl,
          searchParams,
          autoSelectFarm,
          selectedFarmId,
        }),
      [dimensions, syncToUrl, searchParams, selectedFarmId, autoSelectFarm],
    )

    const [filters, setFilters] = useState(initFilters)
    const [locationOptions, setLocationOptions] = useState([])
    const [costCenterOptions, setCostCenterOptions] = useState([])
    const [cropPlanOptions, setCropPlanOptions] = useState([])
    const [activityOptions, setActivityOptions] = useState([])
    const [cropOptions, setCropOptions] = useState([])
    const [loadingOptions, setLoadingOptions] = useState({})
    const activeFarmRef = useRef(filters[DIM.farm])

    useEffect(() => {
      if (autoSelectFarm && hasFarmDimension && selectedFarmId && !filters[DIM.farm]) {
        setFilters((prev) => ({ ...prev, [DIM.farm]: selectedFarmId }))
      }
    }, [selectedFarmId, autoSelectFarm, hasFarmDimension, filters]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!hasLocationDimension && !hasCropPlanDimension) return
      const farmId = filters[DIM.farm]
      activeFarmRef.current = farmId
      if (!farmId) {
        setLocationOptions([])
        return
      }
      let cancelled = false
      setLoadingOptions((prev) => ({ ...prev, location: true }))
      api
        .get('/locations/', { params: { farm_id: farmId, page_size: FILTER_OPTION_PAGE_SIZE } })
        .then((res) => {
          if (cancelled || activeFarmRef.current !== farmId) return
          const nextOptions = res.data?.results || res.data || []
          setLocationOptions((prev) =>
            buildListFingerprint(prev) === buildListFingerprint(nextOptions) ? prev : nextOptions,
          )
        })
        .catch(() => setLocationOptions([]))
        .finally(() => {
          if (!cancelled) setLoadingOptions((prev) => ({ ...prev, location: false }))
        })
      return () => {
        cancelled = true
      }
    }, [filters[DIM.farm], hasLocationDimension, hasCropPlanDimension]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!hasCostCenterDimension) return
      const farmId = filters[DIM.farm]
      if (!farmId) {
        setCostCenterOptions([])
        return
      }
      let cancelled = false
      setLoadingOptions((prev) => ({ ...prev, costCenter: true }))
      api
        .get('/finance/cost-centers/', {
          params: { farm_id: farmId, page_size: FILTER_OPTION_PAGE_SIZE },
        })
        .then((res) => {
          if (cancelled) return
          const nextOptions = res.data?.results || res.data || []
          setCostCenterOptions((prev) =>
            buildListFingerprint(prev) === buildListFingerprint(nextOptions) ? prev : nextOptions,
          )
        })
        .catch(() => setCostCenterOptions([]))
        .finally(() => {
          if (!cancelled) setLoadingOptions((prev) => ({ ...prev, costCenter: false }))
        })
      return () => {
        cancelled = true
      }
    }, [filters[DIM.farm], hasCostCenterDimension]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!hasCropPlanDimension) return
      const farmId = filters[DIM.farm]
      const locationId = filters[DIM.location]
      if (!farmId) {
        setCropPlanOptions([])
        return
      }
      let cancelled = false
      setLoadingOptions((prev) => ({ ...prev, cropPlan: true }))
      const params = { farm_id: farmId, page_size: FILTER_OPTION_PAGE_SIZE }
      if (locationId) params.location_id = locationId
      api
        .get('/crop-plans/', { params })
        .then((res) => {
          if (cancelled) return
          const nextOptions = res.data?.results || res.data || []
          setCropPlanOptions((prev) =>
            buildListFingerprint(prev) === buildListFingerprint(nextOptions) ? prev : nextOptions,
          )
        })
        .catch(() => setCropPlanOptions([]))
        .finally(() => {
          if (!cancelled) setLoadingOptions((prev) => ({ ...prev, cropPlan: false }))
        })
      return () => {
        cancelled = true
      }
    }, [filters[DIM.farm], filters[DIM.location], hasCropPlanDimension]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!hasActivityDimension) return
      const farmId = filters[DIM.farm]
      const locationId = filters[DIM.location]
      const cropPlanId = filters[DIM.cropPlan]
      if (!farmId || !cropPlanId) {
        setActivityOptions([])
        return
      }
      let cancelled = false
      setLoadingOptions((prev) => ({ ...prev, activity: true }))
      const params = { farm_id: farmId, crop_plan_id: cropPlanId, page_size: FILTER_OPTION_PAGE_SIZE }
      if (locationId) params.location_id = locationId
      api
        .get('/activities/', { params })
        .then((res) => {
          if (cancelled) return
          const nextOptions = res.data?.results || res.data || []
          setActivityOptions((prev) =>
            buildListFingerprint(prev) === buildListFingerprint(nextOptions) ? prev : nextOptions,
          )
        })
        .catch(() => setActivityOptions([]))
        .finally(() => {
          if (!cancelled) setLoadingOptions((prev) => ({ ...prev, activity: false }))
        })
      return () => {
        cancelled = true
      }
    }, [filters[DIM.farm], filters[DIM.location], filters[DIM.cropPlan], hasActivityDimension]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!hasCropDimension) return
      const farmId = filters[DIM.farm]
      const cropPlanId = filters[DIM.cropPlan]
      if (!farmId) {
        setCropOptions([])
        return
      }
      let cancelled = false
      setLoadingOptions((prev) => ({ ...prev, crop: true }))
      const params = { farm_id: farmId, page_size: FILTER_OPTION_PAGE_SIZE }
      if (cropPlanId) params.crop_plan_id = cropPlanId
      api
        .get('/crops/', { params })
        .then((res) => {
          if (cancelled) return
          const nextOptions = res.data?.results || res.data || []
          setCropOptions((prev) =>
            buildListFingerprint(prev) === buildListFingerprint(nextOptions) ? prev : nextOptions,
          )
        })
        .catch(() => setCropOptions([]))
        .finally(() => {
          if (!cancelled) setLoadingOptions((prev) => ({ ...prev, crop: false }))
        })
      return () => {
        cancelled = true
      }
    }, [filters[DIM.farm], filters[DIM.cropPlan], hasCropDimension]) // eslint-disable-line react-hooks/exhaustive-deps

    const setFilter = useCallback((key, value) => {
      setFilters((prev) => cascadeNextFilters(prev, key, value))
    }, [])

    const resetFilters = useCallback(() => {
      const reset = {}
      for (const dim of CASCADE_ORDER) {
        if (dimensions.includes(dim)) reset[dim] = ''
      }
      if (autoSelectFarm && hasFarmDimension && selectedFarmId) {
        reset[DIM.farm] = selectedFarmId
      }
      setFilters(reset)
    }, [dimensions, selectedFarmId, autoSelectFarm, hasFarmDimension])

    useEffect(() => {
      if (!syncToUrl || !setSearchParams) return
      const params = new URLSearchParams()
      for (const [k, v] of Object.entries(filters)) {
        if (v) params.set(k, v)
      }
      setSearchParams(params, { replace: true })
    }, [filters, syncToUrl, setSearchParams])

    const filterParams = useMemo(() => {
      const params = {}
      for (const [k, v] of Object.entries(filters)) {
        if (v) params[k] = v
      }
      return params
    }, [filters])

    const options = useMemo(
      () =>
        buildOptions({
          farms,
          locationOptions,
          costCenterOptions,
          cropPlanOptions,
          activityOptions,
          cropOptions,
        }),
      [farms, locationOptions, costCenterOptions, cropPlanOptions, activityOptions, cropOptions],
    )

    const loading = useMemo(
      () => ({
        ...loadingOptions,
        crop_plan: loadingOptions.cropPlan ?? false,
        cropPlan: loadingOptions.cropPlan ?? false,
        activity: loadingOptions.activity ?? false,
      }),
      [loadingOptions],
    )

    return {
      filters,
      options,
      loading,
      setFilter,
      resetFilters,
      filterParams,
      dimensions,
    }
  }
}
