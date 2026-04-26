# V11 Sector Governance and Approval Chain

## Purpose
This doctrine formalizes how the sector operates as a multi-farm management and governed approval layer. It is neither a silent observer nor a replacement for normal farm execution.

## Sector Roles
### 1. محاسب القطاع
- performs first sector-side review of farm submissions
- validates document completeness, metadata, thresholds, and policy prerequisites
- returns incomplete transactions to the farm for correction
- does not provide final approval on material transactions prepared by the same review chain

### 2. مراجع القطاع
- performs second-line review after sector accountant
- validates maker-checker integrity
- challenges anomalies, repeated exceptions, and unsupported overrides
- escalates material issues to sector chief accountant or sector finance director

### 3. رئيس حسابات القطاع
- owns accounting sign-off at the sector level
- validates reconciliations, close readiness, chart usage, and posting correctness
- signs off on accounting readiness before finance final approval

### 4. المدير المالي لقطاع المزارع
- owns final financial approval where policy, threshold, or exception class requires it
- owns hard-close sign-off
- approves material financial exceptions, settlement overrides, and evidence exceptions
- must not become the day-to-day preparer for ordinary farm work

### 5. مدير القطاع
- owns final business/executive approval when policy requires business sign-off beyond finance sign-off
- approves strategic exceptions, high-value contracts, and materially unusual sector outcomes
- is not the ordinary approver for every operational transaction

## Farm vs Sector Split
### Farm responsibilities
- create operational truth
- prepare local financial documents
- execute daily activity, harvest, petty cash, receipts, and local settlement posture
- perform first close preparation

### Sector responsibilities
- review, challenge, consolidate, and approve by threshold
- supervise policy compliance across multiple farms
- own final hard-close and material exceptions
- maintain a multi-farm risk view

## Suggested Approval Ladder by Transaction Class
| Transaction class | Farm action | Sector accountant | Sector reviewer | Sector chief accountant | Sector finance director | Sector director |
|---|---|---|---|---|---|---|
| Routine low-value local expense within threshold | prepare + local approval | sample or scheduled review | optional | optional | not required | not required |
| Above local threshold local expense | prepare + local review | required | required | required | required | optional by policy |
| Supplier settlement material value | prepare + local review | required | required | required | required | optional by policy |
| Period hard-close | prepare + soft-close | required | required | required | required | not usually required |
| Strategic contract or major exception | prepare + local review | required | required | required | required | required |

## Small-Farm Compensating Controls
- threshold-based auto-escalation
- mandatory weekly remote review
- exception dashboard
- hard-close reserved for sector chain
- mandatory evidence for non-routine cash and settlement actions

## Design Anti-Patterns
- sector accountant acting as approver of their own materially prepared transaction
- sector finance director acting as daily farm preparer
- sector director approving every routine local item
- collapsing the sector chain into one role while claiming full governance
