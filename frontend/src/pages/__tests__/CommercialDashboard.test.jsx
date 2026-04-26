import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const asyncRequest = vi.fn()
const asyncStatus = vi.fn()
const asyncDownload = vi.fn()
const toastError = vi.fn()
const toastLoading = vi.fn(() => 'toast-id')
const toastSuccess = vi.fn()
const mockedFinancialFilters = {
  filters: { farm: '16', location: '9', crop_plan: '2', crop: '4' },
  options: {},
  loading: false,
  setFilter: vi.fn(),
  resetFilters: vi.fn(),
  filterParams: { farm: '16', location: '9', crop_plan: '2', crop: '4' },
}

vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="chart-line" />,
}))

vi.mock('chart.js', () => ({
  Chart: { register: vi.fn() },
  CategoryScale: {},
  LinearScale: {},
  PointElement: {},
  LineElement: {},
  BarElement: {},
  ArcElement: {},
  Title: {},
  Tooltip: {},
  Legend: {},
  Filler: {},
}))

vi.mock('../../components/commercial/PremiumUI.jsx', () => ({
  PremiumCard: ({ title, value }) => (
    <div>
      <span>{title}</span>
      <span>{value}</span>
    </div>
  ),
  GlassContainer: ({ title, children, action }) => (
    <section>
      <h2>{title}</h2>
      {action}
      {children}
    </section>
  ),
}))

vi.mock('../../components/filters/FinancialFilterBar', () => ({
  default: () => <div data-testid="financial-filter-bar" />,
}))

vi.mock('../../hooks/useFinancialFilters', () => ({
  default: () => mockedFinancialFilters,
}))

vi.mock('../../api/client', () => ({
  api: { get: (...args) => apiGet(...args) },
  AsyncReports: {
    request: (...args) => asyncRequest(...args),
    status: (...args) => asyncStatus(...args),
    download: (...args) => asyncDownload(...args),
  },
}))

vi.mock('react-hot-toast', () => ({
  toast: {
    error: (...args) => toastError(...args),
    loading: (...args) => toastLoading(...args),
    success: (...args) => toastSuccess(...args),
  },
}))

import CommercialDashboard from '../CommercialDashboard'

describe('CommercialDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('requests and downloads a commercial pdf using live filter params', async () => {
    apiGet.mockResolvedValueOnce({
      data: {
        active_plans: 3,
        financials: { revenue: 1200, cost: 300, net_profit: 900, currency: 'YER' },
        yields: { expected: 80, actual: 60 },
        risk_zone: { margin_percent: 25, zone: 'safe' },
        pulse: { active_plans: 3, approved_invoices: 4, expected_yield: 80, actual_yield: 60 },
        trend: [],
        allocations: [],
        grading: [],
      },
    })
    asyncRequest.mockResolvedValueOnce({ data: { id: 44 } })
    asyncStatus.mockResolvedValueOnce({
      data: { id: 44, status: 'completed', result_url: '/media/reports/c44.pdf' },
    })
    asyncDownload.mockResolvedValueOnce(undefined)

    render(<CommercialDashboard />)

    await waitFor(() =>
      expect(apiGet).toHaveBeenCalledWith('/dashboard-stats/', {
        params: { farm: '16', location: '9', crop_plan: '2', crop: '4' },
      }),
    )

    await userEvent.click(screen.getByRole('button', { name: 'تصدير PDF' }))

    await waitFor(() =>
      expect(asyncRequest).toHaveBeenCalledWith({
        farm_id: '16',
        location_id: '9',
        crop_plan_id: '2',
        crop_id: '4',
        report_type: 'commercial_pdf',
        format: 'pdf',
      }),
    )
    await waitFor(() =>
      expect(asyncDownload).toHaveBeenCalledWith(
        '/media/reports/c44.pdf',
        expect.stringMatching(/^commercial-report-16-/),
      ),
    )
  })

  it('blocks export when dashboard is showing fallback data', async () => {
    apiGet.mockRejectedValueOnce(new Error('network down'))

    render(<CommercialDashboard />)

    await waitFor(() => expect(screen.getByText(/القيم المعروضة احتياطية/)).not.toBeNull())

    const button = screen.getByRole('button', { name: 'تصدير PDF' })
    expect(button.hasAttribute('disabled')).toBe(true)
    expect(asyncRequest).not.toHaveBeenCalled()
  })
})
