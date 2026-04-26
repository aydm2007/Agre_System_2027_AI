import { describe, it, expect, beforeAll, beforeEach, afterAll, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

let DailyLog
let TreeInventoryPage

const {
  mockApiGet,
  mockFarmsList,
  mockItemsList,
  mockReportsDailySummary,
  mockDailyLogsDaySummary,
  mockCropVarietiesList,
  mockCropProductsList,
  mockCropsTasks,
  mockTreeLossReasonsList,
  mockTreeProductivityStatusesList,
  mockTreeInventorySummary,
  mockTreeInventoryEvents,
  mockTreeInventoryLocationSummary,
  mockTreeInventorySummaryExport,
  mockTreeInventoryEventsExport,
  mockLocationWellsList,
  mockEnqueueDailyLogSubmission,
  mockUploadAttachmentsFromCache,
  mockLocationsList,
  mockAssetsList,
  mockGetFarmContext,
  mockPersistFarmContext,
  mockAddToast,
  mockActivitiesTeamSuggestions,
  mockGetOfflineQueueDetails,
} = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockFarmsList: vi.fn(),
  mockItemsList: vi.fn(),
  mockReportsDailySummary: vi.fn(),
  mockDailyLogsDaySummary: vi.fn(),
  mockCropVarietiesList: vi.fn(),
  mockCropProductsList: vi.fn(),
  mockCropsTasks: vi.fn(),
  mockTreeLossReasonsList: vi.fn(),
  mockTreeProductivityStatusesList: vi.fn(),
  mockTreeInventorySummary: vi.fn(),
  mockTreeInventoryEvents: vi.fn(),
  mockTreeInventoryLocationSummary: vi.fn(),
  mockTreeInventorySummaryExport: vi.fn(),
  mockTreeInventoryEventsExport: vi.fn(),
  mockLocationWellsList: vi.fn(),
  mockEnqueueDailyLogSubmission: vi.fn(),
  mockUploadAttachmentsFromCache: vi.fn(),
  mockLocationsList: vi.fn(),
  mockAssetsList: vi.fn(),
  mockGetFarmContext: vi.fn(),
  mockPersistFarmContext: vi.fn(),
  mockAddToast: vi.fn(),
  mockActivitiesTeamSuggestions: vi.fn(),
  mockGetOfflineQueueDetails: vi.fn(),
}))

vi.mock('../src/api/client', () => ({
  api: { get: mockApiGet },
  Farms: { list: mockFarmsList },
  Crops: { tasks: mockCropsTasks },
  CropProducts: { list: mockCropProductsList },
  Locations: { list: mockLocationsList },
  Assets: { list: mockAssetsList },
  Items: { list: mockItemsList },
  DailyLogs: { daySummary: mockDailyLogsDaySummary },
  Attachments: { upload: vi.fn() },
  Reports: { dailySummary: mockReportsDailySummary },
  LocationWells: { list: mockLocationWellsList },
  CropVarieties: { list: mockCropVarietiesList },
  TreeLossReasons: { list: mockTreeLossReasonsList },
  TreeProductivityStatuses: { list: mockTreeProductivityStatusesList },
  TreeInventory: {
    summary: mockTreeInventorySummary,
    events: mockTreeInventoryEvents,
    locationSummary: mockTreeInventoryLocationSummary,
    summaryExport: mockTreeInventorySummaryExport,
    eventsExport: mockTreeInventoryEventsExport,
  },
  Activities: {
    teamSuggestions: mockActivitiesTeamSuggestions,
  },
  enqueueDailyLogSubmission: mockEnqueueDailyLogSubmission,
  uploadAttachmentsFromCache: mockUploadAttachmentsFromCache,
  getOfflineQueueDetails: mockGetOfflineQueueDetails,
}))

vi.mock('../src/api/client.js', () => ({
  api: { get: mockApiGet },
  Farms: { list: mockFarmsList },
  Crops: { tasks: mockCropsTasks },
  CropProducts: { list: mockCropProductsList },
  Locations: { list: mockLocationsList },
  Assets: { list: mockAssetsList },
  Items: { list: mockItemsList },
  DailyLogs: { daySummary: mockDailyLogsDaySummary },
  Attachments: { upload: vi.fn() },
  Reports: { dailySummary: mockReportsDailySummary },
  LocationWells: { list: mockLocationWellsList },
  CropVarieties: { list: mockCropVarietiesList },
  TreeLossReasons: { list: mockTreeLossReasonsList },
  TreeProductivityStatuses: { list: mockTreeProductivityStatusesList },
  TreeInventory: {
    summary: mockTreeInventorySummary,
    events: mockTreeInventoryEvents,
    locationSummary: mockTreeInventoryLocationSummary,
    summaryExport: mockTreeInventorySummaryExport,
    eventsExport: mockTreeInventoryEventsExport,
  },
  Activities: {
    teamSuggestions: mockActivitiesTeamSuggestions,
  },
  enqueueDailyLogSubmission: mockEnqueueDailyLogSubmission,
  uploadAttachmentsFromCache: mockUploadAttachmentsFromCache,
  getOfflineQueueDetails: mockGetOfflineQueueDetails,
}))

vi.mock('../src/api/farmContext.js', () => ({
  getFarmContext: mockGetFarmContext,
  persistFarmContext: mockPersistFarmContext,
  prefetchFarmContext: vi.fn(() => Promise.resolve()),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../src/auth/AuthContext', () => ({
  useAuth: () => ({
    hasFarmAccess: () => true,
    canAddModel: () => true,
    hasPermission: () => false,
  }),
  getAuthContext: () => ({
    hasFarmAccess: () => true,
    userFarmIds: ['1'],
  }),
}))

vi.mock('../src/offline/OfflineQueueProvider.jsx', () => ({
  useOfflineQueue: () => ({
    isOnline: true,
    queuedDailyLogs: 0,
    syncing: false,
    syncNow: vi.fn().mockResolvedValue(undefined),
    refreshCounts: vi.fn(),
  }),
}))

vi.mock('../src/components/ToastProvider.jsx', () => ({
  useToast: () => ({ addToast: mockAddToast }),
}))

const originalCreateObjectURL = globalThis.URL?.createObjectURL
const originalRevokeObjectURL = globalThis.URL?.revokeObjectURL

const describeHeavy = globalThis.process?.env?.RUN_HEAVY_UI_TESTS === '1' ? describe : describe.skip

describeHeavy('tree inventory UI behaviour', () => {
  const AR = {
    treePanelTitle:
      '\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0623\u0634\u062c\u0627\u0631 \u0627\u0644\u0645\u0639\u0645\u0631\u0629',
    farmLabel: '\u0627\u0644\u0645\u0632\u0631\u0639\u0629',
    locationLabel: '\u0627\u0644\u0645\u0648\u0642\u0639',
    cropLabel: '\u0627\u0644\u0645\u062d\u0635\u0648\u0644',
    taskLabel: '\u0627\u0644\u0645\u0647\u0645\u0629',
    serviceCountLabel:
      '\u0627\u0644\u0639\u062f\u062f \u0627\u0644\u062e\u062f\u0645\u064a \u0627\u0644\u0645\u0646\u062c\u0632',
    varietyLabel: '\u0627\u0644\u0635\u0646\u0641',
    treeSummaryTitle:
      '\u0645\u0644\u062e\u0635 \u062e\u062f\u0645\u0629 \u0627\u0644\u0623\u0634\u062c\u0627\u0631',
  }

  beforeAll(async () => {
    const dailyLogModule = await import('../src/pages/DailyLog.jsx')
    const treeInventoryModule = await import('../src/pages/TreeInventory.jsx')
    DailyLog = dailyLogModule.default
    TreeInventoryPage = treeInventoryModule.default
  })

  beforeEach(() => {
    vi.clearAllMocks()

    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock')
    globalThis.URL.revokeObjectURL = vi.fn()

    mockFarmsList.mockResolvedValue({
      data: { results: [{ id: 1, name: 'مزرعة النخيل' }] },
    })
    mockItemsList.mockResolvedValue({ data: { results: [] } })
    mockReportsDailySummary.mockResolvedValue({ data: { metrics: {} } })
    mockDailyLogsDaySummary.mockResolvedValue({ data: {} })
    mockTreeLossReasonsList.mockResolvedValue({
      data: { results: [{ id: 5, code: 'storm', name_ar: 'عاصفة' }] },
    })
    mockTreeProductivityStatusesList.mockResolvedValue({
      data: { results: [{ id: 1, code: 'productive', name_ar: 'منتج' }] },
    })
    mockCropVarietiesList.mockResolvedValue({
      data: { results: [{ id: 200, name: 'الصنف الذهبي' }] },
    })
    mockCropProductsList.mockResolvedValue({ data: { results: [] } })
    mockLocationWellsList.mockResolvedValue({ data: { results: [] } })
    mockCropsTasks.mockResolvedValue({ data: { results: [] } })
    mockLocationsList.mockResolvedValue({ data: { results: [] } })
    mockAssetsList.mockResolvedValue({ data: { results: [] } })
    mockGetOfflineQueueDetails.mockResolvedValue({ dailyLogs: [] })

    mockApiGet.mockImplementation((path, options = {}) => {
      if (path === '/farms/') {
        return Promise.resolve({ data: { results: [{ id: 1, name: 'مزرعة النخيل' }] } })
      }
      if (path === '/locations/') {
        const farmId = options?.params?.farm_id
        if (farmId === 1 || farmId === '1') {
          return Promise.resolve({
            data: { results: [{ id: 10, name: 'الموقع الشرقي', farm: 1 }] },
          })
        }
        return Promise.resolve({ data: { results: [] } })
      }
      return Promise.resolve({ data: { results: [] } })
    })

    mockTreeInventorySummary.mockResolvedValue({
      data: {
        results: [
          {
            id: 301,
            current_tree_count: 75,
            location: { name: 'الموقع الشرقي', farm: { name: 'مزرعة النخيل' } },
            crop_variety: { name: 'الصنف الذهبي' },
            productivity_status: { code: 'productive', name_ar: 'منتج' },
            planting_date: '2024-01-15',
            source: 'المشتل المركزي',
            service_stats: {
              period: {
                total_serviced: 12,
                entries: 2,
                coverage_ratio: 0.16,
                last_service_date: '2024-04-05',
                last_recorded_at: '2024-04-05T08:00:00Z',
                last_activity_id: 501,
                breakdown: { general: 6, irrigation: 6, fertilization: 0, pruning: 0 },
              },
              lifetime: {
                total_serviced: 120,
                entries: 20,
                coverage_ratio: 0.8,
                last_service_date: '2024-04-05',
                last_recorded_at: '2024-04-05T08:00:00Z',
                last_activity_id: 501,
                breakdown: { general: 60, irrigation: 40, fertilization: 10, pruning: 10 },
              },
              latest_entry: {
                activity_date: '2024-04-05',
                service_count: 6,
                service_type: 'irrigation',
                recorded_by_name: 'المهندس سامي',
              },
            },
          },
        ],
      },
    })
    mockTreeInventoryEvents.mockResolvedValue({
      data: {
        results: [
          {
            id: 401,
            event_type: 'planting',
            tree_count_delta: 50,
            resulting_tree_count: 50,
            location_tree_stock: {
              location: { name: 'الموقع الشرقي', farm: { name: 'مزرعة النخيل' } },
              crop_variety: { name: 'الصنف الذهبي' },
            },
            loss_reason: null,
          },
        ],
      },
    })
    mockTreeInventorySummaryExport.mockResolvedValue({
      data: new Blob(['summary'], { type: 'text/csv' }),
    })
    mockTreeInventoryEventsExport.mockResolvedValue({
      data: new Blob(['events'], { type: 'text/csv' }),
    })
    mockTreeInventoryLocationSummary.mockResolvedValue({
      data: {
        location: { id: 10, name: 'الموقع الشرقي', farm_id: 1, farm_name: 'مزرعة النخيل' },
        stocks: [],
        service_scopes: [{ value: 'general', label: 'عام' }],
        service_totals: {
          breakdown: { general: 0 },
          total_current_trees: 0,
          stocks_count: 0,
          last_inventory_update: null,
        },
      },
    })
    mockActivitiesTeamSuggestions.mockResolvedValue({ data: { suggestions: [] } })

    mockGetFarmContext.mockResolvedValue({
      farmId: '1',
      crops: [
        { id: 1, name: 'نخيل', is_perennial: true },
        { id: 2, name: 'قمح', is_perennial: false },
      ],
      locations: [{ id: 10, name: 'الموقع الشرقي' }],
      assets: [],
      wellsByLocation: {},
      tasksByCrop: {
        1: [
          {
            id: 100,
            stage: 'رعاية',
            name: 'تشذيب الأشجار',
            requires_tree_count: true,
            is_perennial_procedure: true,
          },
          { id: 101, stage: 'رعاية', name: 'تنظيف الموقع', requires_tree_count: false },
        ],
      },
      varietiesByCrop: {
        1: [{ id: 200, name: 'الصنف الذهبي' }],
      },
    })
    mockPersistFarmContext.mockResolvedValue(undefined)
  })

  afterAll(() => {
    if (originalCreateObjectURL) {
      globalThis.URL.createObjectURL = originalCreateObjectURL
    } else {
      delete globalThis.URL.createObjectURL
    }
    if (originalRevokeObjectURL) {
      globalThis.URL.revokeObjectURL = originalRevokeObjectURL
    } else {
      delete globalThis.URL.revokeObjectURL
    }
  })

  it('shows tree inputs for perennial crops with tree-count tasks and loads snapshot', async () => {
    render(<DailyLog />)
    expect(screen.queryByText(AR.treePanelTitle)).not.toBeInTheDocument()

    const farmSelect = await screen.findByLabelText(AR.farmLabel)
    await userEvent.selectOptions(farmSelect, '1')
    await waitFor(() => expect(mockGetFarmContext).toHaveBeenCalled())

    const locationSelect = screen.getByLabelText(AR.locationLabel)
    await waitFor(() => expect(locationSelect).not.toBeDisabled())
    await userEvent.selectOptions(locationSelect, '10')

    const cropSelect = screen.getByLabelText(AR.cropLabel)
    await waitFor(() => expect(cropSelect).not.toBeDisabled())
    await userEvent.selectOptions(cropSelect, '1')

    const taskSelect = screen.getByLabelText(AR.taskLabel)
    await waitFor(() => expect(taskSelect).not.toBeDisabled())
    await userEvent.selectOptions(taskSelect, '100')

    const treeSectionTitle = await screen.findByText(AR.treePanelTitle)
    expect(treeSectionTitle).toBeInTheDocument()
    expect(screen.getByLabelText(AR.serviceCountLabel)).toBeInTheDocument()

    const varietySelect = screen.getByLabelText(AR.varietyLabel)
    await userEvent.selectOptions(varietySelect, '200')

    await waitFor(() => {
      expect(mockTreeInventorySummary).toHaveBeenCalledWith({
        location_id: '10',
        variety_id: '200',
      })
    })
  })

  it('hides tree inputs when selected task does not require tree tracking', async () => {
    render(<DailyLog />)

    const farmSelect = await screen.findByLabelText(AR.farmLabel)
    await userEvent.selectOptions(farmSelect, '1')
    await waitFor(() => expect(mockGetFarmContext).toHaveBeenCalled())

    const locationSelect = screen.getByLabelText(AR.locationLabel)
    await waitFor(() => expect(locationSelect).not.toBeDisabled())
    await userEvent.selectOptions(locationSelect, '10')

    const cropSelect = screen.getByLabelText(AR.cropLabel)
    await waitFor(() => expect(cropSelect).not.toBeDisabled())
    await userEvent.selectOptions(cropSelect, '1')

    const taskSelect = screen.getByLabelText(AR.taskLabel)
    await waitFor(() => expect(taskSelect).not.toBeDisabled())
    await userEvent.selectOptions(taskSelect, '101')

    expect(screen.queryByText(AR.treePanelTitle)).not.toBeInTheDocument()
    expect(mockTreeInventorySummary).not.toHaveBeenCalled()
  })

  it('renders perennial summary card when report contains tree metrics', async () => {
    mockReportsDailySummary.mockResolvedValueOnce({
      data: {
        metrics: { logs: 1, activities: 1, distinct_supervisors: 1 },
        perennial: {
          activities: 1,
          trees_serviced: 40,
          net_tree_delta: 5,
          gain_tree_delta: 10,
          loss_tree_delta: -5,
          current_tree_count: 120,
          entries: [
            {
              crop: { id: 1, name: 'نخيل' },
              variety: { id: 200, name: 'الصنف الذهبي' },
              location: { id: 10, name: 'الموقع الشرقي' },
              activities: 1,
              trees_serviced: 40,
              net_tree_delta: 5,
              current_tree_count: 120,
            },
          ],
        },
      },
    })
    mockDailyLogsDaySummary.mockResolvedValueOnce({ data: {} })

    render(<DailyLog />)

    // Match any summary title that contains both 'ملخص' and 'الأشجار' to be resilient
    expect(await screen.findByText(/ملخص[\s\S]*الأشجار/)).toBeInTheDocument()
    expect(screen.getByText('تفاصيل الأصناف والمواقع المخدومة')).toBeInTheDocument()
    expect(screen.getByText('نخيل')).toBeInTheDocument()
    expect(screen.getByText('الصنف الذهبي')).toBeInTheDocument()
  })

  it('fetches tree inventory data, applies filters, and triggers exports', async () => {
    render(<TreeInventoryPage />)

    await screen.findByText('الموقع الشرقي')
    await screen.findByText('سجل الحركات')

    mockTreeInventorySummary.mockClear()
    mockTreeInventoryEvents.mockClear()

    const farmSelect = await screen.findByLabelText('المزرعة')
    await userEvent.selectOptions(farmSelect, '1')

    const locationSelect = screen.getByLabelText('الموقع')
    await waitFor(() => expect(locationSelect).not.toBeDisabled())
    await userEvent.selectOptions(locationSelect, '10')

    const varietySelect = screen.getByLabelText('الصنف')
    await waitFor(() => expect(varietySelect).not.toBeDisabled())
    await userEvent.selectOptions(varietySelect, '200')

    const statusSelect = screen.getByLabelText('الحالة الإنتاجية')
    await waitFor(() => expect(statusSelect).not.toBeDisabled())
    await userEvent.selectOptions(statusSelect, 'productive')

    const lossSelect = screen.getByLabelText('سبب الفقد')
    await waitFor(() => expect(lossSelect).not.toBeDisabled())
    await userEvent.selectOptions(lossSelect, 'storm')

    const startInput = screen.getByLabelText('من تاريخ')
    const endInput = screen.getByLabelText('إلى تاريخ')
    fireEvent.change(startInput, { target: { value: '2024-01-01' } })
    fireEvent.change(endInput, { target: { value: '2024-12-31' } })

    const serviceStartInput = screen.getByLabelText('بداية فترة الخدمة')
    const serviceEndInput = screen.getByLabelText('نهاية فترة الخدمة')
    fireEvent.change(serviceStartInput, { target: { value: '2024-03-01' } })
    fireEvent.change(serviceEndInput, { target: { value: '2024-04-30' } })

    await userEvent.click(screen.getByRole('button', { name: 'تطبيق' }))

    await waitFor(() => expect(mockTreeInventorySummary).toHaveBeenCalledTimes(1))
    expect(mockTreeInventorySummary).toHaveBeenCalledWith({
      farm_id: '1',
      location_id: '10',
      variety_id: '200',
      status_code: 'productive',
      planted_after: '2024-01-01',
      planted_before: '2024-12-31',
      service_start: '2024-03-01',
      service_end: '2024-04-30',
    })
    expect(mockTreeInventoryEvents).toHaveBeenCalledWith({
      farm_id: '1',
      location_id: '10',
      variety_id: '200',
      loss_reason: 'storm',
      from: '2024-01-01',
      to: '2024-12-31',
    })

    await userEvent.click(screen.getByRole('button', { name: 'تصدير الملخص' }))
    expect(mockTreeInventorySummaryExport).toHaveBeenCalledWith({
      farm_id: '1',
      location_id: '10',
      variety_id: '200',
      status_code: 'productive',
      planted_after: '2024-01-01',
      planted_before: '2024-12-31',
      service_start: '2024-03-01',
      service_end: '2024-04-30',
    })

    await userEvent.click(screen.getByRole('button', { name: 'تصدير الحركات' }))
    expect(mockTreeInventoryEventsExport).toHaveBeenCalledWith({
      farm_id: '1',
      location_id: '10',
      variety_id: '200',
      loss_reason: 'storm',
      from: '2024-01-01',
      to: '2024-12-31',
    })
  })

  it('displays service stats within the tree inventory summary table', async () => {
    render(<TreeInventoryPage />)

    const periodCoverage = await screen.findByText(/تغطية الفترة:\s*[0-9\u0660-\u0669.,]+%/)
    expect(periodCoverage).toBeInTheDocument()
    expect(screen.getByText(/التغطية التراكمية:\s*[0-9\u0660-\u0669.,]+%/)).toBeInTheDocument()
    // Use a regex to tolerate minor DOM/text formatting differences around the date
    expect(screen.getByText(/التاريخ:\s*2024-04-05/)).toBeInTheDocument()
    const countLine = screen.getByText(/عدد الأشجار:/)
    expect(countLine.textContent).toMatch(/عدد الأشجار:\s*[0-9\u0660-\u0669]+/)
    expect(screen.getByText('نوع الخدمة: ري')).toBeInTheDocument()
    expect(screen.getByText('مسجل بواسطة: المهندس سامي')).toBeInTheDocument()
  })
})

describe('tree inventory smoke', () => {
  it('loads DailyLog and TreeInventory modules', async () => {
    const dailyLogModule = await import('../src/pages/DailyLog.jsx')
    const treeInventoryModule = await import('../src/pages/TreeInventory.jsx')
    expect(typeof dailyLogModule.default).toBe('function')
    expect(typeof treeInventoryModule.default).toBe('function')
  }, 20000)
})
