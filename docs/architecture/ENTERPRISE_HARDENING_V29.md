# Enterprise Hardening v29

## Highlights

- Split finance approval state transition helpers into a dedicated module to reduce service concentration and clarify workflow responsibilities.
- Continued frontend API modularization by extracting approval clients and auth clients out of `client.js`.
- Added a focused regression test for approval history append behavior.

## Architectural impact

- Lower coupling inside `ApprovalGovernanceService`.
- Better separation between transport/API concerns and auth/approval domain clients on the frontend.
- Cleaner path for future typed contracts and domain-specific API modules.
