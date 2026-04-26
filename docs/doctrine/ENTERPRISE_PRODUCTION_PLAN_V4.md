# Enterprise Production Plan V4

## Objective
Move AgriAsset from a strong enterprise candidate to a production-approved release by closing the remaining evidence gaps.

## V4 scope actually delivered
- enterprise bootstrap artifacts
- enterprise env template
- health-checked compose definitions
- backup/restore operational scripts
- enterprise readiness static gate
- updated release gate and Make targets

## Remaining runtime gates before 100/100
- `python manage.py check --deploy`
- `python manage.py showmigrations`
- `python manage.py migrate --plan`
- backend test suite in provisioned environment
- frontend unit tests and Playwright in provisioned environment
- backup/restore drill evidence from the target environment
- schema parity / zombies / ghost trigger runtime proof

## Domain score targets
- Financial: 96 -> 100 by closing fixed assets and fuel workflow runtime proof
- Regulatory/Audit: 95 -> 100 by immutable centralized evidence and drill proof
- Planning: 90 -> 100 by seasonal settlement + schedule variance runtime coverage
- Administrative: 91 -> 100 by role delegation + tiering runtime proof
- Technical: 95 -> 100 by reproducible bootstrap and CI/CD promotion evidence
