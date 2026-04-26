import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const exportTemplates = vi.fn()
const exportList = vi.fn()
const exportCreate = vi.fn()
const exportStatus = vi.fn()
const exportDownload = vi.fn()
const importTemplates = vi.fn()
const importList = vi.fn()
const importDownloadTemplate = vi.fn()
const importUpload = vi.fn()
const importValidate = vi.fn()
const importApply = vi.fn()
const importDownloadErrors = vi.fn()

vi.mock('../../../api/client', () => ({
  ExportJobs: {
    templates: (...args) => exportTemplates(...args),
    list: (...args) => exportList(...args),
    create: (...args) => exportCreate(...args),
    status: (...args) => exportStatus(...args),
    download: (...args) => exportDownload(...args),
  },
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

import InventoryImportExportCenter from '../InventoryImportExportCenter'

describe('InventoryImportExportCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    exportTemplates.mockResolvedValue({
      data: {
        results: [
          {
            export_type: 'inventory_balance',
            title: 'رصيد المخزون الحالي',
            description: 'رصيد المخزون التشغيلي الحالي',
            mode_scope: 'all',
            sensitivity_level: 'operational',
            ui_surface: 'inventory_center',
            formats: ['xlsx', 'json'],
          },
        ],
      },
    })
    exportList.mockResolvedValue({
      data: {
        results: [
          {
            id: 7,
            status: 'completed',
            output_filename: 'inventory-balance.xlsx',
            metadata: { export_type: 'inventory_balance' },
          },
        ],
      },
    })
    importTemplates.mockResolvedValue({
      data: {
        results: [
          {
            code: 'inventory_operational_adjustment',
            title: 'قالب تسوية تشغيلية للمخزون',
            description: 'تسويات تشغيلية آمنة',
            mode_scope: 'mode_aware_operational',
          },
        ],
      },
    })
    importList.mockResolvedValue({
      data: {
        results: [
          {
            id: 4,
            template_code: 'inventory_count_sheet',
            status: 'preview_ready',
            row_count: 3,
            applied_count: 0,
            rejected_count: 1,
          },
        ],
      },
    })
    exportCreate.mockResolvedValue({
      data: {
        id: 11,
        status: 'pending',
        output_filename: '',
        format: 'xlsx',
      },
    })
    exportStatus.mockResolvedValue({
      data: {
        id: 11,
        status: 'completed',
        output_filename: 'inventory-balance.xlsx',
        format: 'xlsx',
      },
    })
    exportDownload.mockResolvedValue({ data: new Blob(['xlsx']) })
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
        preview_rows: [{ excel_row: 2, severity: 'ok', messages: [], item_name: 'سماد' }],
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
        preview_rows: [{ excel_row: 2, severity: 'ok', messages: [], item_name: 'سماد' }],
        error_workbook_url: '',
      },
    })
  })

  it('renders inventory export catalog and exports balance as xlsx through async jobs', async () => {
    const addToast = vi.fn()
    const createObjectURL = vi.fn(() => 'blob:export')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const originalCreateObjectURL = window.URL.createObjectURL
    const originalRevokeObjectURL = window.URL.revokeObjectURL
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    render(
      <InventoryImportExportCenter
        farmId="7"
        filters={{ item: '3', location: '5' }}
        addToast={addToast}
      />,
    )

    await screen.findByText('رصيد المخزون الحالي')
    expect(screen.getByTestId('inventory-export-catalog')).toBeTruthy()
    expect(screen.getByText('سجل التصدير')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'تصدير Excel' }))

    await waitFor(() =>
      expect(exportCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          export_type: 'inventory_balance',
          format: 'xlsx',
          farm_id: '7',
          item: '3',
          location: '5',
          locale: 'ar-YE',
          rtl: true,
        }),
      ),
    )
    await waitFor(() => expect(exportDownload).toHaveBeenCalledWith(11))
    expect(click).toHaveBeenCalledTimes(1)
    expect(createObjectURL).toHaveBeenCalled()

    click.mockRestore()
    window.URL.createObjectURL = originalCreateObjectURL
    window.URL.revokeObjectURL = originalRevokeObjectURL
  })

  it('downloads template then validates and applies the import job', async () => {
    const addToast = vi.fn()
    const onImportApplied = vi.fn()
    const createObjectURL = vi.fn(() => 'blob:file')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const originalCreateObjectURL = window.URL.createObjectURL
    const originalRevokeObjectURL = window.URL.revokeObjectURL
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    const { container } = render(
      <InventoryImportExportCenter
        farmId="8"
        filters={{}}
        addToast={addToast}
        onImportApplied={onImportApplied}
      />,
    )

    await screen.findByText('قالب تسوية تشغيلية للمخزون')
    expect(screen.getByText('سجل الاستيراد')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'تنزيل القالب' }))
    await waitFor(() =>
      expect(importDownloadTemplate).toHaveBeenCalledWith(
        'inventory_operational_adjustment',
        expect.objectContaining({ farm_id: '8' }),
      ),
    )

    const file = new File(['xlsx'], 'inventory.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [file] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'رفع ملف Excel' }))

    await waitFor(() =>
      expect(importUpload).toHaveBeenCalledWith(
        expect.objectContaining({
          template_code: 'inventory_operational_adjustment',
          farm_id: '8',
          file,
        }),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'معاينة' }))
    await waitFor(() => expect(screen.getAllByText(/جاهز للتطبيق/).length).toBeGreaterThan(0))
    expect(screen.getByText('سماد')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'تطبيق' }))
    await waitFor(() => expect(importApply).toHaveBeenCalledWith(19))
    await waitFor(() => expect(onImportApplied).toHaveBeenCalledTimes(1))

    click.mockRestore()
    window.URL.createObjectURL = originalCreateObjectURL
    window.URL.revokeObjectURL = originalRevokeObjectURL
  })
})
