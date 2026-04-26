import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const summaryMock = vi.fn()
const eventsMock = vi.fn()
const summaryExportMock = vi.fn()
const eventsExportMock = vi.fn()
const adjustMock = vi.fn()
const locationVarietySummaryMock = vi.fn()
const statusesMock = vi.fn()
const reasonsMock = vi.fn()
const varietiesMock = vi.fn()
const cropsListMock = vi.fn()
const useAuthMock = vi.fn()
const toastMock = vi.fn()

vi.mock('../../api/client', () => ({
  api: {
    get: (...args) => apiGet(...args),
  },
  TreeInventory: {
    summary: (...args) => summaryMock(...args),
    events: (...args) => eventsMock(...args),
    summaryExport: (...args) => summaryExportMock(...args),
    eventsExport: (...args) => eventsExportMock(...args),
  },
  TreeInventoryAdmin: {
    adjust: (...args) => adjustMock(...args),
  },
  TreeInventorySummary: {
    locationVarietySummary: (...args) => locationVarietySummaryMock(...args),
  },
  TreeProductivityStatuses: {
    list: (...args) => statusesMock(...args),
  },
  TreeLossReasons: {
    list: (...args) => reasonsMock(...args),
  },
  CropVarieties: {
    list: (...args) => varietiesMock(...args),
  },
  Crops: {
    list: (...args) => cropsListMock(...args),
  },
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => toastMock,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useLocation: () => ({ state: null }),
  }
})

import TreeInventoryPage from '../TreeInventory.jsx'

describe('TreeInventory administrative adjustment path', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthMock.mockReturnValue({
      isAdmin: true,
      isSuperuser: false,
      canChangeModel: vi.fn(() => true),
    })
    apiGet.mockImplementation((url, config = {}) => {
      if (url === '/farms/') {
        return Promise.resolve({ data: [{ id: 11, name: 'الربوعية' }] })
      }
      if (url === '/locations/' && config.params?.farm_id === '11') {
        return Promise.resolve({ data: [{ id: 101, name: 'قطاع المانجو الشرقي' }] })
      }
      return Promise.resolve({ data: [] })
    })
    statusesMock.mockResolvedValue({ data: [] })
    reasonsMock.mockResolvedValue({ data: [] })
    summaryMock.mockResolvedValue({
      data: [
        {
          id: 900,
          current_tree_count: 80,
          location: { id: 101, name: 'قطاع المانجو الشرقي', farm: { id: 11, name: 'الربوعية' } },
          crop_variety: { id: 301, name: 'كيت', crop: { id: 201, name: 'مانجو' } },
          productivity_status: { code: 'productive', name_ar: 'منتج' },
          service_stats: { period: {}, lifetime: {} },
          planting_date: '2020-01-01',
          source: 'bootstrap',
        },
      ],
    })
    eventsMock.mockResolvedValue({ data: [] })
    cropsListMock.mockResolvedValue({ data: [{ id: 201, name: 'مانجو' }] })
    varietiesMock.mockResolvedValue({
      data: [{ id: 301, name: 'كيت', crop_id: 201, crop: { id: 201, name: 'مانجو' } }],
    })
    locationVarietySummaryMock.mockResolvedValue({
      data: {
        results: [
          {
            variety_id: 301,
            variety_name: 'كيت',
            current_tree_count_total: 80,
            by_location: {
              '101': {
                location_id: 101,
                current_tree_count: 80,
              },
            },
          },
        ],
      },
    })
    adjustMock.mockResolvedValue({ data: { id: 900, current_tree_count: 95 } })
  })

  it('shows the audited adjustment CTA only for authorized users', async () => {
    render(<TreeInventoryPage />)

    expect(await screen.findByTestId('tree-inventory-open-adjustment')).toBeTruthy()
  })

  it('submits resulting_tree_count through the existing admin adjust endpoint', async () => {
    render(<TreeInventoryPage />)

    fireEvent.click(await screen.findByTestId('tree-inventory-open-adjustment'))
    fireEvent.change(screen.getByLabelText('المزرعة', { selector: '#adjustment-farm' }), {
      target: { value: '11' },
    })

    await waitFor(() => expect(cropsListMock).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText('الموقع', { selector: '#adjustment-location' }), {
      target: { value: '101' },
    })
    fireEvent.change(screen.getByLabelText('المحصول', { selector: '#adjustment-crop' }), {
      target: { value: '201' },
    })
    fireEvent.change(screen.getByLabelText('الصنف', { selector: '#adjustment-variety' }), {
      target: { value: '301' },
    })

    await waitFor(() => expect(locationVarietySummaryMock).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText('الرصيد الجاري الفعلي', { selector: '#adjustment-count' }), {
      target: { value: '95' },
    })
    fireEvent.change(screen.getByLabelText('سبب التسوية', { selector: '#adjustment-reason' }), {
      target: { value: 'جرد افتتاحي' },
    })
    fireEvent.change(screen.getByLabelText('المصدر', { selector: '#adjustment-source' }), {
      target: { value: 'لجنة الجرد' },
    })
    fireEvent.change(screen.getByLabelText('ملاحظات', { selector: '#adjustment-notes' }), {
      target: { value: 'مطابقة ميدانية للموقع الشرقي' },
    })

    fireEvent.click(screen.getByTestId('tree-inventory-submit-adjustment'))

    await waitFor(() => expect(adjustMock).toHaveBeenCalled())
    expect(adjustMock.mock.calls[0][0]).toMatchObject({
      stock_id: 900,
      resulting_tree_count: 95,
      reason: 'جرد افتتاحي',
      source: 'لجنة الجرد',
      notes: 'مطابقة ميدانية للموقع الشرقي',
    })
    expect(adjustMock.mock.calls[0][0].delta).toBeUndefined()
  })
})
