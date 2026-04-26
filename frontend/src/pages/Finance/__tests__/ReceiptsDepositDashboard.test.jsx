import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const salesList = vi.fn()
const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()

vi.mock('../../../api/client', () => ({
  default: {
    get: (...args) => apiGet(...args),
  },
  Sales: {
    list: (...args) => salesList(...args),
  },
}))

vi.mock('../../../api/farmContext', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../../utils/errorUtils', () => ({
  extractApiError: (_error, fallback) => fallback,
}))

import ReceiptsDepositDashboard from '../ReceiptsDepositDashboard'

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ReceiptsDepositDashboard />
    </MemoryRouter>,
  )
}

describe('ReceiptsDepositDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({ selectedFarmId: '11' })
  })

  it('keeps simple mode focused on control posture without strict amount column', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
    })

    salesList.mockResolvedValue({
      data: [
        {
          id: 1,
          invoice_number: 'SI-1',
          customer_name: 'Client A',
          status: 'approved',
          total_amount: '1500.00',
        },
      ],
    })
    apiGet.mockResolvedValue({
      data: [{ id: 91, transaction_type: 'RECEIPT', amount: '1000.00', reference: 'RCPT-1' }],
    })

    renderPage()

    expect((await screen.findByTestId('receipts-deposit-policy-banner')).textContent).toContain(
      'operations_only',
    )
    expect(screen.getByTestId('receipts-deposit-invoices-table')).toBeTruthy()
    expect(screen.queryByTestId('receipts-deposit-amount-column')).toBeNull()
    expect(screen.getAllByText('حجم العمليات الإدارية').length).toBeGreaterThan(0)
  })

  it('shows strict amount column and governed values in strict mode', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'finance_control',
    })

    salesList.mockResolvedValue({
      data: [
        {
          id: 4,
          invoice_number: 'SI-4',
          customer_name: 'Client B',
          status: 'paid',
          total_amount: '2200.00',
        },
      ],
    })
    apiGet.mockResolvedValue({
      data: [{ id: 92, transaction_type: 'RECEIPT', amount: '2200.00', reference: 'RCPT-2' }],
    })

    renderPage()

    expect(await screen.findByTestId('receipts-deposit-amount-column')).toBeTruthy()
    expect(screen.getAllByText('2,200.00').length).toBeGreaterThan(0)
  })
})
