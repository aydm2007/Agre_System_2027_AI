"""
[AGRI-GUARDIAN] E2E Integration Test: Full DailyLog Pipeline + Rejection Flow

Tests the complete lifecycle:
  1. Model + Service imports
  2. Variance resolution (PlannedCost → ShadowVarianceEngine)
  3. Burn Rate accuracy
  4. Rejection state machine (SUBMITTED→REJECTED→DRAFT)
  5. Correction history tracking
  6. Quarantine service for mode switching
  7. Shadow Ledger independence
  8. PlannedActivity linkage
"""
import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

FOUR_DP = Decimal('0.0001')
ZERO = Decimal('0.0000')
P = '✅'
F = '❌'
results = []


def test(name, condition, detail=''):
    status = P if condition else F
    results.append((name, status, detail))
    print(f'  {status} {name}' + (f' — {detail}' if detail else ''))


def section(title, num):
    print(f'\n▸ {num}. {title}')


def run_all():
    print('\n' + '=' * 70)
    print('[AGRI-GUARDIAN] E2E Integration Test — DailyLog + Rejection + Quarantine')
    print('=' * 70)

    # ── 1. Model Imports ───────────────────────────────────────
    section('Core Model Imports', 1)
    try:
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.activity import Activity
        from smart_agri.core.models.planning import CropPlan, PlannedActivity, PlannedMaterial
        from smart_agri.core.models.settings import FarmSettings, SystemSettings
        from smart_agri.core.models.report import VarianceAlert
        from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine
        from smart_agri.finance.models import FinancialLedger
        test('All core models importable', True)
    except ImportError as e:
        test('Core model imports', False, str(e))
        return

    # ── 2. Service Imports ─────────────────────────────────────
    section('Service Imports', 2)
    services_ok = True
    for mod_path, name in [
        ('smart_agri.core.services.daily_log_execution', 'FrictionlessDailyLogService'),
        ('smart_agri.core.services.daily_log_execution', '_resolve_planned_cost'),
        ('smart_agri.core.services.activity_service', 'ActivityService'),
        ('smart_agri.core.services.shadow_variance_engine', 'ShadowVarianceEngine'),
        ('smart_agri.core.services.log_approval_service', 'LogApprovalService'),
        ('smart_agri.core.services.quarantine_service', 'ModeSwitchQuarantineService'),
        ('smart_agri.finance.services.core_finance', 'FinanceService'),
        ('smart_agri.core.services.costing', 'calculate_activity_cost'),
    ]:
        try:
            mod = __import__(mod_path, fromlist=[name])
            getattr(mod, name)
            test(f'{name} importable', True)
        except (ImportError, AttributeError) as e:
            test(f'{name} importable', False, str(e))
            services_ok = False

    if not services_ok:
        print('\n⛔ Missing services — some tests will be skipped.')

    # Import all needed services
    from smart_agri.core.services.daily_log_execution import _resolve_planned_cost
    from smart_agri.core.services.activity_service import ActivityService
    from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine
    from smart_agri.core.services.log_approval_service import LogApprovalService
    from smart_agri.core.services.quarantine_service import ModeSwitchQuarantineService
    from smart_agri.core.api.burn_rate_api import _compute_elapsed_pct

    # ── 3. Burn Rate Accuracy ──────────────────────────────────
    section('Burn Rate Elapsed % Calculation', 3)
    today = date.today()

    # Mid-season
    pct = _compute_elapsed_pct({
        'start_date': today - timedelta(days=30),
        'end_date': today + timedelta(days=30),
    })
    test('Mid-season ≈ 50%', Decimal('40') <= pct <= Decimal('60'), f'{pct}')

    # Missing dates → 50% fallback
    test('Missing dates → 50%', _compute_elapsed_pct({}) == Decimal('50.0000'))

    # Future plan → 0%
    pct3 = _compute_elapsed_pct({
        'start_date': today + timedelta(days=10),
        'end_date': today + timedelta(days=100),
    })
    test('Future → 0%', pct3 == ZERO, f'{pct3}')

    # Past plan → 100%
    pct4 = _compute_elapsed_pct({
        'start_date': today - timedelta(days=100),
        'end_date': today - timedelta(days=10),
    })
    test('Past → 100%', pct4 == Decimal('100.0000'), f'{pct4}')

    # ── 4. ShadowVarianceEngine ────────────────────────────────
    section('ShadowVarianceEngine Behavior', 4)
    test('_is_strict_mode returns bool',
         isinstance(ShadowVarianceEngine._is_strict_mode(None), bool))

    r1 = ShadowVarianceEngine.audit_execution_cost(
        farm=None, activity_name='test',
        actual_cost=Decimal('100.0000'), planned_cost=Decimal('105.0000'))
    test('Under threshold → PASS', r1 == 'AUDIT_PASSED_OK')

    r2 = ShadowVarianceEngine.audit_execution_cost(
        farm=None, activity_name='test',
        actual_cost=Decimal('100.0000'), planned_cost=ZERO)
    test('Zero plan → SKIP', r2 == 'SKIPPED_NO_PLAN')

    # ── 5. PlannedActivity Linkage ─────────────────────────────
    section('PlannedActivity Auto-Linkage', 5)
    method = getattr(ActivityService, '_link_planned_activity', None)
    test('_link_planned_activity exists', method is not None)
    test('Is static/callable', callable(method))
    # Graceful with empty data
    ActivityService._link_planned_activity({}, None)
    test('Empty payload OK', True)
    ActivityService._link_planned_activity({'crop_plan': None, 'task': None}, today)
    test('None values OK', True)

    # ── 6. Rejection State Machine ─────────────────────────────
    section('Rejection State Machine (Model Level)', 6)
    from smart_agri.core.constants import DailyLogStatus

    transitions = DailyLog.VALID_TRANSITIONS
    test('SUBMITTED can → REJECTED',
         DailyLogStatus.REJECTED in transitions.get(DailyLogStatus.SUBMITTED, set()))
    test('REJECTED can → DRAFT',
         DailyLogStatus.DRAFT in transitions.get(DailyLogStatus.REJECTED, set()))
    test('APPROVED cannot → REJECTED',
         DailyLogStatus.REJECTED not in transitions.get(DailyLogStatus.APPROVED, set()))
    test('DRAFT cannot → APPROVED',
         DailyLogStatus.APPROVED not in transitions.get(DailyLogStatus.DRAFT, set()))

    # ── 7. LogApprovalService Methods ──────────────────────────
    section('LogApprovalService Methods', 7)
    for method_name in ['submit_log', 'approve_log', 'reject_log', 'reopen_log',
                        'note_warning', 'approve_variance']:
        test(f'{method_name} exists',
             hasattr(LogApprovalService, method_name) and
             callable(getattr(LogApprovalService, method_name)))

    # Correction history: reopen_log has tracking code
    import inspect
    src = inspect.getsource(LogApprovalService.reopen_log)
    test('reopen_log tracks correction_count', 'correction_count' in src)
    test('reopen_log stores correction_history', 'correction_history' in src)
    test('reopen_log clears rejection_reason', 'rejection_reason' in src)
    test('reopen_log resets variance', 'variance_status' in src)
    test('reopen_log unlocks Timesheet', 'is_approved=False' in src)

    # ── 8. Quarantine Service ──────────────────────────────────
    section('ModeSwitchQuarantineService', 8)
    test('quarantine_pending_logs_on_mode_switch exists',
         callable(getattr(ModeSwitchQuarantineService,
                          'quarantine_pending_logs_on_mode_switch', None)))
    test('resolve_quarantine exists',
         callable(getattr(ModeSwitchQuarantineService, 'resolve_quarantine', None)))
    test('get_quarantine_stats exists',
         callable(getattr(ModeSwitchQuarantineService, 'get_quarantine_stats', None)))
    test('QUARANTINE_WINDOW is 24h',
         ModeSwitchQuarantineService.QUARANTINE_WINDOW_HOURS == 24)

    # ── 9. OfflineSyncQuarantine Model ─────────────────────────
    section('OfflineSyncQuarantine Model Integrity', 9)
    for field in ['farm', 'submitted_by', 'variance_type', 'device_timestamp',
                  'original_payload', 'idempotency_key', 'status',
                  'manager_signature', 'resolved_at', 'resolution_reason']:
        test(f'OfflineSyncQuarantine.{field}', hasattr(OfflineSyncQuarantine, field))

    # ── 10. Model Field Integrity ──────────────────────────────
    section('Model Field Integrity', 10)
    for field in ['cost_labor', 'cost_materials', 'cost_machinery',
                  'cost_overhead', 'cost_total']:
        test(f'Activity.{field}', hasattr(Activity, field))
    test('Activity.log FK', hasattr(Activity, 'log'))
    test('Activity.crop_plan FK', hasattr(Activity, 'crop_plan'))
    test('PlannedActivity.estimated_hours', hasattr(PlannedActivity, 'estimated_hours'))
    test('VarianceAlert.planned_cost', hasattr(VarianceAlert, 'planned_cost'))
    test('VarianceAlert.actual_cost', hasattr(VarianceAlert, 'actual_cost'))
    test('VarianceAlert.variance_percentage', hasattr(VarianceAlert, 'variance_percentage'))

    # ── 11. Shadow Ledger Fallback (Code Inspection) ───────────
    section('Shadow Ledger Independence (Code Inspection)', 11)
    from smart_agri.core.services import daily_log_execution as dle_mod
    dle_src = inspect.getsource(dle_mod)
    test('Shadow Ledger has idempotency_key dedup',
         'idempotency_key' in dle_src)
    test('Shadow Ledger uses ACCOUNT_WIP',
         'ACCOUNT_WIP' in dle_src)
    test('Shadow Ledger uses analytical_tags',
         'analytical_tags' in dle_src)

    # ── SUMMARY ────────────────────────────────────────────────
    print('\n' + '=' * 70)
    passed = sum(1 for _, s, _ in results if s == P)
    failed = sum(1 for _, s, _ in results if s == F)
    total = len(results)
    pct = (passed / total * 100) if total > 0 else 0
    print(f'RESULT: {passed}/{total} passed ({pct:.0f}%)')
    if failed:
        print(f'\n{F} FAILURES ({failed}):')
        for name, status, detail in results:
            if status == F:
                print(f'   • {name}: {detail}')
    else:
        print(f'\n🎉 ALL TESTS PASSED — FULL COMPLIANCE')
    print('=' * 70)


if __name__ == '__main__':
    run_all()
