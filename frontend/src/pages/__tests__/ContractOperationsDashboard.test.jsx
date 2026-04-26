import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const dashboardMock = vi.fn()
const registerTouringMock = vi.fn()
const processHarvestMock = vi.fn()
const recordRentPaymentMock = vi.fn()
const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()
const useAuthMock = vi.fn()
const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
}

vi.mock('../../api/client', () => ({
  SharecroppingContracts: {
    dashboard: (...args) => dashboardMock(...args),
    registerTouring: (...args) => registerTouringMock(...args),
    processHarvest: (...args) => processHarvestMock(...args),
    recordRentPayment: (...args) => recordRentPaymentMock(...args),
  },
}))

vi.mock('../../api/farmContext', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => toastMock,
}))

vi.mock('../../utils/errorUtils', () => ({
  extractApiError: (_error, fallback) => fallback,
}))

import ContractOperationsDashboard from '../ContractOperationsDashboard'

describe('ContractOperationsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({ selectedFarmId: '8' })
    useAuthMock.mockReturnValue({
      isAdmin: true,
      is_superuser: false,
      hasPermission: vi.fn(() => true),
      hasFarmRole: vi.fn((role) => role === 'manager'),
    })
  })

  it('keeps simple mode control-focused and hides amount column', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
      contractMode: 'operational_only',
    })
    dashboardMock.mockResolvedValue({
      data: {
        summary: {
          awaiting_touring: 1,
          touring_completed_unsettled: 0,
          overdue_rentals: 0,
          mismatched_settlements: 0,
          unresolved_contract_variances: 1,
        },
        results: [
          {
            id: 11,
            farmer_name: 'Field Partner',
            farm_name: 'Farm A',
            crop_name: 'Wheat',
            season_name: '2026',
            contract_type: 'SHARECROPPING',
            status: 'READY_FOR_TOURING',
            touring_state: 'NO_TOURING',
            settlement_state: 'OPEN',
            receipt_state: 'NONE',
            variance_severity: 'warning',
            contract_mode: 'operational_only',
            sharecropping_mode: 'FINANCIAL',
            annual_rent_amount: '0.0000',
            expected_institution_share: '0.0000',
            actual_institution_share: '0.0000',
            expected_vs_actual_gap: '0.0000',
            approval_state: 'OPERATIONAL_ONLY',
            reconciliation_state: 'OPEN',
            flags: ['no_touring'],
            latest_touring: null,
            latest_receipt: null,
            last_rent_payment: null,
          },
        ],
      },
    })

    render(<ContractOperationsDashboard />)

    expect((await screen.findByTestId('contract-operations-policy-banner')).textContent).toContain(
      'operational_only',
    )
    expect(screen.getByTestId('contract-operations-smart-card')).toBeTruthy()
    expect(screen.queryByTestId('contract-operations-amount-column')).toBeNull()
    expect(screen.getByText('READY_FOR_TOURING')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'جولة تقدير' }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'حصاد / استلام' }).disabled).toBe(true)
  })

  it('filters rental contracts and posts rent payment in strict mode', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'full_erp',
      contractMode: 'full_erp',
    })
    dashboardMock
      .mockResolvedValueOnce({
        data: {
          summary: {
            awaiting_touring: 0,
            touring_completed_unsettled: 0,
            overdue_rentals: 1,
            mismatched_settlements: 0,
            unresolved_contract_variances: 1,
          },
          results: [
            {
              id: 14,
              farmer_name: 'Rental Partner',
              farm_name: 'Farm A',
              crop_name: 'Wheat',
              season_name: '2026',
              contract_type: 'RENTAL',
              status: 'ACTIVE',
              touring_state: 'NOT_REQUIRED',
              settlement_state: 'OPEN',
              receipt_state: 'NOT_REQUIRED',
              variance_severity: 'warning',
              contract_mode: 'full_erp',
              sharecropping_mode: 'FINANCIAL',
              annual_rent_amount: '1200.0000',
              expected_institution_share: '1200.0000',
              actual_institution_share: '0.0000',
              expected_vs_actual_gap: '1200.0000',
              approval_state: 'STRICT_READY',
              reconciliation_state: 'OPEN',
              flags: ['overdue_rental'],
              latest_touring: null,
              latest_receipt: null,
              last_rent_payment: null,
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          summary: {
            awaiting_touring: 0,
            touring_completed_unsettled: 0,
            overdue_rentals: 0,
            mismatched_settlements: 0,
            unresolved_contract_variances: 0,
          },
          results: [
            {
              id: 14,
              farmer_name: 'Rental Partner',
              farm_name: 'Farm A',
              crop_name: 'Wheat',
              season_name: '2026',
              contract_type: 'RENTAL',
              status: 'PARTIALLY_SETTLED',
              touring_state: 'NOT_REQUIRED',
              settlement_state: 'PARTIAL',
              receipt_state: 'NOT_REQUIRED',
              variance_severity: 'normal',
              contract_mode: 'full_erp',
              sharecropping_mode: 'FINANCIAL',
              annual_rent_amount: '1200.0000',
              expected_institution_share: '1200.0000',
              actual_institution_share: '300.0000',
              expected_vs_actual_gap: '900.0000',
              approval_state: 'STRICT_READY',
              reconciliation_state: 'OPEN',
              flags: [],
              latest_touring: null,
              latest_receipt: null,
              last_rent_payment: { payment_period: '2026-Q1', amount: '300.0000' },
            },
          ],
        },
      })
    recordRentPaymentMock.mockResolvedValue({ data: { status: 'posted' } })

    render(<ContractOperationsDashboard />)

    expect(await screen.findByTestId('contract-operations-amount-column')).toBeTruthy()
    fireEvent.change(screen.getByTestId('contract-operations-filter'), {
      target: { value: 'RENTAL' },
    })
    expect(screen.getByText('Rental Partner')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'سداد إيجار' }))
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '300.0000' } })
    fireEvent.change(screen.getByLabelText('Payment period'), { target: { value: '2026-Q1' } })
    fireEvent.click(screen.getByRole('button', { name: 'ترحيل الدفعة النقدية' }))

    await waitFor(() =>
      expect(recordRentPaymentMock).toHaveBeenCalledWith(14, {
        amount: '300.0000',
        payment_period: '2026-Q1',
        notes: '',
      }),
    )
    await waitFor(() => expect(toastMock.success).toHaveBeenCalled())
  })
})
