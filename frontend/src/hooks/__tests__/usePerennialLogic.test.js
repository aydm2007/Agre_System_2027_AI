import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { usePerennialLogic } from '../usePerennialLogic'

describe('usePerennialLogic', () => {
  it('builds location-aware display summaries with mapped counts per location', () => {
    const form = {
      locations: ['1', '2'],
      serviceRows: [
        { key: 'a', varietyId: '101', locationId: '1', serviceCount: '2' },
        { key: 'b', varietyId: '101', locationId: '2', serviceCount: '1' },
      ],
      task: '55',
      tree_count_delta: 0,
    }
    const lookups = {
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
          current_tree_count_by_location: { 1: 7, 2: 5 },
        },
      ],
      tasks: [{ id: 55, requires_tree_count: true, is_perennial_procedure: true }],
    }

    const { result } = renderHook(() =>
      usePerennialLogic(form, vi.fn(), lookups, true, {
        enabledCards: { perennial: true },
        requiredInputs: { requiresTreeCount: true, isPerennialProcedure: true },
      }),
    )

    const summary = result.current.getVarietyDisplaySummary('101')

    expect(summary.locationNames).toEqual(['الحقل أ', 'الحقل ب'])
    expect(summary.mappedCountTotal).toBe(3)
    expect(summary.mappedCountByLocation).toEqual({ '1': 2, '2': 1 })
    expect(summary.coverageLabel).toBe('متاح في كل المواقع المختارة')
    expect(result.current.getMappedCount('101', '1')).toBe(2)
  })

  it('keeps fallback varieties visible as generic options when location coverage is unavailable', () => {
    const form = {
      locations: ['1'],
      serviceRows: [],
      task: '55',
      tree_count_delta: 0,
    }
    const lookups = {
      locations: [{ id: 1, name: 'الحقل أ' }],
      varieties: [{ id: 101, name: 'مانجو سكري' }],
      varietiesMeta: {
        usedFallback: true,
        emptyReason:
          'تعذر تحميل تغطية الأصناف حسب الموقع، وتم عرض أصناف المحصول المتاحة كقائمة احتياطية.',
        diagnostics: { varietiesCount: 1 },
      },
      tasks: [{ id: 55, requires_tree_count: true, is_perennial_procedure: true }],
    }

    const { result } = renderHook(() =>
      usePerennialLogic(form, vi.fn(), lookups, true, {
        enabledCards: { perennial: true },
        requiredInputs: { requiresTreeCount: true, isPerennialProcedure: true },
      }),
    )

    expect(result.current.stats.perennialVarietySummary).toHaveLength(1)
    expect(result.current.stats.usedFallback).toBe(true)
    expect(result.current.stats.emptyMessage).toContain('تعذر تحميل تغطية الأصناف حسب الموقع')
    expect(result.current.getVarietyDisplaySummary('101')?.coverageLabel).toBe(
      'صنف عام غير مرتبط بموقع محدد',
    )
  })

  it('prefers tree inventory summary and exposes reconciliation gap fields', () => {
    const form = {
      locations: ['2'],
      serviceRows: [{ key: 'a', varietyId: '202', locationId: '2', serviceCount: '3' }],
      task: '55',
      tree_count_delta: 0,
    }
    const lookups = {
      locations: [{ id: 2, name: 'الحقل ب' }],
      treeVarietySummary: [
        {
          variety_id: 202,
          variety_name: 'مانجو سوداني',
          location_ids: [2],
          available_in_all_locations: true,
          current_tree_count_total: 33,
          cohort_alive_total: 30,
          cohort_stock_delta: -3,
          has_reconciliation_gap: true,
          by_location: {
            2: {
              current_tree_count: 33,
              cohort_alive_total: 30,
              cohort_status_breakdown: { PRODUCTIVE: 30 },
            },
          },
        },
      ],
      tasks: [{ id: 55, requires_tree_count: true, is_perennial_procedure: true }],
    }

    const { result } = renderHook(() =>
      usePerennialLogic(form, vi.fn(), lookups, true, {
        enabledCards: { perennial: true },
        requiredInputs: { requiresTreeCount: true, isPerennialProcedure: true },
      }),
    )

    const summary = result.current.getVarietyDisplaySummary('202')
    expect(summary.currentTreeCountTotal).toBe(33)
    expect(summary.cohortAliveTotal).toBe(30)
    expect(summary.cohortStockDelta).toBe(-3)
    expect(summary.hasReconciliationGap).toBe(true)
    expect(summary.mappedCountTotal).toBe(3)
    expect(result.current.stats.totalCohortAlive).toBe(30)
  })

  it('falls back to cohort alive totals when current stock is zero but cohorts are alive', () => {
    const form = {
      locations: ['1'],
      serviceRows: [{ key: 'a', varietyId: '303', locationId: '1', serviceCount: '2' }],
      task: '55',
      tree_count_delta: 0,
    }
    const lookups = {
      locations: [{ id: 1, name: 'قطعة-1 مانجو مروي' }],
      treeVarietySummary: [
        {
          variety_id: 303,
          variety_name: 'السوداني',
          location_ids: [1],
          available_in_all_locations: true,
          current_tree_count_total: 0,
          cohort_alive_total: 232,
          cohort_stock_delta: 232,
          has_reconciliation_gap: true,
          by_location: {
            1: {
              current_tree_count: 0,
              cohort_alive_total: 232,
              cohort_status_breakdown: { PRODUCTIVE: 232 },
            },
          },
        },
      ],
      tasks: [{ id: 55, requires_tree_count: true, is_perennial_procedure: true }],
    }

    const { result } = renderHook(() =>
      usePerennialLogic(form, vi.fn(), lookups, true, {
        enabledCards: { perennial: true },
        requiredInputs: { requiresTreeCount: true, isPerennialProcedure: true },
      }),
    )

    expect(result.current.getVarietyCount('303', '1')).toBe(232)
    expect(result.current.getVarietyDisplaySummary('303').currentTreeCountTotal).toBe(232)
    expect(result.current.validatePerennialCompliance()).toBeNull()
  })

  it('allows positive tree delta service rows for a variety without prior location coverage', () => {
    const form = {
      locations: ['1'],
      serviceRows: [{ key: 'a', varietyId: '404', locationId: '1', serviceCount: '5' }],
      task: '55',
      tree_count_delta: 5,
    }
    const lookups = {
      locations: [{ id: 1, name: 'حقل المانجو 1' }],
      varieties: [{ id: 404, name: 'مانجو جديد' }],
      tasks: [{ id: 55, requires_tree_count: true, is_perennial_procedure: true }],
    }

    const { result } = renderHook(() =>
      usePerennialLogic(form, vi.fn(), lookups, true, {
        enabledCards: { perennial: true },
        requiredInputs: { requiresTreeCount: true, isPerennialProcedure: true },
      }),
    )

    expect(result.current.isVarietyAvailableInLocation('404', '1')).toBe(true)
    expect(result.current.validatePerennialCompliance()).toBeNull()
  })
})
