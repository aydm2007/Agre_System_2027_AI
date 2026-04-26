# 🚨 DOCKER TROUBLESHOOTING GUIDE

## Issue: Docker API Error 500

**Symptom:**
```
request returned 500 Internal Server Error for API route
```

This means Docker Desktop is not fully initialized or has API compatibility issues.

---

## Solution 1: Restart Docker Desktop

### Steps:
```powershell
# 1. Stop all Docker services
Stop-Service -Name com.docker.service -Force
Stop-Service -Name docker -Force

# 2. Restart Docker Desktop application
# Close Docker Desktop completely (from system tray)
# Wait 10 seconds
# Start Docker Desktop again

# 3. Wait for Docker to fully start (2-3 minutes)
# Look for "Docker is running" in system tray

# 4. Verify Docker works
docker --version
docker ps
```

---

## Solution 2: Reset Docker to Default

### Steps:
1. Open Docker Desktop
2. Go to: Settings → Troubleshoot → Reset to factory defaults
3. Click "Reset"
4. Wait for Docker to restart
5. Try: `docker ps` again

---

## Solution 3: Use Local PostgreSQL (Recommended if Docker fails)

### Install PostgreSQL 16

```powershell
# 1. Download from:
# https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

# 2. Install PostgreSQL 16
# Use default settings
# Remember the password you set for user 'postgres'

# 3. Verify installation
psql --version

# 4. Create database
psql -U postgres
CREATE DATABASE smart_agri_db;
\q
```

### Configure Django

```powershell
# Create .env file in backend/
cd c:\tools\workspace\saradud2027\backend

# Create .env file with:
@"
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/smart_agri_db
DJANGO_SECRET_KEY=your-secret-key-here-please-change-me
DJANGO_DEBUG=True
"@ | Out-File -FilePath .env -Encoding utf8
```

### Apply Migrations

```powershell
cd c:\tools\workspace\saradud2027\backend

# Run migrations
python manage.py migrate

# Apply RLS migrations
python manage.py migrate core 0093_enable_rls_core_tables
python manage.py migrate core 0094_create_rls_policies

# Verify
python manage.py showmigrations core
```

### Verify RLS

```powershell
# Connect to database
psql -U postgres -d smart_agri_db

# Check RLS enabled (should return 9)
SELECT COUNT(*) as rls_tables 
FROM pg_tables 
WHERE schemaname='public' AND rowsecurity=true;

# Check policies (should return 8)
SELECT COUNT(*) as policies 
FROM pg_policies 
WHERE schemaname='public';

# List all RLS tables
SELECT tablename 
FROM pg_tables 
WHERE schemaname='public' AND rowsecurity=true 
ORDER BY tablename;

# Exit
\q
```

---

## ~~Solution 4: Use SQLite for Tests~~ — **BANNED**

> [!CAUTION]
> **SQLite is strictly banned** per `AGENTS.md` Rule 7. Do NOT use SQLite for tests, development, governance validation, or production.
> SQLite cannot replicate RLS policies, `btree_gist` constraints, `ExclusionConstraint`, PostgreSQL triggers, or `NUMERIC(19,4)` precision.

**Instead**, fix your PostgreSQL connection:

```powershell
# 1. Ensure PostgreSQL service is running
Get-Service | Where-Object {$_.Name -like "*postgres*"}

# 2. If not running, start it
Start-Service postgresql-x64-16

# 3. Load credentials into shell
. scripts/windows/Resolve-BackendDbEnv.ps1

# 4. Verify connection
python manage.py check
python manage.py showmigrations --plan
```

**⚠️ Warning:** All test, governance, and compliance validation MUST run against PostgreSQL.

---

## Next Steps After Fixing Database

Once database is working:

```bash
# 1. Apply migrations
python manage.py migrate core 0093
python manage.py migrate core 0094

# 2. Run tests
python manage.py test smart_agri.core.tests.test_rls_policies
python manage.py test smart_agri.core.tests.test_rls_middleware
python manage.py test smart_agri.core.tests.test_financial_rls

# 3. Verify
python manage.py nightly_integrity_check --strict
python manage.py check --deploy

# 4. Done! 🎉
```

---

## Quick Diagnostic Commands

```powershell
# Check Docker status
docker info
docker ps
docker version

# Check PostgreSQL status
Get-Service | Where-Object {$_.Name -like "*postgres*"}
psql --version

# Test database connection
psql -U postgres -c "SELECT version();"
```

---

## If All Else Fails

Contact me with output of:
```powershell
docker info
docker version
Get-Service | Where-Object {$_.Name -like "*docker*"}
```

I'll help debug the specific issue.
