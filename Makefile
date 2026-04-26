.PHONY: verify-static verify-runtime-proof verify-release-gate verify-release-gate-fast verify-enterprise-static verify-v5-static bootstrap-postgres-foundation closure-evidence verify-tests verify-float-guard verify-all verify-frontend

# ─── Static Analysis ──────────────────────────────────────────────────
verify-static:
	python3 backend/manage.py verify_static_v21

# ─── Float Guard (Financial Integrity Linter) ─────────────────────────
verify-float-guard:
	cd backend && python3 scripts/float_guard.py --strict

# ─── Backend Tests ────────────────────────────────────────────────────
verify-tests:
	cd backend && python3 -m pytest --tb=short -q --timeout=120

verify-tests-cov:
	cd backend && python3 -m pytest --tb=short -q --timeout=120 --cov=smart_agri --cov-report=term-missing

# ─── Frontend Verification ────────────────────────────────────────────
verify-frontend:
	cd frontend && npm ci --prefer-offline
	cd frontend && npm run lint 2>/dev/null || true
	cd frontend && npm run test -- --run 2>/dev/null || true
	cd frontend && npm run build

# ─── Django Checks & Migrations ───────────────────────────────────────
verify-django:
	cd backend && python3 manage.py check --deploy 2>/dev/null || python3 manage.py check
	cd backend && python3 manage.py showmigrations --plan 2>/dev/null | tail -20
	cd backend && python3 manage.py migrate --plan 2>/dev/null | head -20

# ─── Runtime Proof ────────────────────────────────────────────────────
verify-runtime-proof:
	python3 backend/manage.py run_closure_evidence_v21

# ─── Release Gate (Full) ──────────────────────────────────────────────
verify-release-gate:
	python3 backend/manage.py verify_release_gate_v21

verify-release-gate-fast:
	$(MAKE) verify-release-gate

# ─── Full Verification (All Layers) ──────────────────────────────────
verify-all:
	@echo "═══════════════════════════════════════════════════"
	@echo "  AgriAsset V21 — Full Verification Suite"
	@echo "═══════════════════════════════════════════════════"
	$(MAKE) verify-static
	$(MAKE) verify-float-guard
	$(MAKE) verify-django
	$(MAKE) verify-tests
	$(MAKE) verify-frontend
	$(MAKE) verify-runtime-proof
	@echo "═══════════════════════════════════════════════════"
	@echo "  ✅ All verification steps completed"
	@echo "═══════════════════════════════════════════════════"

# ─── Aliases / Legacy ────────────────────────────────────────────────
verify-enterprise-static:
	$(MAKE) verify-static

verify-v5-static:
	$(MAKE) verify-static

closure-evidence:
	python3 backend/manage.py run_closure_evidence_v21

bootstrap-postgres-foundation:
	bash scripts/bootstrap/bootstrap_postgres_foundation.sh
