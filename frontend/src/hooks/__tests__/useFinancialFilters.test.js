import { renderHook, waitFor, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildInitialFilters,
  buildOptions,
  cascadeNextFilters,
  createUseFinancialFilters,
  DIM,
  formatActivityOptionLabel,
  normalizeDimensions,
} from '../../hooks/useFinancialFiltersCore'

describe('useFinancialFilters', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('exports activity dimension and keeps crop_plan in snake_case', () => {
    expect(DIM.cropPlan).toBe('crop_plan')
    expect(DIM.activity).toBe('activity')
  })

  it('normalizes legacy cropPlan dimension aliases', () => {
    expect(normalizeDimensions(['farm', 'cropPlan', 'activity'])).toEqual([
      'farm',
      'crop_plan',
      'activity',
    ])
  })

  it('builds initial filters with auto-selected farm and URL state', () => {
    const searchParams = new URLSearchParams('location=9&period=2026-03')
    expect(
      buildInitialFilters({
        dimensions: ['farm', 'location', 'period'],
        syncToUrl: true,
        searchParams,
        autoSelectFarm: true,
        selectedFarmId: '3',
      }),
    ).toEqual({
      farm: '3',
      location: '9',
      period: '2026-03',
    })
  })

  it('clears downstream filters when a higher-order dimension changes', () => {
    expect(
      cascadeNextFilters(
        {
          farm: '3',
          location: '9',
          costCenter: '12',
          crop_plan: '137',
          activity: '501',
        },
        'location',
        '10',
      ),
    ).toEqual({
      farm: '3',
      location: '10',
      costCenter: '',
      crop_plan: '',
      activity: '',
    })
  })

  it('builds crop_plan and activity options under the expected keys', () => {
    const options = buildOptions({
      farms: [{ id: 3, name: 'Farm 3' }],
      cropPlanOptions: [{ id: 137, name: 'Plan 137' }],
      activityOptions: [
        {
          id: 501,
          task: { name: 'Spraying' },
          log_date: '2026-03-12',
          locations: [{ name: 'Block A' }],
        },
      ],
    })

    expect(options.farm).toEqual([{ value: '3', label: 'Farm 3' }])
    expect(options.crop_plan).toEqual([{ value: '137', label: 'Plan 137' }])
    expect(options.cropPlan).toEqual(options.crop_plan)
    expect(options.activity).toEqual([{ value: '501', label: 'Spraying - 2026-03-12 - Block A' }])
  })

  it('formats activity labels from fallback shapes', () => {
    expect(
      formatActivityOptionLabel({
        id: 22,
        task_name: 'Irrigation',
        location_name: 'Block B',
      }),
    ).toBe('Irrigation - Block B')

    expect(formatActivityOptionLabel({ id: 23, date: '2026-03-15' })).toBe('2026-03-15')
  })

  it('does not refetch locations and crops on rerender when dimensions values stay the same', async () => {
    const api = {
      get: vi.fn((url) => {
        if (url === '/locations/') {
          return Promise.resolve({ data: { results: [{ id: 1, name: 'Block A' }] } })
        }
        if (url === '/crops/') {
          return Promise.resolve({ data: { results: [{ id: 9, name: 'Wheat' }] } })
        }
        return Promise.resolve({ data: { results: [] } })
      }),
    }
    const useFinancialFilters = createUseFinancialFilters({
      api,
      useFarmContext: () => ({
        farms: [{ id: '30', name: 'Farm 30' }],
        selectedFarmId: '30',
      }),
      useSearchParamsHook: () => [new URLSearchParams(), vi.fn()],
    })

    const { rerender } = renderHook(
      ({ dimensions }) => useFinancialFilters({ dimensions }),
      { initialProps: { dimensions: ['farm', 'location', 'crop'] } },
    )

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2))
    expect(api.get).toHaveBeenNthCalledWith(1, '/locations/', {
      params: { farm_id: '30', page_size: 500 },
    })
    expect(api.get).toHaveBeenNthCalledWith(2, '/crops/', {
      params: { farm_id: '30', page_size: 500 },
    })

    rerender({ dimensions: ['farm', 'location', 'crop'] })
    await act(async () => {
      await Promise.resolve()
    })
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('refetches crops only when crop_plan changes under the same farm scope', async () => {
    const api = {
      get: vi.fn((url) => {
        if (url === '/locations/') {
          return Promise.resolve({ data: { results: [{ id: 1, name: 'Block A' }] } })
        }
        if (url === '/crop-plans/') {
          return Promise.resolve({ data: { results: [{ id: 137, name: 'Plan 137' }] } })
        }
        if (url === '/crops/') {
          return Promise.resolve({ data: { results: [{ id: 9, name: 'Wheat' }] } })
        }
        return Promise.resolve({ data: { results: [] } })
      }),
    }
    const useFinancialFilters = createUseFinancialFilters({
      api,
      useFarmContext: () => ({
        farms: [{ id: '30', name: 'Farm 30' }],
        selectedFarmId: '30',
      }),
      useSearchParamsHook: () => [new URLSearchParams(), vi.fn()],
    })

    const { result } = renderHook(() =>
      useFinancialFilters({ dimensions: ['farm', 'location', 'crop_plan', 'crop'] }),
    )

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(3))
    act(() => {
      result.current.setFilter(DIM.cropPlan, '137')
    })
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(4))
    expect(api.get.mock.calls[3]).toEqual([
      '/crops/',
      { params: { farm_id: '30', crop_plan_id: '137', page_size: 500 } },
    ])
  })
})
