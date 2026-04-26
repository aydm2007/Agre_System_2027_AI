import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { toast } from 'react-hot-toast'

import { api, ExportJobs, TreeInventory, getFinancialRiskZone } from '../../../api/client'
import { logRuntimeError } from '../../../utils/runtimeLogger'
import { REPORT_SECTIONS, TEXT } from '../constants'
import { buildAdvancedReportParamsWithSections, buildTreeFilters } from '../reportParams'

const REPORT_PENDING_MESSAGE = 'التقرير قيد التجهيز، ستظهر النتائج فور اكتمال المعالجة.'
const REPORT_STALLED_MESSAGE = 'التقرير قيد التجهيز، تتم متابعة المهمة وإنعاشها تلقائيًا عند الحاجة.'

const DEFAULT_SELECTED_SECTIONS = REPORT_SECTIONS.filter((section) => section.defaultSelected).map(
  (section) => section.key,
)
const BASE_SECTIONS = new Set(['summary', 'activities', 'charts', 'detailed_tables'])

const EMPTY_SECTION_STATUS = REPORT_SECTIONS.reduce((acc, section) => {
  acc[section.key] = 'idle'
  return acc
}, {})

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const timerId = window.setTimeout(resolve, ms)
    if (signal) {
      signal.addEventListener(
        'abort',
        () => {
          window.clearTimeout(timerId)
          reject(new DOMException('Aborted', 'AbortError'))
        },
        { once: true },
      )
    }
  })

const buildFilterSignature = (filters = {}) =>
  JSON.stringify({
    start: filters.start || '',
    end: filters.end || '',
    farm: filters.farm || '',
    season: filters.season || '',
    location_id: filters.location_id || '',
    crop_id: filters.crop_id || '',
    task_id: filters.task_id || '',
    variety_id: filters.variety_id || '',
    status_code: filters.status_code || '',
  })

const normalizeSelectedSections = (sections = []) => {
  const normalized = Array.from(new Set(sections.filter(Boolean)))
  return normalized.includes('summary') ? normalized : ['summary', ...normalized]
}

const buildChartsPayload = (summary, activities) => {
  const materialChart =
    summary?.materials?.length
      ? {
          labels: summary.materials.map((item) => item.name || 'غير معروف'),
          datasets: [
            {
              label: 'إجمالي الكمية',
              data: summary.materials.map((item) => Number(item.total_qty || 0)),
              backgroundColor: 'rgba(22, 163, 74, 0.7)',
            },
          ],
        }
      : null

  const grouped = new Map()
  activities.forEach((act) => {
    const label = act.asset?.name || 'غير معروف'
    const current = grouped.get(label) || { hours: 0, fuel: 0, meter: 0 }
    current.hours += Number(act.machine_hours || 0)
    current.fuel += Number(act.fuel_consumed || 0)
    current.meter += Number(act.machine_meter_reading || 0)
    grouped.set(label, current)
  })
  const labels = Array.from(grouped.keys())
  const machineryChart = labels.length
    ? {
        labels,
        datasets: [
          {
            label: 'ساعات الآلة',
            data: labels.map((label) => Number(grouped.get(label).hours.toFixed(2))),
            backgroundColor: 'rgba(59, 130, 246, 0.7)',
          },
          {
            label: 'الوقود (لتر)',
            data: labels.map((label) => Number(grouped.get(label).fuel.toFixed(2))),
            backgroundColor: 'rgba(249, 115, 22, 0.7)',
          },
          {
            label: 'قراءة العداد',
            data: labels.map((label) => Number(grouped.get(label).meter.toFixed(2))),
            backgroundColor: 'rgba(16, 185, 129, 0.7)',
          },
        ],
      }
    : null

  return { materialChart, machineryChart }
}

export const useReportData = (filters) => {
  const [summary, setSummary] = useState(null)
  const [activities, setActivities] = useState([])
  const [treeSummary, setTreeSummary] = useState([])
  const [treeEvents, setTreeEvents] = useState([])
  const [riskData, setRiskData] = useState([])
  const [loading, setLoading] = useState(false)
  const [treeLoading, setTreeLoading] = useState(false)
  const [treeError, setTreeError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [exportJobs, setExportJobs] = useState([])
  const [exportTemplates, setExportTemplates] = useState([])
  const [reportRefreshing, setReportRefreshing] = useState(false)
  const [reportPendingMessage, setReportPendingMessage] = useState('')
  const [selectedSections, setSelectedSections] = useState(DEFAULT_SELECTED_SECTIONS)
  const [sectionStatusMap, setSectionStatusMap] = useState(EMPTY_SECTION_STATUS)

  const latestFiltersRef = useRef(filters)
  const latestSelectedSectionsRef = useRef(selectedSections)
  const initializedRef = useRef(false)
  const controllersRef = useRef({})
  const sectionCacheRef = useRef(new Map())

  useEffect(() => {
    latestFiltersRef.current = filters
  }, [filters])

  useEffect(() => {
    latestSelectedSectionsRef.current = selectedSections
  }, [selectedSections])

  const filterSignature = useMemo(() => buildFilterSignature(filters), [filters])

  const hasStaleSections = useMemo(
    () => Object.values(sectionStatusMap).includes('stale'),
    [sectionStatusMap],
  )

  const setSectionStatuses = useCallback((sectionKeys, status) => {
    setSectionStatusMap((prev) => {
      const next = { ...prev }
      sectionKeys.forEach((sectionKey) => {
        next[sectionKey] = status
      })
      return next
    })
  }, [])

  const cancelRequest = useCallback((key) => {
    const controller = controllersRef.current[key]
    if (controller) {
      controller.abort()
      delete controllersRef.current[key]
    }
  }, [])

  const cancelAllRequests = useCallback(() => {
    Object.keys(controllersRef.current).forEach((key) => {
      controllersRef.current[key]?.abort()
      delete controllersRef.current[key]
    })
  }, [])

  useEffect(() => () => cancelAllRequests(), [cancelAllRequests])

  const fetchJobPayload = useCallback(async (sectionScope, signal) => {
    const params = buildAdvancedReportParamsWithSections(latestFiltersRef.current, sectionScope)
    const requestResponse = await api.post('/advanced-report/requests/', params, { signal })
    const jobId = requestResponse?.data?.id
    setReportRefreshing(true)
    setReportPendingMessage(REPORT_PENDING_MESSAGE)

    let polling = true
    while (polling) {
      if (signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError')
      }
      const { data } = await api.get(`/advanced-report/requests/${jobId}/`, { signal })
      if (data.status === 'completed' && data.result_url) {
        const response = await fetch(new URL(data.result_url, window.location.origin), {
          credentials: 'include',
          signal,
        })
        if (!response.ok) {
          throw new Error(TEXT.errors.loadReport || 'تعذر تحميل التقرير.')
        }
        setReportPendingMessage('')
        setReportRefreshing(false)
        polling = false
        return response.json()
      }
      if (data.status === 'failed') {
        setReportPendingMessage('')
        setReportRefreshing(false)
        polling = false
        throw new Error(data.error_message || TEXT.export.failed)
      }
      setReportPendingMessage(data.stalled ? REPORT_STALLED_MESSAGE : REPORT_PENDING_MESSAGE)
      await sleep(data.stalled ? 2000 : 1500, signal)
    }
  }, [])

  const loadBaseReport = useCallback(
    async ({ sections, force = false }) => {
      const requestedSections = Array.from(new Set(sections.filter((section) => BASE_SECTIONS.has(section))))
      if (!requestedSections.length) return

      const summaryCacheKey = `${filterSignature}:summary`
      const detailsCacheKey = `${filterSignature}:details`
      if (!force && requestedSections.every((section) => sectionCacheRef.current.has(`${filterSignature}:${section}`))) {
        if (requestedSections.includes('summary')) {
          setSummary(sectionCacheRef.current.get(summaryCacheKey) || null)
        }
        if (requestedSections.some((section) => ['activities', 'charts', 'detailed_tables'].includes(section))) {
          setActivities(sectionCacheRef.current.get(detailsCacheKey) || [])
        }
        setSectionStatuses(requestedSections, 'ready')
        return
      }

      cancelRequest('base')
      const controller = new AbortController()
      controllersRef.current.base = controller
      setLoading(true)
      setSectionStatuses(requestedSections, 'loading')

      try {
        const payload = await fetchJobPayload(requestedSections, controller.signal)
        if (requestedSections.includes('summary')) {
          setSummary(payload.summary || null)
          sectionCacheRef.current.set(summaryCacheKey, payload.summary || null)
          sectionCacheRef.current.set(`${filterSignature}:summary`, payload.summary || null)
        }
        if (requestedSections.some((section) => ['activities', 'charts', 'detailed_tables'].includes(section))) {
          const nextDetails = Array.isArray(payload.details) ? payload.details : []
          setActivities(nextDetails)
          sectionCacheRef.current.set(detailsCacheKey, nextDetails)
          ;['activities', 'charts', 'detailed_tables'].forEach((sectionKey) => {
            sectionCacheRef.current.set(`${filterSignature}:${sectionKey}`, nextDetails)
          })
        }
        setSectionStatuses(requestedSections, 'ready')
      } catch (error) {
        if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') {
          return
        }
        logRuntimeError('REPORT_LOAD_FAILED', error, {
          farm_id: latestFiltersRef.current?.farm,
          section_scope: requestedSections,
        })
        setReportPendingMessage('')
        setSectionStatuses(requestedSections, 'error')
        toast.error(error?.message || TEXT.errors.loadReport || 'تعذر تحميل التقرير.')
      } finally {
        setLoading(false)
        setReportRefreshing(false)
        delete controllersRef.current.base
      }
    },
    [cancelRequest, fetchJobPayload, filterSignature, setSectionStatuses],
  )

  const loadRiskZone = useCallback(
    async ({ force = false } = {}) => {
      const cacheKey = `${filterSignature}:risk_zone`
      if (!force && sectionCacheRef.current.has(cacheKey)) {
        setRiskData(sectionCacheRef.current.get(cacheKey) || [])
        setSectionStatuses(['risk_zone'], 'ready')
        return
      }
      if (!latestFiltersRef.current?.farm || !latestFiltersRef.current?.crop_id) {
        setRiskData([])
        setSectionStatuses(['risk_zone'], 'idle')
        return
      }

      cancelRequest('risk_zone')
      const controller = new AbortController()
      controllersRef.current.risk_zone = controller
      setSectionStatuses(['risk_zone'], 'loading')

      try {
        const response = await getFinancialRiskZone(
          latestFiltersRef.current.farm,
          latestFiltersRef.current.crop_id,
          latestFiltersRef.current.season,
        )
        if (controller.signal.aborted) return
        const nextRiskData = Array.isArray(response?.results) ? response.results : response || []
        setRiskData(nextRiskData)
        sectionCacheRef.current.set(cacheKey, nextRiskData)
        setSectionStatuses(['risk_zone'], 'ready')
      } catch (error) {
        if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') return
        logRuntimeError('REPORT_RISK_DATA_LOAD_FAILED', error, {
          farm_id: latestFiltersRef.current?.farm,
          crop_id: latestFiltersRef.current?.crop_id,
        })
        setSectionStatuses(['risk_zone'], 'error')
      } finally {
        delete controllersRef.current.risk_zone
      }
    },
    [cancelRequest, filterSignature, setSectionStatuses],
  )

  const loadTreeSummary = useCallback(
    async ({ force = false } = {}) => {
      const cacheKey = `${filterSignature}:tree_summary`
      if (!force && sectionCacheRef.current.has(cacheKey)) {
        setTreeSummary(sectionCacheRef.current.get(cacheKey) || [])
        setSectionStatuses(['tree_summary'], 'ready')
        return
      }

      cancelRequest('tree_summary')
      const controller = new AbortController()
      controllersRef.current.tree_summary = controller
      setTreeLoading(true)
      setTreeError('')
      setSectionStatuses(['tree_summary'], 'loading')

      try {
        const response = await TreeInventory.summary(buildTreeFilters(latestFiltersRef.current))
        if (controller.signal.aborted) return
        const nextSummary = response?.data?.results || response?.data || []
        setTreeSummary(nextSummary)
        sectionCacheRef.current.set(cacheKey, nextSummary)
        setSectionStatuses(['tree_summary'], 'ready')
      } catch (error) {
        if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') return
        logRuntimeError('REPORT_TREE_SUMMARY_LOAD_FAILED', error, {
          farm_id: latestFiltersRef.current?.farm,
        })
        setTreeError(TEXT.treeSummary.noData)
        setSectionStatuses(['tree_summary'], 'error')
      } finally {
        setTreeLoading(false)
        delete controllersRef.current.tree_summary
      }
    },
    [cancelRequest, filterSignature, setSectionStatuses],
  )

  const loadTreeEvents = useCallback(
    async ({ force = false } = {}) => {
      const cacheKey = `${filterSignature}:tree_events`
      if (!force && sectionCacheRef.current.has(cacheKey)) {
        setTreeEvents(sectionCacheRef.current.get(cacheKey) || [])
        setSectionStatuses(['tree_events'], 'ready')
        return
      }

      cancelRequest('tree_events')
      const controller = new AbortController()
      controllersRef.current.tree_events = controller
      setTreeLoading(true)
      setTreeError('')
      setSectionStatuses(['tree_events'], 'loading')

      try {
        const response = await TreeInventory.events({
          ...buildTreeFilters(latestFiltersRef.current),
          from: latestFiltersRef.current.start,
          to: latestFiltersRef.current.end,
        })
        if (controller.signal.aborted) return
        const nextEvents = response?.data?.results || response?.data || []
        setTreeEvents(nextEvents)
        sectionCacheRef.current.set(cacheKey, nextEvents)
        setSectionStatuses(['tree_events'], 'ready')
      } catch (error) {
        if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') return
        logRuntimeError('REPORT_TREE_EVENTS_LOAD_FAILED', error, {
          farm_id: latestFiltersRef.current?.farm,
        })
        setTreeError(TEXT.treeEvents.noData)
        setSectionStatuses(['tree_events'], 'error')
      } finally {
        setTreeLoading(false)
        delete controllersRef.current.tree_events
      }
    },
    [cancelRequest, filterSignature, setSectionStatuses],
  )

  const loadSection = useCallback(
    async (sectionKey, { force = false } = {}) => {
      if (BASE_SECTIONS.has(sectionKey)) {
        const nextBaseSections = normalizeSelectedSections(selectedSections).filter((section) =>
          BASE_SECTIONS.has(section),
        )
        await loadBaseReport({ sections: nextBaseSections, force })
        return
      }
      if (sectionKey === 'risk_zone') {
        await loadRiskZone({ force })
        return
      }
      if (sectionKey === 'tree_summary') {
        await loadTreeSummary({ force })
        return
      }
      if (sectionKey === 'tree_events') {
        await loadTreeEvents({ force })
      }
    },
    [loadBaseReport, loadRiskZone, loadTreeEvents, loadTreeSummary, selectedSections],
  )

  const loadSelectedSections = useCallback(
    async ({ force = false } = {}) => {
      const activeSections = normalizeSelectedSections(selectedSections)
      const promises = []
      const baseSections = activeSections.filter((section) => BASE_SECTIONS.has(section))
      if (baseSections.length) {
        promises.push(loadBaseReport({ sections: baseSections, force }))
      }
      if (activeSections.includes('risk_zone')) {
        promises.push(loadRiskZone({ force }))
      }
      if (activeSections.includes('tree_summary')) {
        promises.push(loadTreeSummary({ force }))
      }
      if (activeSections.includes('tree_events')) {
        promises.push(loadTreeEvents({ force }))
      }
      await Promise.all(promises)
    },
    [loadBaseReport, loadRiskZone, loadTreeEvents, loadTreeSummary, selectedSections],
  )

  const refreshSelectedSections = useCallback(() => loadSelectedSections({ force: true }), [loadSelectedSections])

  const toggleSection = useCallback(
    (sectionKey) => {
      if (sectionKey === 'summary') return
      setSelectedSections((prev) => {
        const next = prev.includes(sectionKey)
          ? prev.filter((item) => item !== sectionKey)
          : normalizeSelectedSections([...prev, sectionKey])
        return next
      })
      setSectionStatusMap((prev) => ({
        ...prev,
        [sectionKey]: prev[sectionKey] === 'stale' ? 'stale' : 'idle',
      }))
    },
    [],
  )

  useEffect(() => {
    if (!initializedRef.current) return
    const activeSections = normalizeSelectedSections(selectedSections)
    const pendingLoads = activeSections.filter((sectionKey) => {
      if (sectionKey === 'risk_zone') {
        return latestFiltersRef.current?.farm && latestFiltersRef.current?.crop_id
      }
      return true
    })
    pendingLoads.forEach((sectionKey) => {
      if (sectionStatusMap[sectionKey] === 'idle') {
        void loadSection(sectionKey, { force: false })
      }
    })
  }, [loadSection, sectionStatusMap, selectedSections])

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true
      void loadBaseReport({ sections: ['summary'], force: true })
      return
    }

    setSectionStatusMap((prev) => {
      const next = { ...prev, summary: 'idle' }
      normalizeSelectedSections(latestSelectedSectionsRef.current).forEach((sectionKey) => {
        if (sectionKey !== 'summary') {
          next[sectionKey] = 'stale'
        }
      })
      return next
    })
    void loadBaseReport({ sections: ['summary'], force: true })
  }, [filterSignature, loadBaseReport])

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const [templatesResponse, jobsResponse] = await Promise.all([
          ExportJobs.templates({
            farm_id: filters.farm || '',
            ui_surface: 'reports_hub',
          }),
          ExportJobs.list({
            farm_id: filters.farm || '',
            limit: 8,
          }),
        ])
        if (!active) return
        setExportTemplates(templatesResponse?.data?.results || [])
        setExportJobs(jobsResponse?.data?.results || [])
      } catch (error) {
        if (active) {
          logRuntimeError('REPORT_EXPORT_CATALOG_LOAD_FAILED', error, { farm_id: filters.farm })
        }
      }
    })()
    return () => {
      active = false
    }
  }, [filters.farm])

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  const pollExportJob = async (jobId) => {
    const maxAttempts = 16
    const delayMs = 1500
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const { data } = await ExportJobs.status(jobId)
      setExportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 5))
      if (data.status === 'completed') return data
      if (data.status === 'failed') {
        throw new Error(data.error_message || TEXT.export.failed)
      }
      await sleep(delayMs)
    }
    throw new Error(TEXT.export.timeout)
  }

  const handleExport = async (selection = 'xlsx') => {
    setExporting(true)
    const toastId = toast.loading(TEXT.export.pending)
    try {
      const exportType = typeof selection === 'string' ? 'advanced_report' : selection.exportType
      const format = typeof selection === 'string' ? selection : selection.format
      const response = await ExportJobs.create({
        ...buildAdvancedReportParamsWithSections(filters, selectedSections),
        export_type: exportType,
        format,
        locale: 'ar-YE',
        rtl: true,
        section_scope: selectedSections,
      })
      const job = response.data
      setExportJobs((prev) => [job, ...prev.filter((entry) => entry.id !== job.id)].slice(0, 5))
      const readyReport = await pollExportJob(job.id)
      const downloadResponse = await ExportJobs.download(readyReport.id)
      const filename =
        readyReport.output_filename ||
        `${exportType}-${filters.start || 'latest'}-${filters.end || 'latest'}.${format}`
      downloadBlob(downloadResponse.data, filename)
      toast.success(TEXT.export.success, { id: toastId })
    } catch (error) {
      toast.error(error?.message || TEXT.export.failed, { id: toastId })
    } finally {
      setExporting(false)
    }
  }

  const treeTotals = useMemo(() => {
    const totals = { total: 0, status: {} }
    treeSummary.forEach((item) => {
      const count = Number(item?.current_tree_count ?? 0)
      totals.total += count
      const code = item?.productivity_status?.code || item?.productivity_status_code || 'unknown'
      totals.status[code] = (totals.status[code] || 0) + count
    })
    return totals
  }, [treeSummary])

  const { materialChart, machineryChart } = useMemo(
    () => buildChartsPayload(summary, activities),
    [activities, summary],
  )

  const sectionDataMap = useMemo(
    () => ({
      summary,
      activities,
      charts: { materialChart, machineryChart },
      tree_summary: treeSummary,
      tree_events: treeEvents,
      risk_zone: riskData,
      detailed_tables: { summary, activities },
    }),
    [activities, machineryChart, materialChart, riskData, summary, treeEvents, treeSummary],
  )

  const dataSourceMap = useMemo(
    () => ({
      summary: 'async_request',
      activities: 'async_request',
      charts: 'async_request',
      detailed_tables: 'async_request',
      risk_zone: 'direct_api',
      tree_summary: 'direct_api',
      tree_events: 'direct_api',
    }),
    [],
  )

  return {
    summary,
    activities,
    treeSummary,
    treeEvents,
    loading,
    treeLoading,
    treeError,
    riskData,
    exporting,
    exportTemplates,
    fetchReport: refreshSelectedSections,
    handleExport,
    exportJobs,
    treeTotals,
    materialChart,
    machineryChart,
    reportPendingMessage,
    reportRefreshing,
    selectedSections,
    setSelectedSections,
    sectionDataMap,
    dataSourceMap,
    sectionStatusMap,
    hasStaleSections,
    loadSelectedSections,
    refreshSelectedSections,
    toggleSection,
  }
}
