"""
Strict-Mode Permission Classification
======================================
[AGRI-GUARDIAN Axis 6 / AGENTS.md §119 / PRD V21 §7]

Permissions listed here belong to interfaces that are ONLY active when
``FarmSettings.mode == 'STRICT'`` — the canonical dual-mode contract per
PRD V21 §7 and AGENTS.md.  ``SystemSettings.strict_erp_mode`` may remain
as a legacy bootstrap signal only; it is NOT the primary contract for any
new dual-mode workflow logic.

When a SIMPLE-mode farm attempts to access these routes the backend MUST:
  1. Return 403 / ``PermissionDenied``, and
  2. Emit an ``AuditLog`` entry (mode_breach) — AGENTS.md §14.

The set uses Django permission **codenames** (e.g. ``view_financialledger``).
"""

# ─── Financial Ledger & Treasury ──────────────────────────────────────
_FINANCE_PERMS = {
    "view_financialledger",
    "add_financialledger",
    "change_financialledger",
    "view_treasurytransaction",
    "add_treasurytransaction",
    "change_treasurytransaction",
}

# ─── Fiscal Period & Budget ───────────────────────────────────────────
_FISCAL_PERMS = {
    "view_fiscalperiod",
    "change_fiscalperiod",
    "view_fiscalyear",
    "change_fiscalyear",
    "view_budgetclassification",
    "add_budgetclassification",
    "change_budgetclassification",
}

# ─── Expenses & Cost Centres ─────────────────────────────────────────
_EXPENSE_PERMS = {
    "view_actualexpense",
    "add_actualexpense",
    "change_actualexpense",
    "view_costcenter",
    "change_costcenter",
    "view_costconfiguration",
    "change_costconfiguration",
}

# ─── Approval Workflow ────────────────────────────────────────────────
_APPROVAL_PERMS = {
    "view_approvalrequest",
    "add_approvalrequest",
    "change_approvalrequest",
    "view_approvalrule",
    "add_approvalrule",
    "change_approvalrule",
    "approve_salesinvoice",
}

# ─── Audit & Finance Logs ────────────────────────────────────────────
_AUDIT_PERMS = {
    "view_financeauditlog",
}

# ─── Combined Set (immutable frozenset for safety) ────────────────────
STRICT_MODE_PERMISSIONS: frozenset = frozenset(
    _FINANCE_PERMS
    | _FISCAL_PERMS
    | _EXPENSE_PERMS
    | _APPROVAL_PERMS
    | _AUDIT_PERMS
)


def is_strict_permission(codename: str) -> bool:
    """Return ``True`` if the codename belongs to a strict-mode-only interface."""
    return codename in STRICT_MODE_PERMISSIONS


def classify_permissions(codenames):
    """
    Split an iterable of codenames into two sets:
    ``(strict_set, general_set)``.
    """
    strict = set()
    general = set()
    for c in codenames:
        (strict if c in STRICT_MODE_PERMISSIONS else general).add(c)
    return strict, general
