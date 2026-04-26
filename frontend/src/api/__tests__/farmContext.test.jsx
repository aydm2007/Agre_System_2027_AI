import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FarmProvider, useFarmContext } from '../farmContext'

const mockUseAuth = vi.fn()
const mockFarmsList = vi.fn()

vi.mock('../client', () => ({
  Farms: {
    list: (...args) => mockFarmsList(...args),
  },
  Crops: { list: vi.fn(), tasks: vi.fn() },
  Locations: { list: vi.fn() },
  Assets: { list: vi.fn() },
  LocationWells: { list: vi.fn() },
  CropVarieties: { list: vi.fn() },
  Activities: { teamSuggestions: vi.fn() },
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../../auth/contextBridge', () => ({
  getAuthContext: () => ({ user: { id: 99, username: 'tester' } }),
}))

vi.mock('idb-keyval', () => ({
  get: vi.fn().mockResolvedValue(null),
  set: vi.fn().mockResolvedValue(undefined),
  del: vi.fn().mockResolvedValue(undefined),
}))

function Probe() {
  const { farms, selectedFarmId, loading } = useFarmContext()
  return (
    <div>
      <div data-testid="loading">{String(loading)}</div>
      <div data-testid="farm-count">{String(farms.length)}</div>
      <div data-testid="selected-farm">{selectedFarmId || ''}</div>
    </div>
  )
}

describe('FarmProvider', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    mockFarmsList.mockReset()
  })

  it('does not request farms before authentication is ready', async () => {
    mockUseAuth.mockReturnValue({
      userFarms: [],
      isLoading: false,
      isAuthenticated: false,
    })

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <FarmProvider>
          <Probe />
        </FarmProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    expect(mockFarmsList).not.toHaveBeenCalled()
    expect(screen.getByTestId('farm-count').textContent).toBe('0')
    expect(screen.getByTestId('selected-farm').textContent).toBe('')
  })

  it('uses profile farms after authentication without refetching /farms', async () => {
    mockUseAuth.mockReturnValue({
      userFarms: [
        { farm_id: 30, farm_name: 'Farm 30' },
        { farm_id: 31, farm_name: 'Farm 31' },
      ],
      isLoading: false,
      isAuthenticated: true,
    })

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <FarmProvider>
          <Probe />
        </FarmProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByTestId('farm-count').textContent).toBe('2'))
    expect(mockFarmsList).not.toHaveBeenCalled()
    expect(screen.getByTestId('selected-farm').textContent).toBe('30')
  })

  it('falls back to /farms when authenticated profile farms are unavailable', async () => {
    mockUseAuth.mockReturnValue({
      userFarms: [],
      isLoading: false,
      isAuthenticated: true,
    })
    mockFarmsList.mockResolvedValue({
      data: {
        results: [{ id: 44, name: 'Fallback Farm' }],
      },
    })

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <FarmProvider>
          <Probe />
        </FarmProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByTestId('farm-count').textContent).toBe('1'))
    expect(mockFarmsList).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('selected-farm').textContent).toBe('44')
  })
})
