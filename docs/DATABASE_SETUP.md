# 🚀 DATABASE SETUP GUIDE - Complete Instructions

## Current Status
- ✅ Migrations created (0093, 0094)
- ✅ Code complete and production-ready
- ⚠️ Database connection needs setup

---

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker Desktop installed and running
- Docker Compose 2.0+

### Setup Steps

```bash
# 1. Navigate to project root
cd c:\tools\workspace\saradud2027

# 2. Start only database service
docker-compose up -d db

# 3. Wait for PostgreSQL to be ready (30 seconds)
timeout /t 30

# 4. Verify database is running
docker-compose ps
```

### Apply Migrations

```bash
# Set environment variable for local connection
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/smart_agri_db"

# Navigate to backend
cd backend

# Check migration status
python manage.py showmigrations core

# Apply RLS migrations
python manage.py migrate core 0093_enable_rls_core_tables
python manage.py migrate core 0094_create_rls_policies

# Verify migrations applied
python manage.py showmigrations core | Select-String "0093\|0094"
```

### Verify RLS in Database

```bash
# Connect to database
docker exec -it saradud2027-db-1 psql -U postgres -d smart_agri_db

# Check RLS enabled (should return 9)
SELECT COUNT(*) as rls_enabled_tables 
FROM pg_tables 
WHERE schemaname='public' AND rowsecurity=true;

# Check policies created (should return 8)
SELECT COUNT(*) as rls_policies 
FROM pg_policies 
WHERE schemaname='public';

# List all RLS-protected tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname='public' AND rowsecurity=true;

# List all policies
SELECT schemaname, tablename, policyname, cmd
FROM pg_policies 
WHERE schemaname='public'
ORDER BY tablename, policyname;

# Exit psql
\q
```

---

## Option 2: Local PostgreSQL Installation

### If Docker is not available:

```bash
# 1. Install PostgreSQL 16
# Download from: https://www.postgresql.org/download/windows/

# 2. Create database
createdb -U postgres smart_agri_db

# 3. Set connection string
$env:DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/smart_agri_db"

# 4. Apply migrations
cd backend
python manage.py migrate

# 5. Apply RLS migrations
python manage.py migrate core 0093
python manage.py migrate core 0094
```

---

## Option 3: Run Tests WITHOUT Database

### Unit Tests (Work without DB)

```bash
cd backend

# Run tests that don't require database
python manage.py test --tag=unit

# Run specific test modules
pytest smart_agri/core/tests/test_cost_allocation.py -v
```

---

## Test Execution (After DB Setup)

### Run RLS Tests

```bash
cd backend

# Set database URL
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/smart_agri_db"

# Run RLS policy tests
python manage.py test smart_agri.core.tests.test_rls_policies --verbosity=2

# Run RLS middleware tests  
python manage.py test smart_agri.core.tests.test_rls_middleware --verbosity=2

# Run financial RLS tests
python manage.py test smart_agri.core.tests.test_financial_rls --verbosity=2

# Run all RLS tests
python manage.py test smart_agri.core.tests.test_rls* --verbosity=2
```

### Run Full Test Suite

```bash
# All tests
python manage.py test --verbosity=2

# With coverage
pytest --cov=smart_agri --cov-report=html --cov-report=term

# View coverage report
start htmlcov/index.html
```

---

## Production Verification Commands

### Security Check

```bash
# Development settings
python manage.py check --deploy

# Production settings  
python manage.py check --deploy --settings=smart_agri.production_settings
```

### Schema Sentinel

```bash
# Run integrity check
python manage.py nightly_integrity_check

# Run in strict mode (fails on warnings)
python manage.py nightly_integrity_check --strict
```

---

## Troubleshooting

### Issue: DATABASE_URL not recognized

**Solution:**
```bash
# PowerShell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/smart_agri_db"

# Or create .env file in backend/
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_agri_db
DJANGO_SECRET_KEY=your-secret-key-here
```

### Issue: Docker not running

**Solution:**
1. Start Docker Desktop
2. Wait for it to fully initialize
3. Run: `docker ps` to verify

### Issue: Port 5432 already in use

**Solution:**
```bash
# Stop existing PostgreSQL service
net stop postgresql-x64-16

# Or use different port in docker-compose.yml
ports:
  - "5433:5432"  # External:Internal
```

### Issue: Migrations conflict

**Solution:**
```bash
# Check migration status
python manage.py showmigrations core

# If conflicts, migrate to specific version
python manage.py migrate core 0092
python manage.py migrate core 0093  
python manage.py migrate core 0094
```

---

## Quick Verification Checklist

After setup, verify:

- [ ] Docker container running: `docker ps`
- [ ] Database accessible: `docker exec -it saradud2027-db-1 psql -U postgres -l`
- [ ] Migrations applied: `python manage.py showmigrations core`
- [ ] RLS enabled: Check pg_tables query
- [ ] Tests passing: `python manage.py test smart_agri.core.tests.test_rls*`
- [ ] Schema Sentinel: `python manage.py nightly_integrity_check`
- [ ] Security check: `python manage.py check --deploy`

---

## Expected Results

### Successful Migration Output
```
Operations to perform:
  Apply all migrations: core
Running migrations:
  Applying core.0093_enable_rls_core_tables... OK
  Applying core.0094_create_rls_policies... OK
```

### Successful RLS Verification
```sql
rls_enabled_tables = 9
rls_policies = 8
```

### Successful Test Output
```
Ran 25 tests in 5.234s
OK
```

---

**Ready to proceed? Choose an option above and follow the steps!**
