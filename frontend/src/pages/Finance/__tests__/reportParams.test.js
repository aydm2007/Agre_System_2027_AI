import { describe, expect, it } from 'vitest'

import { buildAdvancedFinancialReportParams, buildCommercialReportParams } from '../reportParams'

describe('finance report params', () => {
  it('builds advanced financial report payload with unified start/end keys', () => {
    expect(
      buildAdvancedFinancialReportParams({
        farmId: '16',
        reportType: 'profitability_pdf',
        costCenterId: '7',
        cropPlanId: '11',
        start: '2026-01-01',
        end: '2026-01-31',
      }),
    ).toEqual({
      farm_id: '16',
      report_type: 'profitability_pdf',
      format: 'pdf',
      cost_center_id: '7',
      crop_plan_id: '11',
      start: '2026-01-01',
      end: '2026-01-31',
    })
  })

  it('builds commercial export params from visible dashboard filters', () => {
    expect(
      buildCommercialReportParams({
        farm: '5',
        location: '3',
        crop_plan: '8',
        crop: '2',
      }),
    ).toEqual({
      farm_id: '5',
      location_id: '3',
      crop_plan_id: '8',
      crop_id: '2',
      report_type: 'commercial_pdf',
      format: 'pdf',
    })
  })
})
