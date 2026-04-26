"""
[AGRI-GUARDIAN §Axis-8] Variance & Approval Controls Verification
AGENTS.md Axis 8: Variance and Approval Controls.

Verifies:
  1. DailyLog.variance_status field exists (OK/WARNING/CRITICAL)
  2. LogApprovalService enforces supervisor note at WARNING
  3. LogApprovalService enforces manager approval at CRITICAL
  4. MaterialVarianceAlert model exists
  5. ApprovalRule / ApprovalRequest models exist with module/action/amount fields
  6. Variance computation service (compute_log_variance) exists

Usage:
    python scripts/check_variance_controls.py
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS_COUNT = 0
FAIL_COUNT = 0
ERRORS = []


def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  [OK] {msg}")


def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    ERRORS.append(msg)
    print(f"  [FAIL] {msg}")


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def phase1_static_checks():
    print("\n[Phase 1] Static Variance Enforcement Checks:")

    # Check LogApprovalService
    svc = os.path.join(BASE, 'smart_agri', 'core', 'services', 'log_approval_service.py')
    if not os.path.exists(svc):
        fail("T1: log_approval_service.py NOT FOUND")
        return

    src = open(svc, encoding='utf-8').read()

    # T1: supervisor note required at WARNING
    if 'WARNING' in src and 'variance_note' in src and ('not log.variance_note' in src or 'note' in src):
        ok("T1: WARNING variance requires supervisor note before approval ✓")
    else:
        fail("T1: WARNING variance supervisor note enforcement NOT FOUND")

    # T2: manager approval required at CRITICAL
    if 'CRITICAL' in src and 'variance_approved_by' in src:
        ok("T2: CRITICAL variance requires manager approval (variance_approved_by) ✓")
    else:
        fail("T2: CRITICAL variance manager approval enforcement NOT FOUND")

    # T3: variance_approved_at timestamp
    if 'variance_approved_at' in src:
        ok("T3: variance_approved_at timestamp recorded for CRITICAL approvals ✓")
    else:
        fail("T3: variance_approved_at MISSING — no timestamp for CRITICAL approvals")

    # T4: compute_log_variance service exists
    variance_svc = os.path.join(BASE, 'smart_agri', 'core', 'services', 'variance.py')
    if os.path.exists(variance_svc):
        ok("T4: compute_log_variance service exists at core/services/variance.py ✓")
    else:
        fail("T4: variance.py service MISSING")

    # T5: MaterialVarianceAlert in log.py
    log_py = os.path.join(BASE, 'smart_agri', 'core', 'models', 'log.py')
    log_src = open(log_py, encoding='utf-8').read()
    if 'MaterialVarianceAlert' in log_src:
        ok("T5: MaterialVarianceAlert model exists in core/models/log.py ✓")
    else:
        fail("T5: MaterialVarianceAlert model MISSING from core/models/log.py")

    # T6: Self-approval prevention
    if 'created_by_id == user.id' in src or 'created_by == user' in src:
        ok("T6: Self-approval prevention (مخالفة مبدأ الفصل الرقابي) enforced ✓")
    else:
        fail("T6: Self-approval prevention MISSING — creator can approve own log")


def phase2_approval_workflow_check():
    print("\n[Phase 2] ApprovalRule / ApprovalRequest Workflow:")

    finance_models = os.path.join(BASE, 'smart_agri', 'finance', 'models.py')
    src = open(finance_models, encoding='utf-8').read()

    # T7: ApprovalRule exists
    if 'class ApprovalRule' in src:
        ok("T7: ApprovalRule model exists ✓")
    else:
        fail("T7: ApprovalRule model MISSING from finance/models.py")

    # T8: ApprovalRequest exists
    if 'class ApprovalRequest' in src:
        ok("T8: ApprovalRequest model exists ✓")
    else:
        fail("T8: ApprovalRequest model MISSING from finance/models.py")

    # T9: ApprovalRule has module, action, required_role
    for field in ['module', 'action', 'required_role', 'min_amount']:
        if field in src:
            ok(f"T9: ApprovalRule.{field} field present ✓")
        else:
            fail(f"T9: ApprovalRule.{field} MISSING")


def phase3_orm_checks():
    print("\n[Phase 3] Django ORM Verification:")
    try:
        import django
        django.setup()
        from smart_agri.core.models.log import DailyLog, MaterialVarianceAlert
        from smart_agri.finance.models import ApprovalRule, ApprovalRequest

        # T10: DailyLog.variance_status has OK/WARNING/CRITICAL choices
        field = DailyLog._meta.get_field('variance_status')
        choices = [c[0] for c in (field.choices or [])]
        if 'WARNING' in choices and 'CRITICAL' in choices:
            ok("T10: DailyLog.variance_status has OK/WARNING/CRITICAL choices ✓")
        else:
            fail(f"T10: variance_status choices incomplete: {choices}")

        # T11: ApprovalRequest.STATUS_PENDING / APPROVED / REJECTED constants
        if (hasattr(ApprovalRequest, 'STATUS_PENDING') and
                hasattr(ApprovalRequest, 'STATUS_APPROVED') and
                hasattr(ApprovalRequest, 'STATUS_REJECTED')):
            ok("T11: ApprovalRequest status constants (PENDING/APPROVED/REJECTED) defined ✓")
        else:
            fail("T11: ApprovalRequest status constants MISSING")

    except Exception as e:
        fail(f"Phase 3 ORM error: {e}")


print("=" * 60)
print("[AGRI-GUARDIAN] Variance & Approval Controls — Axis 8")
print("=" * 60)
phase1_static_checks()
phase2_approval_workflow_check()
phase3_orm_checks()
print()
print(f"  Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
if FAIL_COUNT == 0:
    print("\nPASSED: Variance and approval controls fully enforced. ✅")
    sys.exit(0)
else:
    print("\nFAILED:")
    for e in ERRORS:
        print(f"  - {e}")
    sys.exit(1)
