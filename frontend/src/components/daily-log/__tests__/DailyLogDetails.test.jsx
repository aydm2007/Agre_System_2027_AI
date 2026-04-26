import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../ActivityItemsField', () => ({
  ActivityItemsField: () => null,
}))

import { DailyLogDetails } from '../DailyLogDetails'

const baseLookups = {
  tasks: [
    {
      id: 1,
      name: 'خدمة أشجار',
      requires_tree_count: true,
      is_perennial_procedure: true,
    },
  ],
  locations: [
    { id: 1, name: 'الحقل أ' },
    { id: 2, name: 'الحقل ب' },
  ],
  varieties: [
    {
      id: 101,
      name: 'مانجو سكري',
      location_ids: [1, 2],
      available_in_all_locations: true,
      current_tree_count_total: 12,
    },
    {
      id: 102,
      name: 'موز ويليامز',
      location_ids: [1],
      available_in_all_locations: false,
      current_tree_count_total: 5,
    },
  ],
}

const basePerennialLogic = {
  addServiceRow: vi.fn(),
  removeServiceRow: vi.fn(),
  updateServiceRow: vi.fn(),
  getVarietyCount: (id, locationId) => {
    if (String(id) === '101') return locationId === '1' ? 7 : 5
    if (String(id) === '102') return 5
    return '?'
  },
  getVarietyLocationNames: (id) => {
    if (String(id) === '101') return ['الحقل أ', 'الحقل ب']
    if (String(id) === '102') return ['الحقل أ']
    return []
  },
  stats: {
    totalTreeCount: 17,
    totalCohortAlive: 15,
    perennialVarietySummary: [
      {
        varietyId: '101',
        varietyName: 'مانجو سكري',
        locationIds: ['1', '2'],
        locationNames: ['الحقل أ', 'الحقل ب'],
        locationNamesById: { '1': 'الحقل أ', '2': 'الحقل ب' },
        availableInAllLocations: true,
        currentTreeCountTotal: 12,
        currentTreeCountByLocation: { '1': 7, '2': 5 },
        cohortAliveTotal: 10,
        cohortAliveByLocation: { '1': 6, '2': 4 },
        cohortStockDelta: -2,
        hasReconciliationGap: true,
        mappedCountTotal: 3,
        mappedCountByLocation: { '1': 2, '2': 1 },
        coverageLabel: 'متاح في كل المواقع المختارة',
      },
      {
        varietyId: '102',
        varietyName: 'موز ويليامز',
        locationIds: ['1'],
        locationNames: ['الحقل أ'],
        locationNamesById: { '1': 'الحقل أ' },
        availableInAllLocations: false,
        currentTreeCountTotal: 5,
        currentTreeCountByLocation: { '1': 5 },
        cohortAliveTotal: 5,
        cohortAliveByLocation: { '1': 5 },
        cohortStockDelta: 0,
        hasReconciliationGap: false,
        mappedCountTotal: 1,
        mappedCountByLocation: { '1': 1 },
        coverageLabel: 'متاح في: الحقل أ',
      },
    ],
  },
}

describe('DailyLogDetails perennial flow', () => {
  it('renders location-aware perennial stats and reconciliation details', () => {
    render(
      <DailyLogDetails
        form={{
          task: '1',
          locations: ['1', '2'],
          serviceRows: [{ key: 'row-1', varietyId: '101', locationId: '1', serviceCount: '2', notes: '' }],
          tree_count_delta: 0,
          activity_tree_count: '',
        }}
        updateField={vi.fn()}
        lookups={baseLookups}
        perennialLogic={basePerennialLogic}
      />,
    )

    expect(screen.getByText('إحصائيات الأصناف في المواقع المختارة')).toBeTruthy()
    expect(screen.getByText(/الرصيد الجاري: 17/)).toBeTruthy()
    expect(screen.getByText(/الدفعات الحية: 15/)).toBeTruthy()
    expect(screen.getByTitle('مانجو سكري')).toBeTruthy()
    expect(screen.getByText('الحقل أ، الحقل ب')).toBeTruthy()
    expect(screen.getByText('الحقل أ: 2/7')).toBeTruthy()
    expect(screen.getByText('الحقل ب: 1/5')).toBeTruthy()
    expect(screen.getByText(/إجمالي الدفعات الحية: 10/)).toBeTruthy()
    expect(screen.getByText(/فجوة بين الجرد الجاري والدفعات: -2/)).toBeTruthy()
  })

  it('renders a row-level location selector for multi-location perennial rows', () => {
    const updateServiceRow = vi.fn()

    render(
      <DailyLogDetails
        form={{
          task: '1',
          locations: ['1', '2'],
          serviceRows: [{ key: 'row-1', varietyId: '', locationId: '', serviceCount: '1', notes: '' }],
          tree_count_delta: 0,
          activity_tree_count: '',
        }}
        updateField={vi.fn()}
        lookups={baseLookups}
        perennialLogic={{ ...basePerennialLogic, updateServiceRow }}
      />,
    )

    const locationSelect = screen.getByTestId('service-row-location-row-1')
    fireEvent.change(locationSelect, { target: { value: '2' } })

    expect(updateServiceRow).toHaveBeenCalledWith('row-1', 'locationId', '2')
    expect(screen.getAllByText('الحقل أ').length).toBeGreaterThan(0)
    expect(screen.getAllByText('الحقل ب').length).toBeGreaterThan(0)
  })

  it('shows location-aware labels for partially covered varieties before row location is selected', () => {
    render(
      <DailyLogDetails
        form={{
          task: '1',
          locations: ['1', '2'],
          serviceRows: [{ key: 'row-1', varietyId: '', locationId: '', serviceCount: '1', notes: '' }],
          tree_count_delta: 0,
          activity_tree_count: '',
        }}
        updateField={vi.fn()}
        lookups={baseLookups}
        perennialLogic={basePerennialLogic}
      />,
    )

    expect(screen.getByText(/موز ويليامز - متاح في: الحقل أ/)).toBeTruthy()
    expect(screen.queryByText(/في 1 موقع/)).toBeNull()
  })

  it('filters service-row write options to crop-scoped varieties only', () => {
    render(
      <DailyLogDetails
        form={{
          crop: '501',
          task: '1',
          locations: ['1'],
          serviceRows: [{ key: 'row-1', varietyId: '', locationId: '1', serviceCount: '1', notes: '' }],
          tree_count_delta: 1,
          activity_tree_count: '',
        }}
        updateField={vi.fn()}
        lookups={{
          ...baseLookups,
          varieties: [
            {
              id: 5011,
              crop: 501,
              name: 'مانجو معتمد',
              location_ids: [1],
              available_in_all_locations: true,
              current_tree_count_total: 12,
            },
            {
              id: 5012,
              crop: null,
              name: 'Legacy Null Crop',
              location_ids: [1],
              available_in_all_locations: true,
              current_tree_count_total: 8,
            },
            {
              id: 5013,
              crop: 999,
              name: 'Cross Crop Variety',
              location_ids: [1],
              available_in_all_locations: true,
              current_tree_count_total: 6,
            },
          ],
        }}
        perennialLogic={basePerennialLogic}
      />,
    )

    const varietySelect = screen.getByTestId('service-row-variety-row-1')
    const optionLabels = Array.from(varietySelect.querySelectorAll('option')).map((option) => option.textContent)

    expect(optionLabels).toContain('مانجو معتمد')
    expect(optionLabels).not.toContain('Legacy Null Crop')
    expect(optionLabels).not.toContain('Cross Crop Variety')
  })
})
