import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const useFarmContextMock = vi.fn()
const useSettingsMock = vi.fn()
const useOpsRuntimeMock = vi.fn()
const useOfflineQueueMock = vi.fn()
const useAuthMock = vi.fn()

vi.mock('../../api/farmContext.jsx', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../contexts/SettingsContext.jsx', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../contexts/OpsRuntimeContext.jsx', () => ({
  useOpsRuntime: () => useOpsRuntimeMock(),
}))

vi.mock('../../offline/OfflineQueueProvider.jsx', () => ({
  useOfflineQueue: () => useOfflineQueueMock(),
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

import SimpleOperationsHub from '../SimpleOperationsHub.jsx'

describe('SimpleOperationsHub navigation contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({
      farms: [{ id: '11', name: 'الربوعية' }],
      selectedFarmId: '11',
      selectFarm: vi.fn(),
    })
    useSettingsMock.mockReturnValue({
      modeLabel: 'SIMPLE',
      isStrictMode: false,
      showDailyLogSmartCard: true,
    })
    useOpsRuntimeMock.mockReturnValue({
      topAlerts: [],
      summary: { open_alerts: 0, exceptions_count: 0 },
      localOfflineSignals: {
        queuedRequests: 0,
        queuedHarvests: 0,
        queuedDailyLogs: 0,
        queuedCustody: 0,
        failedRequests: 0,
        failedHarvests: 0,
        failedDailyLogs: 0,
        failedCustody: 0,
        lastSync: '2026-04-11T10:00:00.000Z',
      },
    })
    useOfflineQueueMock.mockReturnValue({
      queuedRequests: 0,
      queuedHarvests: 0,
      queuedDailyLogs: 0,
      queuedCustody: 0,
      failedRequests: 0,
      failedHarvests: 0,
      failedDailyLogs: 0,
      failedCustody: 0,
      syncing: false,
      lastSync: '2026-04-11T10:00:00.000Z',
    })
  })

  it('falls back to reports for financial posture when finance hub is not visible to the user', () => {
    useAuthMock.mockReturnValue({
      isAdmin: false,
      isSuperuser: false,
      hasFarmRole: () => false,
    })

    render(
      <MemoryRouter>
        <SimpleOperationsHub />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-hub-card-financial-posture-cta').getAttribute('href')).toBe(
      '/reports',
    )
  })

  it('links financial posture to the finance hub for finance-capable SIMPLE users', () => {
    useAuthMock.mockReturnValue({
      isAdmin: true,
      isSuperuser: false,
      hasFarmRole: () => false,
    })

    render(
      <MemoryRouter>
        <SimpleOperationsHub />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-hub-card-financial-posture-cta').getAttribute('href')).toBe(
      '/finance',
    )
  })
})
