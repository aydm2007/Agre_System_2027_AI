# RUNTIME EVIDENCE GATES — V8

Required before claiming Production Full:
- `python manage.py check --deploy`
- `python manage.py showmigrations`
- `python manage.py migrate --plan`
- backend boot PASS
- frontend boot PASS
- smoke PASS
- selected E2E PASS
- backup/restore drill PASS
