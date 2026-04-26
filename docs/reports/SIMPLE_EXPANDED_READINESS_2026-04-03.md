# SIMPLE Expanded Readiness Report

Date: 2026-04-03
Mode: `SIMPLE`
Classification: supplemental readiness evidence

## Purpose

This report records the expanded SIMPLE proof bundle used to validate:

- strict authoring isolation
- posture-first governed cycle surfaces
- mixed seasonal/perennial daily execution
- perennial forensic flow stability

This report is supporting evidence only. Canonical release and score authority remain:

- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`

## Commands

```bash
python backend/manage.py test smart_agri.core.tests.test_tree_inventory smart_agri.core.tests.test_seed_tree_inventory_endpoint smart_agri.core.tests.test_simple_mode_crop_variance_audit smart_agri.core.tests.test_al_jaruba_simple_cycle --keepdb --noinput
npm --prefix frontend run test -- src/hooks/__tests__/usePerennialLogic.test.js src/components/daily-log/__tests__/DailyLogDetails.test.jsx src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx --run
npm --prefix frontend run lint
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-simple-expanded
npx --prefix frontend playwright test frontend/tests/e2e/simple_mode_isolation.spec.js frontend/tests/e2e/simple-mode-governed-cycles-ar.spec.js frontend/tests/e2e/sardud_perennial_forensic_cycle.spec.js frontend/tests/e2e/daily-log-seasonal-perennial.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

## Outcome

- backend targeted regression: PASS
- frontend targeted regression: PASS
- frontend lint: PASS
- expanded SIMPLE Playwright bundle: `10/10 PASS`

## Notes

- The expanded bundle confirms the active SIMPLE contract: posture-first governed surfaces may remain visible, while strict authoring routes stay hidden or redirect to dashboard.
- The mixed seasonal/perennial proof validates crop-scoped perennial variety writes, positive `tree_count_delta` addition flow, and location-aware perennial service rows.
