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

vi.mock('../../../api/farmContext', () => ({
  useFarmContext: () => ({ selectedFarmId: '16' }),
}))

vi.mock('../../../api/client', () => ({
  api: { get: (...args) => apiGet(...args) },
  AsyncReports: {
    request: (...args) => asyncRequest(...args),
    status: (...args) => asyncStatus(...args),
    download: (...args) => asyncDownload(...args),
  },
}))

vi.mock('../../../hooks/useFinancialFilters', () => ({
  default: () => ({
    filters: { farm: '16', costCenter: '7', crop_plan: '9' },
    options: {},
    loading: false,
    setFilter: vi.fn(),
    resetFilters: vi.fn(),
  }),
}))

vi.mock('../../../components/filters/FinancialFilterBar', () => ({
  default: () => <div data-testid="financial-filter-bar" />,
}))

vi.mock('react-hot-toast', () => ({
  toast: {
    error: (...args) => toastError(...args),
    loading: (...args) => toastLoading(...args),
    success: (...args) => toastSuccess(...args),
  },
}))

import AdvancedReportsScreen from '../AdvancedReportsScreen'

describe('AdvancedReportsScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('generates report requests using start/end payload keys', async () => {
    apiGet.mockResolvedValueOnce({
      data: {
        revenue_accounts: [],
        expense_accounts: [],
        totals: { total_revenue: '10.00', total_expense: '5.00', net_income: '5.00' },
      },
    })
    asyncRequest.mockResolvedValueOnce({ data: { id: 71 } })
    asyncStatus.mockResolvedValueOnce({
      data: { id: 71, status: 'completed', result_url: '/media/reports/f71.pdf' },
    })

    render(<AdvancedReportsScreen />)

    await waitFor(() => expect(apiGet).toHaveBeenCalled())

    await userEvent.type(screen.getByLabelText('من تاريخ'), '2026-01-01')
    await userEvent.type(screen.getByLabelText('إلى تاريخ'), '2026-01-31')
    await userEvent.click(screen.getByTestId('generate-report-button'))

    await waitFor(() =>
      expect(asyncRequest).toHaveBeenCalledWith({
        farm_id: '16',
        report_type: 'profitability_pdf',
        format: 'pdf',
        cost_center_id: '7',
        crop_plan_id: '9',
        start: '2026-01-01',
        end: '2026-01-31',
      }),
    )
    expect(asyncRequest.mock.calls[0][0].start_date).toBeUndefined()
    expect(asyncRequest.mock.calls[0][0].end_date).toBeUndefined()
  })
})
