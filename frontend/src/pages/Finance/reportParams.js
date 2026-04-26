export function buildAdvancedFinancialReportParams({
  farmId,
  reportType,
  costCenterId,
  cropPlanId,
  start,
  end,
}) {
  const params = {
    farm_id: farmId || '',
    report_type: reportType || 'profitability_pdf',
    format: 'pdf',
  }
  if (costCenterId) params.cost_center_id = costCenterId
  if (cropPlanId) params.crop_plan_id = cropPlanId
  if (start) params.start = start
  if (end) params.end = end
  return params
}

export function buildCommercialReportParams(filterParams = {}) {
  return {
    farm_id: filterParams.farm || '',
    location_id: filterParams.location || '',
    crop_plan_id: filterParams.crop_plan || '',
    crop_id: filterParams.crop || '',
    report_type: 'commercial_pdf',
    format: 'pdf',
  }
}
