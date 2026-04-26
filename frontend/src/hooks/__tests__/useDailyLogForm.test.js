import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'

import { useDailyLogForm } from '../useDailyLogForm'

const saveDraftMock = vi.fn()
const loadDraftMock = vi.fn()
const loadDraftsMock = vi.fn()
const clearDraftMock = vi.fn()
const queueLogSubmissionMock = vi.fn()

vi.mock('../useDailyLogOffline', () => ({
  useDailyLogOffline: () => ({
    saveDraft: saveDraftMock,
    loadDraft: loadDraftMock,
    loadDrafts: loadDraftsMock,
    clearDraft: clearDraftMock,
    queueLogSubmission: queueLogSubmissionMock,
    isOnline: true,
  }),
}))

describe('useDailyLogForm', () => {
  beforeEach(() => {
    saveDraftMock.mockReset()
    loadDraftMock.mockReset()
    loadDraftsMock.mockReset()
    clearDraftMock.mockReset()
    queueLogSubmissionMock.mockReset()
    loadDraftMock.mockResolvedValue(null)
    loadDraftsMock.mockResolvedValue([])
    queueLogSubmissionMock.mockResolvedValue({ ok: true })
    window.scrollTo = vi.fn()
  })

  it('skips labor validation when labor step is disabled by task policy', () => {
    const { result } = renderHook(() =>
      useDailyLogForm(
        { date: '2026-03-21', farm: '1', locations: ['2'], task: '3' },
        {
          requireLaborStep: false,
          laborPolicy: {
            registeredAllowed: false,
            casualBatchAllowed: false,
            surrahRequired: false,
          },
        },
      ),
    )

    act(() => {
      result.current.setStep(2)
    })
    act(() => {
      result.current.nextStep()
    })

    expect(result.current.errors.team).toBeUndefined()
    expect(result.current.errors.surrah_count).toBeUndefined()
    expect(result.current.step).toBe(3)
  })

  it('enforces labor mode policy during validation', () => {
    const { result } = renderHook(() =>
      useDailyLogForm(
        {
          date: '2026-03-21',
          farm: '1',
          locations: ['2'],
          task: '3',
          labor_entry_mode: 'REGISTERED',
          team: [],
          surrah_count: '1.0',
        },
        {
          requireLaborStep: true,
          laborPolicy: {
            registeredAllowed: false,
            casualBatchAllowed: true,
            surrahRequired: true,
          },
        },
      ),
    )

    act(() => {
      result.current.setStep(2)
    })
    act(() => {
      result.current.nextStep()
    })

    expect(result.current.errors.labor_entry_mode).toBe('هذه المهمة لا تسمح بإدخال عمالة مسجلة.')
  })

  it('scrubs stale labor payload when labor card is disabled', () => {
    const { result } = renderHook(() =>
      useDailyLogForm(
        {
          labor_entry_mode: 'REGISTERED',
          team: ['11', '12'],
          casual_workers_count: '7',
          surrah_count: '1.5',
        },
        {
          requireLaborStep: false,
          laborPolicy: {
            registeredAllowed: false,
            casualBatchAllowed: false,
            surrahRequired: false,
          },
        },
      ),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.team).toEqual([])
    expect(payload.employees).toEqual([])
    expect(payload.employees_payload).toEqual([])
    expect(payload.casual_workers_count).toBe('')
  })

  it('removes backend-owned cost and read-only fields from submitted payloads', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        farm: '21',
        crop: '8',
        task: '15',
        cost_materials: '123.1234567',
        cost_total: '456.9999999',
        smart_card_stack: [{ card_key: 'materials' }],
        log_details: { id: 5 },
      }),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.cost_materials).toBeUndefined()
    expect(payload.cost_total).toBeUndefined()
    expect(payload.smart_card_stack).toBeUndefined()
    expect(payload.log_details).toBeUndefined()
    expect(payload.farm).toBe('21')
    expect(payload.crop).toBe('8')
    expect(payload.task).toBe('15')
  })

  it('builds registered labor payload when registered labor is allowed', () => {
    const { result } = renderHook(() =>
      useDailyLogForm(
        {
          labor_entry_mode: 'REGISTERED',
          team: ['11', '12'],
          surrah_count: '2',
        },
        {
          requireLaborStep: true,
          laborPolicy: {
            registeredAllowed: true,
            casualBatchAllowed: false,
            surrahRequired: true,
          },
        },
      ),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.employees).toEqual(['11', '12'])
    expect(payload.employees_payload).toHaveLength(2)
    expect(payload.employees_payload[0].labor_type).toBe('REGISTERED')
  })

  it('normalizes item wastage payloads for offline replay', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        items: [
          {
            item: '9',
            qty: '3',
            applied_qty: '2',
            waste_qty: '1',
            waste_reason: 'spill',
            uom: 'kg',
          },
        ],
      }),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.items_payload).toEqual([
      {
        item_id: 9,
          qty: '3',
          applied_qty: '2',
          waste_qty: '1',
        waste_reason: 'spill',
        uom: 'kg',
        batch_number: undefined,
      },
    ])
  })

  it('builds service coverage payload with distribution fields', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        serviceRows: [
          {
            varietyId: '4',
            locationId: '6',
            serviceCount: '10',
            distributionMode: 'exception_weighted',
            distributionFactor: '1.75',
          },
        ],
      }),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.service_counts_payload).toEqual([
      {
        variety_id: 4,
        location_id: 6,
        service_count: '10',
        service_type: 'general',
        service_scope: 'location',
        distribution_mode: 'exception_weighted',
        distribution_factor: '1.75',
        notes: '',
      },
    ])
  })

  it('starts a new draft while preserving core daily context', async () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        farm: '1',
        date: '2026-04-12',
        crop: '9',
        locations: ['5'],
      }),
    )

    const firstDraft = result.current.form.draft_uuid
    await act(async () => {
      await result.current.startNewDraft({ preserveContext: true })
    })

    expect(result.current.form.draft_uuid).not.toBe(firstDraft)
    expect(result.current.form.farm).toBe('1')
    expect(result.current.form.date).toBe('2026-04-12')
    expect(result.current.form.crop).toBe('9')
    expect(result.current.form.locations).toEqual(['5'])
  })

  it('resumes a saved draft by id', async () => {
    loadDraftMock.mockResolvedValueOnce({
      draft_uuid: 'draft-55',
      data: {
        farm: '7',
        date: '2026-04-13',
        crop: '3',
      },
    })

    const { result } = renderHook(() => useDailyLogForm())

    await act(async () => {
      await result.current.resumeDraft('draft-55')
    })

    expect(result.current.form.draft_uuid).toBe('draft-55')
    expect(result.current.form.farm).toBe('7')
    expect(result.current.form.crop).toBe('3')
  })

  it('scrubs diesel_qty when is_solar_powered is true', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        is_solar_powered: true,
        diesel_qty: '15.5',
        water_volume: '200',
        well_id: '3',
      }),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.is_solar_powered).toBe(true)
    expect(payload.diesel_qty).toBeNull()
    expect(payload.water_volume).toBe('200')
  })

  it('preserves diesel_qty when is_solar_powered is false', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        is_solar_powered: false,
        diesel_qty: '22.5',
        water_volume: '100',
      }),
    )

    const payload = result.current.scrubPayload(result.current.form)

    expect(payload.is_solar_powered).toBe(false)
    expect(payload.diesel_qty).toBe('22.5')
    expect(payload.water_volume).toBe('100')
  })

  it('resets solar/diesel fields when task changes', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        is_solar_powered: true,
        diesel_qty: '10',
        well_id: '5',
        task: '1',
      }),
    )

    act(() => {
      result.current.updateField('task', '2')
    })

    expect(result.current.form.is_solar_powered).toBe(false)
    expect(result.current.form.diesel_qty).toBe('')
    expect(result.current.form.well_id).toBe('')
  })

  it('includes solar fields in draft payload for offline resume', () => {
    const { result } = renderHook(() =>
      useDailyLogForm({
        farm: '1',
        date: '2026-04-13',
        is_solar_powered: true,
        diesel_qty: '',
        water_volume: '300',
      }),
    )

    // Verify form state includes solar fields
    expect(result.current.form.is_solar_powered).toBe(true)
    expect(result.current.form.diesel_qty).toBe('')
    expect(result.current.form.water_volume).toBe('300')

    // Verify scrubbed payload
    const payload = result.current.scrubPayload(result.current.form)
    expect(payload.is_solar_powered).toBe(true)
    expect(payload.diesel_qty).toBeNull()
  })
})
