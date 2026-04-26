import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const activitiesList = vi.fn()
const dailyLogsList = vi.fn()
const useSettingsMock = vi.fn()
const toastMock = vi.fn()
const setFarmIdMock = vi.fn()
const setPageFarmIdMock = vi.fn()
const farmOptionsMock = [{ id: 21, name: 'Mango Farm' }]

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, username: 'admin' },
    isAdmin: false,
    is_superuser: false,
    hasFarmRole: () => true,
  }),
}))

vi.mock('../../api/client', () => ({
  DailyLogs: { list: (...args) => dailyLogsList(...args) },
  Activities: { list: (...args) => activitiesList(...args) },
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => toastMock,
}))

vi.mock('../../hooks/usePageFarmFilter', () => ({
  usePageFarmFilter: () => ({
    farmId: '21',
    setFarmId: setFarmIdMock,
    farmOptions: farmOptionsMock,
    canUseAll: false,
    effectiveFarmScope: '21',
    pageFarmId: null,
    setPageFarmId: setPageFarmIdMock,
    farms: farmOptionsMock,
    loadingFarms: false,
  }),
}))

vi.mock('../../components/filters/PageFarmFilter', () => ({
  default: () => <div data-testid="page-farm-filter" />,
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

import DailyLogHistory, { LogDetailPanel } from '../DailyLogHistory.jsx'

describe('LogDetailPanel governance controls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setFarmIdMock.mockReset()
    setPageFarmIdMock.mockReset()
    activitiesList.mockResolvedValue({ data: [] })
    dailyLogsList.mockResolvedValue({ data: [] })
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      costVisibility: 'summarized_amounts',
    })
  })

  it('disables approval when ghost cost is blocked', async () => {
    render(
      <LogDetailPanel
        log={{
          id: 11,
          status: 'SUBMITTED',
          variance_status: 'OK',
          ghost_cost_blocked: true,
          missing_price_governance: false,
          material_governance_blocked: false,
          ghost_cost_reasons: ['يوجد تنفيذ فعلي لكن التكلفة صفرية'],
        }}
        loading={false}
        onAction={vi.fn()}
        getFarmName={() => 'المزرعة'}
      />,
    )

    await waitFor(() => expect(activitiesList).toHaveBeenCalledWith({ log: 11 }))

    const approveButton = screen.getByTestId('dailylog-approve-button')
    expect(approveButton.hasAttribute('disabled')).toBe(true)
    expect(approveButton.getAttribute('title')).toBeTruthy()
  })

  it('uses stricter governance wording in strict mode', async () => {
    useSettingsMock.mockReturnValue({
      isStrictMode: true,
      costVisibility: 'full_amounts',
    })

    render(
      <LogDetailPanel
        log={{
          id: 12,
          status: 'SUBMITTED',
          variance_status: 'OK',
          ghost_cost_blocked: false,
          missing_price_governance: true,
          material_governance_blocked: false,
          ghost_cost_reasons: [],
        }}
        loading={false}
        onAction={vi.fn()}
        getFarmName={() => 'المزرعة'}
      />,
    )

    await waitFor(() => expect(activitiesList).toHaveBeenCalledWith({ log: 12 }))

    const approveButton = screen.getByTestId('dailylog-approve-button')
    expect(approveButton.hasAttribute('disabled')).toBe(true)
    expect(approveButton.getAttribute('title')).toContain('الاعتماد')
  })

  it('disables approval when material governance is blocked', async () => {
    render(
      <LogDetailPanel
        log={{
          id: 13,
          status: 'SUBMITTED',
          variance_status: 'OK',
          ghost_cost_blocked: false,
          missing_price_governance: false,
          material_governance_blocked: true,
          ghost_cost_reasons: [],
        }}
        loading={false}
        onAction={vi.fn()}
        getFarmName={() => 'المزرعة'}
      />,
    )

    await waitFor(() => expect(activitiesList).toHaveBeenCalledWith({ log: 13 }))

    const approveButton = screen.getByTestId('dailylog-approve-button')
    expect(approveButton.hasAttribute('disabled')).toBe(true)
  })

  it('refreshes history when a synced offline daily log matches the current scope', async () => {
    render(<DailyLogHistory />)

    await waitFor(() => expect(dailyLogsList).toHaveBeenCalled())
    const callsBeforeSync = dailyLogsList.mock.calls.length

    window.dispatchEvent(
      new CustomEvent('offline-daily-log-synced', {
        detail: {
          syncedDailyLogs: [
            {
              farmId: 21,
              date: '2026-04-25',
              logId: 101,
              activityId: 202,
            },
          ],
        },
      }),
    )

    await waitFor(() => expect(dailyLogsList.mock.calls.length).toBeGreaterThan(callsBeforeSync))
  })
})
