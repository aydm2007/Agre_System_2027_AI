import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DetailedTables from '../DetailedTables'

describe('DetailedTables', () => {
  it('renders export catalog and uses scoped export actions', () => {
    const handleExport = vi.fn()

    render(
      <DetailedTables
        summary={{ locations: [{ id: 1, name: 'الموقع أ', total_hours: 4, harvest_total_qty: 8 }] }}
        activities={[
          {
            id: 1,
            log_date: '2026-04-03',
            location: { name: 'الموقع أ' },
            crop: { name: 'قمح' },
            task: { name: 'ري' },
            hours: 2,
            machine_hours: 1,
            well_reading: 12,
          },
        ]}
        loading={false}
        exporting={false}
        handleExport={handleExport}
        exportTemplates={[
          {
            export_type: 'daily_execution_summary',
            title: 'ملخص التنفيذ اليومي',
            description: 'تنفيذ يومي بحسب المزرعة والموقع والمحصول',
            report_group: 'execution',
            mode_scope: 'all',
            sensitivity_level: 'operational',
            formats: ['xlsx', 'json'],
          },
          {
            export_type: 'plan_actual_variance',
            title: 'الخطة مقابل الفعلي والانحراف',
            description: 'انحرافات التنفيذ والمدخلات',
            report_group: 'variance',
            mode_scope: 'all',
            sensitivity_level: 'operational',
            formats: ['xlsx'],
          },
        ]}
        exportJobs={[
          {
            id: 8,
            status: 'running',
            format: 'xlsx',
            output_filename: 'daily.xlsx',
            metadata: { report_group: 'execution' },
          },
          {
            id: 9,
            status: 'completed',
            format: 'json',
            output_filename: 'daily.json',
            metadata: { report_group: 'variance' },
          },
        ]}
        reportPendingMessage="التقرير قيد التجهيز، ستظهر النتائج فور اكتمال المعالجة."
        reportRefreshing
        selectedSections={['summary', 'detailed_tables', 'activities']}
        sectionStatusMap={{ detailed_tables: 'ready', activities: 'ready' }}
        canUseJsonExports
      />,
    )

    expect(screen.getByTestId('report-export-catalog')).toBeTruthy()
    expect(screen.getByTestId('detailed-report-pending-banner')).toBeTruthy()
    expect(screen.getAllByText('تقارير التنفيذ اليومي').length).toBeGreaterThan(0)
    expect(screen.getAllByText('تقارير الخطة والانحراف').length).toBeGreaterThan(0)
    expect(screen.getByText('ملخص التنفيذ اليومي')).toBeTruthy()
    expect(screen.getByText('الخطة مقابل الفعلي والانحراف')).toBeTruthy()
    expect(screen.getByText('مهام التصدير')).toBeTruthy()
    expect(screen.getByText('قيد المعالجة')).toBeTruthy()
    expect(screen.getByText('مكتمل')).toBeTruthy()

    fireEvent.click(screen.getAllByRole('button', { name: 'تصدير Excel للأقسام المختارة' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'تصدير JSON للأقسام المختارة' }))

    expect(handleExport).toHaveBeenNthCalledWith(1, {
      exportType: 'daily_execution_summary',
      format: 'xlsx',
    })
    expect(handleExport).toHaveBeenNthCalledWith(2, {
      exportType: 'daily_execution_summary',
      format: 'json',
    })
  })

  it('hides json export controls when the current role is not allowed to use them', () => {
    render(
      <DetailedTables
        summary={{ locations: [] }}
        activities={[]}
        loading={false}
        exporting={false}
        handleExport={vi.fn()}
        exportTemplates={[
          {
            export_type: 'daily_execution_summary',
            title: 'ملخص التنفيذ اليومي',
            report_group: 'execution',
            mode_scope: 'all',
            sensitivity_level: 'operational',
            formats: ['xlsx', 'json'],
          },
        ]}
        selectedSections={['detailed_tables']}
        sectionStatusMap={{ detailed_tables: 'ready' }}
        canUseJsonExports={false}
      />,
    )

    expect(screen.queryByRole('button', { name: 'تصدير JSON للأقسام المختارة' })).toBeNull()
    expect(screen.getByText('XLSX أساسي')).toBeTruthy()
  })
})
