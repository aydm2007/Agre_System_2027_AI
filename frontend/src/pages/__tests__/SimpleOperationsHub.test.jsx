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

describe('SimpleOperationsHub', () => {
  const baseFarmContext = {
    farms: [{ id: '11', name: 'الربوعية' }],
    selectedFarmId: '11',
    selectFarm: vi.fn(),
  }

  const baseSettings = {
    modeLabel: 'SIMPLE',
    isStrictMode: false,
    showDailyLogSmartCard: true,
  }

  const baseOffline = {
    queuedRequests: 0,
    queuedHarvests: 1,
    queuedDailyLogs: 2,
    queuedCustody: 1,
    failedRequests: 0,
    failedHarvests: 0,
    failedDailyLogs: 0,
    failedCustody: 0,
    syncing: false,
    lastSync: '2026-04-11T10:00:00.000Z',
  }

  const baseOps = {
    topAlerts: [{ title: 'تنبيه انحراف مفتوح' }],
    summary: { open_alerts: 2, exceptions_count: 0 },
    localOfflineSignals: baseOffline,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue(baseFarmContext)
    useSettingsMock.mockReturnValue(baseSettings)
    useOpsRuntimeMock.mockReturnValue(baseOps)
    useOfflineQueueMock.mockReturnValue(baseOffline)
    useAuthMock.mockReturnValue({
      isAdmin: false,
      isSuperuser: false,
      hasFarmRole: () => false,
    })
  })

  it('renders the six SIMPLE operational cards as one integrated entry surface', () => {
    render(
      <MemoryRouter>
        <SimpleOperationsHub />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-hub-title').textContent).toContain('مركز العمليات')
    expect(screen.getByTestId('simple-hub-mode-badge').textContent).toContain('SIMPLE')
    expect(screen.getByTestId('simple-hub-card-daily-log')).toBeTruthy()
    expect(screen.getByTestId('simple-hub-card-harvest')).toBeTruthy()
    expect(screen.getByTestId('simple-hub-card-custody')).toBeTruthy()
    expect(screen.getByTestId('simple-hub-card-variance')).toBeTruthy()
    expect(screen.getByTestId('simple-hub-card-reports')).toBeTruthy()
    expect(screen.getByTestId('simple-hub-card-financial-posture')).toBeTruthy()
  })
})
