# Runtime Evidence Gates — V9

Required before a final 100/100 claim:

1. `python manage.py check --deploy`
2. `python manage.py showmigrations`
3. `python manage.py migrate --plan`
4. backend boot in production-like settings
5. frontend build and smoke
6. DB-backed integration tests
7. Playwright/E2E critical cycles
8. backup/restore drill in a production-like environment
