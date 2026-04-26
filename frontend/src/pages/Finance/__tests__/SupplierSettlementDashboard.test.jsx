import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const supplierSettlementsList = vi.fn()
const supplierSettlementsCreate = vi.fn()
const supplierSettlementsSubmitReview = vi.fn()
const supplierSettlementsApprove = vi.fn()
const supplierSettlementsRecordPayment = vi.fn()
const purchaseOrdersList = vi.fn()
const apiGet = vi.fn()
const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()
const useAuthMock = vi.fn()
const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
}

vi.mock('../../../api/client', () => ({
  SupplierSettlements: {
    list: (...args) => supplierSettlementsList(...args),
    create: (...args) => supplierSettlementsCreate(...args),
    submitReview: (...args) => supplierSettlementsSubmitReview(...args),
    approve: (...args) => supplierSettlementsApprove(...args),
    recordPayment: (...args) => supplierSettlementsRecordPayment(...args),
  },
  PurchaseOrders: {
    list: (...args) => purchaseOrdersList(...args),
  },
  api: {
    get: (...args) => apiGet(...args),
  },
}))

vi.mock('../../../api/farmContext', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('../../../components/ToastProvider', () => ({
  useToast: () => toastMock,
}))

vi.mock('../../../utils/errorUtils', () => ({
  extractApiError: (_error, fallback) => fallback,
}))

import SupplierSettlementDashboard from '../SupplierSettlementDashboard'

describe('SupplierSettlementDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({ selectedFarmId: '8' })
    useAuthMock.mockReturnValue({
      isAdmin: true,
      is_superuser: false,
      hasPermission: vi.fn(() => true),
      hasFarmRole: vi.fn(() => false),
    })
  })

  it('keeps simple mode control-focused and hides strict amount column', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
    })
    supplierSettlementsList.mockResolvedValue({
      data: [
        {
          id: 4,
          purchase_order: 12,
          vendor_name: 'Green Supplier',
          status: 'UNDER_REVIEW',
          variance_severity: 'warning',
          reconciliation_state: 'OPEN',
          remaining_balance: '800.00',
          paid_amount: '0.00',
          payable_amount: '800.00',
        },
      ],
    })
    purchaseOrdersList.mockResolvedValue({ data: [] })
    apiGet.mockResolvedValue({ data: [] })

    render(<SupplierSettlementDashboard />)

    expect((await screen.findByTestId('supplier-settlement-policy-banner')).textContent).toContain(
      'operations_only',
    )
    expect(screen.getByTestId('supplier-settlement-table')).toBeTruthy()
    expect(screen.queryByTestId('supplier-settlement-amount-column')).toBeNull()
    expect(screen.getByText('warning')).toBeTruthy()
  })

  it('shows strict actions and can create then approve a settlement', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'finance_control',
    })
    supplierSettlementsList
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({
        data: [
          {
            id: 14,
            purchase_order: 21,
            vendor_name: 'Blue Vendor',
            status: 'DRAFT',
            variance_severity: 'normal',
            reconciliation_state: 'OPEN',
            remaining_balance: '1200.00',
            paid_amount: '0.00',
            payable_amount: '1200.00',
          },
        ],
      })
      .mockResolvedValueOnce({
        data: [
          {
            id: 14,
            purchase_order: 21,
            vendor_name: 'Blue Vendor',
            status: 'UNDER_REVIEW',
            variance_severity: 'normal',
            reconciliation_state: 'OPEN',
            remaining_balance: '1200.00',
            paid_amount: '0.00',
            payable_amount: '1200.00',
          },
        ],
      })
    purchaseOrdersList.mockResolvedValue({
      data: [{ id: 21, vendor_name: 'Blue Vendor', status: 'APPROVED' }],
    })
    apiGet.mockResolvedValue({ data: [{ id: 3, name: 'Main Safe' }] })
    supplierSettlementsCreate.mockResolvedValue({ data: { id: 14 } })
    supplierSettlementsSubmitReview.mockResolvedValue({ data: { id: 14, status: 'UNDER_REVIEW' } })

    render(<SupplierSettlementDashboard />)

    expect(await screen.findByTestId('supplier-settlement-amount-column')).toBeTruthy()
    fireEvent.change(screen.getByTestId('supplier-settlement-create-select'), {
      target: { value: '21' },
    })
    fireEvent.click(screen.getByText('إنشاء'))

    await waitFor(() =>
      expect(supplierSettlementsCreate).toHaveBeenCalledWith({ purchase_order: '21' }),
    )

    expect(await screen.findByText('طلب مراجعة')).toBeTruthy()
    fireEvent.click(screen.getByText('طلب مراجعة'))

    await waitFor(() => expect(supplierSettlementsSubmitReview).toHaveBeenCalledWith(14, {}))
    await waitFor(() => expect(toastMock.success).toHaveBeenCalled())
  })
})
