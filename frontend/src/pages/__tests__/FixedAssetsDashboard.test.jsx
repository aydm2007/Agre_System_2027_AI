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

import FixedAssetsDashboard from '../FixedAssetsDashboard'

describe('FixedAssetsDashboard', () => {
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

  it('keeps tracking mode readable in simple mode without full capitalization values', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'ratios_only',
      visibilityLevel: 'operations_only',
      fixedAssetMode: 'tracking_only',
    })
    apiGet.mockResolvedValue({
      data: {
        summary: {
          assets_count: 1,
          warning_assets: 0,
          critical_assets: 0,
          total_purchase_value: '120000.00',
          categories: ['Solar'],
          report_flags: { tracking_only: true, requires_capitalization_controls: false },
        },
        results: [
          {
            id: 1,
            name: 'Solar Array 1',
            farm_name: 'Farm A',
            category: 'Solar',
            asset_type: 'solar_array',
            health_status: 'GREEN',
            capitalization_state: 'tracking_only',
            purchase_date: '2026-01-01',
            useful_life_years: 10,
            operational_cost_per_hour: '0.00',
            fixed_asset_mode: 'tracking_only',
            visibility_level: 'operations_only',
            cost_display_mode: 'ratios_only',
            purchase_value: '120000.00',
            accumulated_depreciation: '45000.00',
            book_value: '75000.00',
            depreciation_percentage: '40.91',
            status: 'active',
          },
        ],
      },
    })

    render(<FixedAssetsDashboard />)

    expect(await screen.findByTestId('fixed-assets-policy-banner')).toBeTruthy()
    expect(screen.getByTestId('fixed-assets-table')).toBeTruthy()
    expect(screen.queryByTestId('fixed-assets-amount-column')).toBeNull()
    expect(screen.getByTestId('fixed-assets-smart-card').textContent).toContain('tracking_only')
  })

  it('shows capitalization values in strict full-capitalization mode', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
      visibilityLevel: 'full_erp',
      fixedAssetMode: 'full_capitalization',
    })
    apiGet.mockResolvedValue({
      data: {
        summary: {
          assets_count: 2,
          warning_assets: 1,
          critical_assets: 0,
          total_purchase_value: '200000.00',
          categories: ['Machinery', 'Solar'],
          report_flags: { tracking_only: false, requires_capitalization_controls: true },
        },
        results: [
          {
            id: 2,
            name: 'Field Tractor',
            farm_name: 'Farm A',
            category: 'Machinery',
            asset_type: 'tractor',
            health_status: 'WARNING',
            capitalization_state: 'capitalized_and_depreciating',
            purchase_date: '2026-01-01',
            useful_life_years: 8,
            operational_cost_per_hour: '250.00',
            fixed_asset_mode: 'full_capitalization',
            visibility_level: 'full_erp',
            cost_display_mode: 'full_amounts',
            purchase_value: '80000.00',
            accumulated_depreciation: '10000.00',
            book_value: '70000.00',
            depreciation_percentage: '13.33',
            status: 'active',
          },
        ],
      },
    })

    render(<FixedAssetsDashboard />)

    expect(await screen.findByTestId('fixed-assets-amount-column')).toBeTruthy()
    await waitFor(() =>
      expect(screen.getByTestId('fixed-assets-smart-card').textContent).toContain(
        'capitalized_and_depreciating',
      ),
    )
    expect(screen.getAllByText('Field Tractor').length).toBeGreaterThan(0)
  })
})
