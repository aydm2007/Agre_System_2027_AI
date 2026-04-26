import { describe, expect, it } from 'vitest'

import { buildAdvancedReportParams, buildTreeFilters } from '../reportParams'

describe('reportParams', () => {
  it('builds advanced report params with season and scoped tree filters', () => {
    const filters = {
      start: '2026-01-01',
      end: '2026-01-31',
      farm: '4',
      season: '19',
      location_id: '14',
      crop_id: '2',
      task_id: '8',
      variety_id: '3',
      status_code: 'productive',
    }

    expect(buildTreeFilters(filters)).toEqual({
      farm_id: '4',
      location_id: '14',
      variety_id: '3',
      status_code: 'productive',
    })

    expect(buildAdvancedReportParams(filters)).toEqual({
      start: '2026-01-01',
      end: '2026-01-31',
      farm_id: '4',
      season_id: '19',
      location_id: '14',
      crop_id: '2',
      task_id: '8',
      include_tree_inventory: true,
      tree_filters: JSON.stringify({
        farm_id: '4',
        location_id: '14',
        variety_id: '3',
        status_code: 'productive',
      }),
    })
  })
})
