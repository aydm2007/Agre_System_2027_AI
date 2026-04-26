# V8 FINAL CLOSURE MATRIX

| Area | V7 Status | V8 Action | V8 Status |
|---|---|---|---|
| Strong float gate | FAIL in fixed assets | Introduced `decimal_guard.safe_percentage()` and removed raw `/` from fixed asset dashboard path | PASS static |
| Integrations service layer | 1 direct write hotspot | Added `ExternalFinanceBatchService` and rewired `integrations/api.py` | PASS static |
| Evidence integrity | Drift between weak and strong float checks | V8 evidence uses `backend/scripts/check_no_float_mutations.py` explicitly | PASS static |
| Fiscal/Fund governance | Partial | Added `FiscalFundGovernanceService` | Improved/partial |
| Farm tiering runtime policy | Partial | Added `FarmTieringPolicyService` | Improved/partial |
| Harvest compliance | Blocked | Added `HarvestComplianceService` | Improved/partial |
| Seasonal settlement | Blocked | Added `SeasonalSettlementService` | Improved/partial |
| Sharecropping settlement | Blocked | Added `SharecroppingSettlementService` | Improved/partial |
| Sovereign/Zakat policy | Blocked | Added `SovereignZakatService` wrapper | Improved/partial |
> [!WARNING]
> Historical baseline only. Not active reference.
> Use the V21 active references and strict completion matrix instead.
