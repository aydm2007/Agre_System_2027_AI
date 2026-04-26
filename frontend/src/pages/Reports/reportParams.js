export function buildTreeFilters(filters = {}) {
  const treeFilters = {}

  if (filters.farm) treeFilters.farm_id = filters.farm
  if (filters.location_id) treeFilters.location_id = filters.location_id
  if (filters.variety_id) treeFilters.variety_id = filters.variety_id
  if (filters.status_code) treeFilters.status_code = filters.status_code

  return treeFilters
}

export function buildAdvancedReportParams(filters = {}) {
  const treeFilters = buildTreeFilters(filters)

  return {
    start: filters.start || '',
    end: filters.end || '',
    farm_id: filters.farm || '',
    season_id: filters.season || '',
    location_id: filters.location_id || '',
    crop_id: filters.crop_id || '',
    task_id: filters.task_id || '',
    include_tree_inventory: Object.keys(treeFilters).length > 0 || Boolean(filters.include_tree_inventory),
    tree_filters: JSON.stringify(treeFilters),
  }
}

export function buildAdvancedReportParamsWithSections(filters = {}, sectionScope = ['summary']) {
  const normalizedSectionScope = Array.from(
    new Set((Array.isArray(sectionScope) ? sectionScope : ['summary']).filter(Boolean)),
  )
  const includeTreeInventory =
    normalizedSectionScope.includes('tree_summary') || normalizedSectionScope.includes('tree_events')

  return {
    start: filters.start || '',
    end: filters.end || '',
    farm_id: filters.farm || '',
    season_id: filters.season || '',
    location_id: filters.location_id || '',
    crop_id: filters.crop_id || '',
    task_id: filters.task_id || '',
    include_tree_inventory: includeTreeInventory,
    section_scope: normalizedSectionScope,
    tree_filters: JSON.stringify(buildTreeFilters(filters)),
  }
}
