import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const safeRequestMock = vi.fn()
const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()
const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
}
const useAuthMock = vi.fn()

vi.mock('../../../api/client', () => ({
  default: {
    get: (...args) => apiGet(...args),
  },
  safeRequest: (...args) => safeRequestMock(...args),
}))

vi.mock('../../../api/farmContext', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../../components/ToastProvider', () => ({
  useToast: () => toastMock,
}))

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('../../../utils/errorUtils', () => ({
  extractApiError: (_error, fallback) => fallback,
}))

import PettyCashDashboard from '../PettyCashDashboard'

describe('PettyCashDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({ selectedFarmId: '7' })
    useAuthMock.mockReturnValue({
      isAdmin: true,
      is_superuser: false,
      hasPermission: vi.fn(() => true),
      hasFarmRole: vi.fn(() => false),
    })
  })

  it('keeps simple mode focused on operational visibility without strict-only columns', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      isPettyCashEnabled: true,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
    })

    apiGet
      .mockResolvedValueOnce({
        data: [
          {
            id: 12,
            amount: '125.0000',
            description: 'Fuel run',
            status: 'PENDING',
            created_at: null,
          },
        ],
      })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ id: 3, name: 'Main Safe' }] })
      .mockResolvedValueOnce({ data: [] })

    render(<PettyCashDashboard />)

    expect((await screen.findByTestId('petty-cash-visibility-banner')).textContent).toContain(
      'operations_only',
    )
    expect(screen.getByTestId('petty-cash-requests-table')).toBeTruthy()
    expect(screen.queryByTestId('petty-cash-cost-center-column')).toBeNull()
    expect(screen.getByText('رؤية محجوبة (صلاحية)')).toBeTruthy()
  })

  it('shows strict controls and can approve a pending request', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      isPettyCashEnabled: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'finance_control',
    })

    apiGet
      .mockResolvedValueOnce({
        data: [
          {
            id: 21,
            amount: '300.0000',
            description: 'Field team petty cash',
            status: 'PENDING',
            created_at: '2026-03-13T10:00:00Z',
            cost_center: 'CC-01',
          },
        ],
      })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ id: 5, name: 'Main Safe' }] })
      .mockResolvedValueOnce({ data: [{ id: 8, code: 'CC-01', name: 'Field Ops' }] })
      .mockResolvedValueOnce({
        data: [
          {
            id: 21,
            amount: '300.0000',
            description: 'Field team petty cash',
            status: 'APPROVED',
            created_at: '2026-03-13T10:00:00Z',
            cost_center: 'CC-01',
          },
        ],
      })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ id: 5, name: 'Main Safe' }] })
      .mockResolvedValueOnce({ data: [{ id: 8, code: 'CC-01', name: 'Field Ops' }] })

    safeRequestMock.mockResolvedValue({ data: { id: 21, status: 'APPROVED' } })

    render(<PettyCashDashboard />)

    expect(await screen.findByTestId('petty-cash-cost-center-column')).toBeTruthy()
    fireEvent.click(screen.getByText('اعتماد الطلب'))

    await waitFor(() =>
      expect(safeRequestMock).toHaveBeenCalledWith(
        'post',
        '/finance/petty-cash-requests/21/approve/',
        {},
      ),
    )
    await waitFor(() => expect(toastMock.success).toHaveBeenCalled())
  })
})
