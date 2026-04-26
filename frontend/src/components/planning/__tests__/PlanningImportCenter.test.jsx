import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const importTemplates = vi.fn()
const importList = vi.fn()
const importDownloadTemplate = vi.fn()
const importUpload = vi.fn()
const importValidate = vi.fn()
const importApply = vi.fn()
const importDownloadErrors = vi.fn()

vi.mock('../../../api/client', () => ({
  ImportJobs: {
    templates: (...args) => importTemplates(...args),
    list: (...args) => importList(...args),
    downloadTemplate: (...args) => importDownloadTemplate(...args),
    upload: (...args) => importUpload(...args),
    validate: (...args) => importValidate(...args),
    apply: (...args) => importApply(...args),
    downloadErrors: (...args) => importDownloadErrors(...args),
  },
}))

import PlanningImportCenter from '../PlanningImportCenter'

describe('PlanningImportCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    importTemplates.mockResolvedValue({
      data: {
        results: [
          {
            code: 'planning_crop_plan_structure',
            title: 'استيراد الهيكل التشغيلي',
            description: 'هيكل تشغيلي',
            mode_scope: 'mode_aware_operational',
            requires_crop_plan: true,
            template_version: 'v1',
          },
        ],
      },
    })
    importList.mockResolvedValue({
      data: {
        results: [
          {
            id: 14,
            template_code: 'planning_crop_plan_structure',
            status: 'preview_ready',
            row_count: 3,
            applied_count: 0,
            rejected_count: 1,
            metadata: { crop_plan_id: 22 },
          },
        ],
      },
    })
    importDownloadTemplate.mockResolvedValue({ data: new Blob(['template']) })
    importUpload.mockResolvedValue({
      data: { id: 19, status: 'uploaded', preview_rows: [], error_workbook_url: '' },
    })
    importValidate.mockResolvedValue({
      data: {
        id: 19,
        status: 'approved_for_apply',
        row_count: 1,
        rejected_count: 0,
        applied_count: 0,
        preview_rows: [{ excel_row: 2, severity: 'ok', messages: [], task_name: 'حراثة' }],
        error_workbook_url: '',
      },
    })
    importApply.mockResolvedValue({
      data: {
        id: 19,
        status: 'applied',
        row_count: 1,
        rejected_count: 0,
        applied_count: 1,
        preview_rows: [{ excel_row: 2, severity: 'ok', messages: [], task_name: 'حراثة' }],
        error_workbook_url: '',
      },
    })
  })

  it('downloads template then uploads, previews, and applies a crop-plan-scoped import job', async () => {
    const addToast = vi.fn()
    const onApplied = vi.fn()
    const createObjectURL = vi.fn(() => 'blob:file')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const originalCreateObjectURL = window.URL.createObjectURL
    const originalRevokeObjectURL = window.URL.revokeObjectURL
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    const { container } = render(
      <PlanningImportCenter
        farmId="7"
        cropPlanId={22}
        templateCode="planning_crop_plan_structure"
        title="استيراد الهيكل التشغيلي"
        description="اختبار"
        onClose={() => {}}
        onApplied={onApplied}
        addToast={addToast}
      />,
    )

    await screen.findByText('استيراد الهيكل التشغيلي')
    expect(screen.getByText('سجل الاستيراد')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'تنزيل القالب' }))
    await waitFor(() =>
      expect(importDownloadTemplate).toHaveBeenCalledWith(
        'planning_crop_plan_structure',
        expect.objectContaining({ farm_id: '7', crop_plan_id: 22 }),
      ),
    )

    const file = new File(['xlsx'], 'planning.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [file] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'رفع ملف Excel' }))

    await waitFor(() =>
      expect(importUpload).toHaveBeenCalledWith(
        expect.objectContaining({
          template_code: 'planning_crop_plan_structure',
          farm_id: '7',
          crop_plan_id: 22,
          file,
        }),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'معاينة' }))
    await waitFor(() => expect(screen.getAllByText(/جاهز للتطبيق/).length).toBeGreaterThan(0))
    expect(screen.getByText('حراثة')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'تطبيق' }))
    await waitFor(() => expect(importApply).toHaveBeenCalledWith(19))
    await waitFor(() => expect(onApplied).toHaveBeenCalledTimes(1))

    click.mockRestore()
    window.URL.createObjectURL = originalCreateObjectURL
    window.URL.revokeObjectURL = originalRevokeObjectURL
  })

  it('shows unavailable state when the template is not allowed for the current mode', async () => {
    importTemplates.mockResolvedValueOnce({ data: { results: [] } })
    importList.mockResolvedValueOnce({ data: { results: [] } })

    render(
      <PlanningImportCenter
        farmId="9"
        cropPlanId={33}
        templateCode="planning_crop_plan_budget"
        title="استيراد ميزانية الخطة"
        description="اختبار"
        onClose={() => {}}
        onApplied={() => {}}
        addToast={vi.fn()}
      />,
    )

    await screen.findByText('هذا القالب غير متاح للمزرعة أو المود الحالي.')
    expect(screen.getByRole('button', { name: 'تنزيل القالب' }).disabled).toBe(true)
  })
})
