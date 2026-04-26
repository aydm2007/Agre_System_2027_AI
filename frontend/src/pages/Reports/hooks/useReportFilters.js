import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { format, subDays } from 'date-fns'
import { api, CropVarieties, TreeProductivityStatuses, Seasons } from '../../../api/client'
import { TEXT } from '../constants'
import { logRuntimeError } from '../../../utils/runtimeLogger'

export const useReportFilters = (selectedFarmId) => {
  const [filters, setFilters] = useState({
    start: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
    end: format(new Date(), 'yyyy-MM-dd'),
    farm: selectedFarmId || '',
    location_id: '',
    crop_id: '',
    task_id: '',
    variety_id: '',
    status_code: '',
    season: '',
  })

  // Options State
  const [farms, setFarms] = useState([])
  const [locations, setLocations] = useState([])
  const [crops, setCrops] = useState([])
  const [tasks, setTasks] = useState([])
  const [varieties, setVarieties] = useState([])
  const [treeStatuses, setTreeStatuses] = useState([])
  const [seasons, setSeasons] = useState([])

  // Sync with context
  useEffect(() => {
    if (selectedFarmId && selectedFarmId !== 'all') {
      setFilters((prev) => ({ ...prev, farm: selectedFarmId }))
    }
  }, [selectedFarmId])

  // Load Initial Metadata (Seasons, Statuses, LossReasons, Farms)
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const [statusRes, seasonsRes, farmsRes] = await Promise.all([
          TreeProductivityStatuses.list(),
          Seasons.list({ is_active: true }),
          api.get('/farms/'),
        ])

        setTreeStatuses(
          Array.isArray(statusRes.data?.results || statusRes.data)
            ? statusRes.data?.results || statusRes.data
            : [],
        )
        // Loaded for backend compatibility checks; currently not rendered in filters UI.
        // Keep request to validate availability of tree metadata, but don't store unused state.
        setSeasons(
          Array.isArray(seasonsRes.data?.results || seasonsRes.data)
            ? seasonsRes.data?.results || seasonsRes.data
            : [],
        )
        setFarms(farmsRes.data.results || farmsRes.data || [])
      } catch (error) {
        logRuntimeError('REPORT_FILTER_METADATA_LOAD_FAILED', error)
        toast.error(TEXT.errors?.loadReport || 'تعذر تحميل بيانات المرشحات.')
      }
    }
    loadMetadata()
  }, [])

  // Load cascading filters: Farm -> Locations, Crops
  useEffect(() => {
    if (!filters.farm) {
      setLocations([])
      setCrops([])
      setVarieties([])
      setFilters((prev) => ({ ...prev, location_id: '', crop_id: '', task_id: '', variety_id: '' }))
      return
    }
    const loadFarmDependents = async () => {
      try {
        const [locRes, cropsRes] = await Promise.all([
          api.get('/locations/', { params: { farm_id: filters.farm } }),
          api.get('/crops/', { params: { farm_id: filters.farm } }),
        ])
        setLocations(locRes.data.results || locRes.data || [])
        setCrops(cropsRes.data.results || cropsRes.data || [])
      } catch (error) {
        logRuntimeError('REPORT_FILTER_FARM_DEPENDENTS_FAILED', error, { farm_id: filters.farm })
        toast.error(TEXT.errors.loadLocations || 'تعذر تحميل المواقع/المحاصيل.')
      }
    }
    loadFarmDependents()
  }, [filters.farm])

  // Load cascading filters: Crop -> Tasks, Varieties
  useEffect(() => {
    if (!filters.crop_id) {
      setTasks([])
      setVarieties([])
      setFilters((prev) => ({ ...prev, task_id: '', variety_id: '' }))
      return
    }
    const loadCropDependents = async () => {
      try {
        const varietyParams = { crop: filters.crop_id }
        if (filters.farm) varietyParams.farm_id = filters.farm

        const [tasksRes, varRes] = await Promise.all([
          api.get('/tasks/', { params: { crop: filters.crop_id } }),
          CropVarieties.list(varietyParams),
        ])
        setTasks(tasksRes.data.results || tasksRes.data || [])
        setVarieties(
          Array.isArray(varRes.data?.results || varRes.data)
            ? varRes.data?.results || varRes.data
            : [],
        )
      } catch (error) {
        logRuntimeError('REPORT_FILTER_CROP_DEPENDENTS_FAILED', error, { crop_id: filters.crop_id })
        toast.error(TEXT.errors.loadTasks || 'تعذر تحميل المهام/الأصناف.')
      }
    }
    loadCropDependents()
  }, [filters.crop_id, filters.farm])

  const handleFilterChange = (event) => {
    const { name, value } = event.target
    const normalizedValue = name === 'farm' && value === 'all' ? '' : value
    setFilters((prev) => {
      const next = { ...prev, [name]: normalizedValue }
      // Cascading clear
      if (name === 'farm') {
        next.location_id = ''
        next.crop_id = ''
        next.task_id = ''
        next.variety_id = ''
      }
      if (name === 'crop_id') {
        next.task_id = ''
        next.variety_id = ''
      }
      if (name === 'location_id' && value === '') {
        next.location_id = ''
      }
      return next
    })
  }

  return {
    filters,
    setFilters,
    handleFilterChange,
    farms,
    locations,
    crops,
    tasks,
    varieties,
    treeStatuses,
    seasons,
  }
}
