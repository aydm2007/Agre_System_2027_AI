/**
 * [AGRI-GUARDIAN] Test Fixtures for E2E Tests
 * Provides consistent test data for all E2E test scenarios.
 */

export const testFarm = {
  id: 1,
  name: 'مزرعة الاختبار',
  area: 1000,
  area_unit: 'sqm',
}

export const testLocation = {
  id: 1,
  name: 'موقع A - شمال',
  farm: 1,
  area: 500,
  location_type: 'FIELD',
}

export const testCrop = {
  id: 1,
  name: 'قمح اختبار',
  farm: 1,
  variety: 'محلي',
  is_perennial: false,
}

export const testTask = {
  id: 1,
  name: 'ري بالتنقيط',
  stage: 'الري',
  crop: 1,
  requires_well: true,
  requires_machinery: false,
  is_harvest_task: false,
  is_perennial_procedure: false,
}

export const testTaskHarvest = {
  id: 2,
  name: 'حصاد آلي',
  stage: 'الحصاد',
  crop: 1,
  requires_well: false,
  requires_machinery: true,
  is_harvest_task: true,
  is_perennial_procedure: false,
}

export const testTaskPerennial = {
  id: 3,
  name: 'تقليم الأشجار',
  stage: 'الخدمة',
  crop: 1,
  requires_well: false,
  requires_machinery: false,
  is_harvest_task: false,
  is_perennial_procedure: true,
}

export const testWell = {
  id: 1,
  name: 'بئر 1',
  location: 1,
  asset_type: 'WELL',
  last_meter_reading: 12500,
}

export const testMaterial = {
  id: 1,
  name: 'سماد NPK',
  uom: 'kg',
  unit_price: 50,
}

export const testTeamMember = {
  id: 1,
  name: 'محمد أحمد',
  role: 'عامل',
}

// Daily Log form fixture
export const testDailyLogForm = {
  log_date: '2026-02-03',
  farm: testFarm.id,
  location: testLocation.id,
  crop: testCrop.id,
  task: testTask.id,
  team_names: ['محمد', 'علي'],
  hours: 4,
  notes: 'ملاحظات الاختبار',
  well_id: testWell.id,
  meter_reading: 12550,
  water_volume: 500,
}

// API mock responses
export const mockApiResponses = {
  farms: { results: [testFarm] },
  locations: { results: [testLocation] },
  crops: { results: [testCrop] },
  tasks: { results: [testTask, testTaskHarvest, testTaskPerennial] },
  wells: { results: [testWell] },
  materials: { results: [testMaterial] },
  teamMembers: { results: [testTeamMember] },
}

/**
 * Setup mock API routes for Playwright page
 * @param {import('@playwright/test').Page} page
 */
export async function setupMockApi(page) {
  // Mock farms endpoint
  await page.route('**/api/farms/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.farms),
    })
  })

  // Mock locations endpoint
  await page.route('**/api/locations/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.locations),
    })
  })

  // Mock crops endpoint
  await page.route('**/api/crops/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.crops),
    })
  })

  // Mock tasks endpoint
  await page.route('**/api/tasks/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.tasks),
    })
  })

  // Mock wells endpoint
  await page.route('**/api/wells/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiResponses.wells),
    })
  })

  // Mock activities endpoint (for submission)
  await page.route('**/api/activities/**', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 999, ...testDailyLogForm }),
      })
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [] }),
      })
    }
  })
}
