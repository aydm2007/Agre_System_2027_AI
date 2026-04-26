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

describe('SimpleOperationsHub offline posture', () => {
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
    useAuthMock.mockReturnValue({
      isAdmin: false,
      isSuperuser: false,
      hasFarmRole: () => false,
    })
  })

  it('shows waiting-to-send status when queued operational items exist', () => {
    const offlineState = {
      queuedRequests: 0,
      queuedHarvests: 1,
      queuedDailyLogs: 2,
      queuedCustody: 1,
      failedRequests: 0,
      failedHarvests: 0,
      failedDailyLogs: 0,
      failedCustody: 0,
      lastSync: '2026-04-11T10:00:00.000Z',
    }
    useOpsRuntimeMock.mockReturnValue({
      topAlerts: [],
      summary: {},
      localOfflineSignals: offlineState,
    })
    useOfflineQueueMock.mockReturnValue({ ...offlineState, syncing: false })

    render(
      <MemoryRouter>
        <SimpleOperationsHub />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-hub-sync-badge').textContent).toContain('بانتظار الإرسال')
  })

  it('shows conflict status when failed offline items exist', () => {
    const offlineState = {
      queuedRequests: 0,
      queuedHarvests: 0,
      queuedDailyLogs: 0,
      queuedCustody: 0,
      failedRequests: 0,
      failedHarvests: 1,
      failedDailyLogs: 1,
      failedCustody: 0,
      lastSync: '2026-04-11T10:00:00.000Z',
    }
    useOpsRuntimeMock.mockReturnValue({
      topAlerts: [],
      summary: {},
      localOfflineSignals: offlineState,
    })
    useOfflineQueueMock.mockReturnValue({ ...offlineState, syncing: false })

    render(
      <MemoryRouter>
        <SimpleOperationsHub />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-hub-sync-badge').textContent).toContain('يوجد تعارض')
  })
})
