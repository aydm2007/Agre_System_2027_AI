# Reference Demo Seed Manifest (V39)

The release package intentionally excludes legacy production-like dumps and password snapshots.
Use the authoritative bootstrap path instead:
- `python backend/manage.py bootstrap_postgres_foundation --default-password <PASSWORD>`
- `python backend/manage.py seed_full_system --default-password <PASSWORD>`
