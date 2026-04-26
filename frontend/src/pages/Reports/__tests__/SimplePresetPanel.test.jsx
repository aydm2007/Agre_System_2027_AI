import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const useSettingsMock = vi.fn()
const usePageFarmFilterMock = vi.fn()
const useReportFiltersMock = vi.fn()
const useReportDataMock = vi.fn()
const setSelectedSectionsMock = vi.fn()

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../../hooks/usePageFarmFilter', () => ({
  usePageFarmFilter: () => usePageFarmFilterMock(),
}))

vi.mock('../hooks/useReportFilters', () => ({
  useReportFilters: (...args) => useReportFiltersMock(...args),
}))

vi.mock('../hooks/useReportData', () => ({
  useReportData: (...args) => useReportDataMock(...args),
}))

vi.mock('../components/ReportFilters', () => ({ default: () => <div data-testid="report-filters" /> }))
vi.mock('../components/ReportSectionSelector', () => ({ default: () => <div data-testid="report-section-selector" /> }))
vi.mock('../components/KeyMetricsCard', () => ({ default: () => <div data-testid="key-metrics" /> }))
vi.mock('../components/FinancialRiskZone', () => ({ default: () => <div data-testid="risk-zone" /> }))
vi.mock('../components/ActivityCharts', () => ({ default: () => <div data-testid="activity-charts" /> }))
vi.mock('../components/TreeInsights', () => ({ default: () => <div data-testid="tree-insights" /> }))
vi.mock('../components/DetailedTables', () => ({ default: () => <div data-testid="detailed-tables" /> }))

import ReportsPage from '../index.jsx'

describe('ReportsPage SIMPLE preset panel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSettingsMock.mockReturnValue({
      isStrictMode: false,
      modeLabel: 'SIMPLE',
    })
    usePageFarmFilterMock.mockReturnValue({
      farmId: '11',
      setFarmId: vi.fn(),
      canUseAll: true,
    })
    useReportFiltersMock.mockReturnValue({
      filters: { farm: '11', crop_id: '', season: '', start: '', end: '' },
      handleFilterChange: vi.fn(),
      farms: [{ id: 11, name: 'الربوعية' }],
      locations: [],
      crops: [],
      tasks: [],
      varieties: [],
      treeStatuses: [],
      seasons: [],
    })
    useReportDataMock.mockReturnValue({
      summary: {},
      activities: [],
      treeSummary: [],
      treeEvents: [],
      loading: false,
      treeLoading: false,
      treeError: '',
      riskData: [],
      exporting: false,
      fetchReport: vi.fn(),
      handleExport: vi.fn(),
      exportJobs: [],
      exportTemplates: [],
      treeTotals: { status: {} },
      materialChart: null,
      machineryChart: null,
      reportPendingMessage: '',
      reportRefreshing: false,
      selectedSections: ['summary'],
      setSelectedSections: setSelectedSectionsMock,
      dataSourceMap: {},
      sectionStatusMap: {},
      hasStaleSections: false,
      toggleSection: vi.fn(),
    })
  })

  it('renders SIMPLE presets and applies the requested section set', () => {
    render(
      <MemoryRouter initialEntries={['/reports']}>
        <ReportsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('simple-report-presets-panel')).toBeTruthy()

    fireEvent.click(screen.getByTestId('simple-report-preset-custody_materials'))

    expect(setSelectedSectionsMock).toHaveBeenCalledWith([
      'summary',
      'activities',
      'charts',
      'detailed_tables',
    ])
  })
})
