import React from 'react'
import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()
const useAuthMock = vi.fn()

vi.mock('../../../api/client', () => ({
  api: {
    get: (...args) => apiGet(...args),
  },
}))

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

import FarmSettingsTab from '../FarmSettingsTab'

describe('FarmSettingsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthMock.mockReturnValue({
      isSuperuser: true,
      isAdmin: true,
      hasPermission: vi.fn(() => true),
    })
    apiGet.mockResolvedValue({
      data: {
        results: [
          {
            id: 7,
            mode: 'SIMPLE',
            approval_profile: 'tiered',
            cost_visibility: 'summarized_amounts',
            treasury_visibility: 'hidden',
            fixed_asset_mode: 'tracking_only',
            contract_mode: 'operational_only',
            variance_behavior: 'warn',
            enable_zakat: true,
            enable_depreciation: true,
            enable_sharecropping: false,
            enable_petty_cash: true,
            remote_site: false,
            single_finance_officer_allowed: false,
            mandatory_attachment_for_cash: false,
            weekly_remote_review_required: false,
            attachment_require_clean_scan_for_strict: true,
            allow_overlapping_crop_plans: false,
            allow_multi_location_activities: true,
            allow_cross_plan_activities: false,
            allow_creator_self_variance_approval: false,
            show_daily_log_smart_card: true,
            show_finance_in_simple: true,
            show_stock_in_simple: true,
            show_employees_in_simple: false,
          },
        ],
      },
    })
  })

  it('renders SIMPLE compatibility warning for transitional visibility flags', async () => {
    render(<FarmSettingsTab selectedFarmId="12" hasFarms />)

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/farm-settings/?farm=12'))
    expect(await screen.findByTestId('simple-compatibility-note')).toHaveTextContent(
      'compatibility-only',
    )
    expect(screen.getByTestId('simple-compatibility-note')).toHaveTextContent('display-only')
    expect(screen.getByTestId('simple-compatibility-note')).toHaveTextContent(
      'not authoring authority',
    )
  })
})
