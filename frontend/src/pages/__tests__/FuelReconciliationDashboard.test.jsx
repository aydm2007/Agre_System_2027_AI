import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()
const useAuthMock = vi.fn()

vi.mock('../../api/client', () => ({
  api: {
    get: (...args) => apiGet(...args),
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

vi.mock('../../utils/errorUtils', () => ({
  extractApiError: (_error, fallback) => fallback,
}))

import FuelReconciliationDashboard from '../FuelReconciliationDashboard'

describe('FuelReconciliationDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({ selectedFarmId: '12' })
    useAuthMock.mockReturnValue({
      isAdmin: true,
      is_superuser: false,
      hasPermission: vi.fn(() => true),
      hasFarmRole: vi.fn(() => false),
    })
  })

  it('keeps simple mode operational and hides amount column', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
      varianceBehavior: 'warn',
      treasuryVisibility: 'hidden',
    })
    apiGet.mockResolvedValue({
      data: {
        summary: {
          logs_count: 1,
          open_anomalies: 1,
          warning_logs: 1,
          critical_logs: 0,
          missing_calibration_logs: 0,
          pending_reconciliation_logs: 1,
        },
        results: [
          {
            id: 1,
            tank: 'Diesel Tank 1',
            tank_code: 'TNK-1',
            farm_name: 'Farm A',
            supervisor: 'Fuel Supervisor',
            measurement_method: 'DIPSTICK',
            reading_date: '2026-03-13T09:00:00Z',
            expected_liters: '10.0000',
            actual_liters: '12.0000',
            variance_liters: '2.0000',
            variance_severity: 'warning',
            fuel_alert_status: 'WARNING',
            reconciliation_state: 'pending_review',
            visibility_level: 'operations_only',
            cost_display_mode: 'ratios_only',
            flags: {
              missing_calibration: false,
              missing_benchmark: false,
              warning_variance: true,
              critical_variance: false,
              no_machine_link: false,
            },
            alerts_count: 1,
          },
        ],
      },
    })

    render(<FuelReconciliationDashboard />)

    expect(await screen.findByTestId('fuel-reconciliation-policy-banner')).toBeTruthy()
    expect(screen.getByTestId('fuel-reconciliation-table')).toBeTruthy()
    expect(screen.queryByTestId('fuel-reconciliation-amount-column')).toBeNull()
    expect(screen.getByTestId('fuel-reconciliation-smart-card').textContent).toContain(
      'pending_review',
    )
  })

  it('shows strict trace values when full amounts are allowed', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'full_erp',
      varianceBehavior: 'block',
      treasuryVisibility: 'visible',
    })
    apiGet.mockResolvedValue({
      data: {
        summary: {
          logs_count: 2,
          open_anomalies: 1,
          warning_logs: 0,
          critical_logs: 1,
          missing_calibration_logs: 0,
          pending_reconciliation_logs: 1,
        },
        results: [
          {
            id: 4,
            tank: 'Diesel Tank 2',
            tank_code: 'TNK-2',
            farm_name: 'Farm A',
            supervisor: 'Fuel Supervisor',
            measurement_method: 'COUNTER',
            reading_date: '2026-03-13T10:00:00Z',
            expected_liters: '15.0000',
            actual_liters: '22.5000',
            variance_liters: '7.5000',
            variance_severity: 'critical',
            fuel_alert_status: 'CRITICAL',
            reconciliation_state: 'manager_review_required',
            visibility_level: 'full_erp',
            cost_display_mode: 'full_amounts',
            flags: {
              missing_calibration: false,
              missing_benchmark: true,
              warning_variance: false,
              critical_variance: true,
              no_machine_link: false,
            },
            alerts_count: 1,
          },
        ],
      },
    })

    render(<FuelReconciliationDashboard />)

    expect(await screen.findByTestId('fuel-reconciliation-amount-column')).toBeTruthy()
    await waitFor(() =>
      expect(screen.getByTestId('fuel-reconciliation-smart-card').textContent).toContain(
        'manager_review_required',
      ),
    )
    expect(screen.getAllByText('Diesel Tank 2').length).toBeGreaterThan(0)
  })

  it('keeps the policy banner visible while data is still loading', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
      varianceBehavior: 'warn',
      treasuryVisibility: 'hidden',
    })

    let resolveRequest
    apiGet.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )

    render(<FuelReconciliationDashboard />)

    expect(screen.getByTestId('fuel-reconciliation-policy-banner').textContent).toContain(
      'الوضع المبسط',
    )
    expect(screen.getByTestId('fuel-reconciliation-loading')).toBeTruthy()

    resolveRequest({
      data: {
        summary: {
          logs_count: 0,
          open_anomalies: 0,
          warning_logs: 0,
          critical_logs: 0,
          missing_calibration_logs: 0,
          pending_reconciliation_logs: 0,
        },
        results: [],
      },
    })

    await waitFor(() =>
      expect(screen.queryByTestId('fuel-reconciliation-loading')).toBeNull(),
    )
  })
})
