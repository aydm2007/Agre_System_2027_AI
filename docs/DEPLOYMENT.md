# AgriAsset V21 Production Deployment Guide

> [!IMPORTANT]
> This guide is an execution runbook, not the live release-status authority.
> Live status must be read from:
> - `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
> - `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
> - `docs/evidence/uat/khameesiya/latest/summary.json` for the current new-tenant dual-mode UAT pack

## Gold Baseline Gate

Treat a deployment candidate as `Gold Baseline achieved` only when all of the following are true in the same baseline:

- latest `verify_release_gate_v21` summary reports `overall_status=PASS`
- latest `verify_axis_complete_v21` summary reports:
  - `overall_status=PASS`
  - `axis_overall_status=PASS`
- latest `docs/evidence/uat/khameesiya/latest/summary.json` reports `overall_status=PASS`
- no active reference conflict remains in `docs/reference/`
- deployment and handoff documents match the latest canonical summaries exactly
- the release baseline is packaged from a clean worktree/tag rather than an uncommitted local snapshot

## Production Contract

- PostgreSQL is the only permitted production and governance database engine.
- Production settings must remain fail-closed:
  - `DJANGO_ENV=production`
  - `DJANGO_DEBUG=False`
  - explicit `DJANGO_SECRET_KEY`
  - explicit `DJANGO_ALLOWED_HOSTS` or `ALLOWED_HOSTS`
  - no wildcard hosts
- Health verification must cover application health, database reachability, and auth readiness.
- Release packaging must exclude ad-hoc evidence folders, local-only credentials, and unreviewed report rewrites.
- The approved UAT tenant pack for this baseline is `docs/evidence/uat/khameesiya/latest/`.

## Canonical Evidence Bundle

Treat the following paths as the release-facing evidence bundle for the current baseline:

- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
- `docs/evidence/uat/khameesiya/latest/summary.json`
- `docs/evidence/uat/khameesiya/latest/summary.md`

The UAT evidence pack is supporting release evidence. It does not outrank the canonical closure summaries.

## Prerequisites

- **PostgreSQL:** 16+
- **Python:** 3.11+
- **Node.js:** 18+
- **Docker:** 20.10+ (recommended)
- **Docker Compose:** 2.0+

---

## 📋 Pre-Deployment Checklist

- [ ] Database backup created
- [ ] Environment variables configured
- [ ] Secret key generated
- [ ] SSL certificates ready (production)
- [ ] Domain DNS configured
- [ ] Git tag created for release

---

## 🔐 Environment Variables

### Required Variables

```bash
# Django Core
export DJANGO_SECRET_KEY="<generate-with-command-below>"
export DJANGO_SETTINGS_MODULE="smart_agri.production_settings"
export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
export DEBUG=False

# Database
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
export DB_NAME="agriasset_prod"
export DB_USER="agri_user"
export DB_PASSWORD="<secure-password>"
export DB_HOST="db"
export DB_PORT="5432"

# CORS & Security
export CORS_ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
export CSRF_TRUSTED_ORIGINS="https://yourdomain.com"

# AGRI-MAESTRO Settings
export COSTING_STRICT_MODE=True
```

### Generate Secret Key

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

---

## 📦 Deployment Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/agriasset-2025.git
cd agriasset-2025
git checkout v1.0.0  # or your release tag
```

### Step 2: Build Docker Images

```bash
# Build backend and frontend
docker-compose -f docker-compose.prod.yml build
```

### Step 3: Database Setup

```bash
# Start only database first
docker-compose -f docker-compose.prod.yml up -d db

# Wait for PostgreSQL to be ready
docker-compose -f docker-compose.prod.yml exec db pg_isready

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# Apply RLS migrations (Phase 3)
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate core 0093_enable_rls_core_tables
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate core 0094_create_rls_policies
```

### Step 4: Verify RLS Policies

```bash
# Connect to database
docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME

# Check RLS enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname='public' AND tablename LIKE 'core_%' AND rowsecurity=true;
-- Expected: 9 rows

# Check policies created
SELECT COUNT(*) FROM pg_policies WHERE schemaname='public';
-- Expected: 8

# Exit psql
\q
```

### Step 5: Create Superuser

```bash
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py createsuperuser
```

### Step 6: Collect Static Files

```bash
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput
```

### Step 7: Security Check

```bash
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py check --deploy
# Expected: System check identified no issues (0 silenced).
```

### Step 7.5: Canonical Release Proof

```bash
python backend/manage.py run_khameesiya_uat --artifact-root docs/evidence/uat/khameesiya/latest
python scripts/verification/verify_release_hygiene.py
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
```

Expected:

- `docs/evidence/uat/khameesiya/latest/summary.json` -> `overall_status=PASS`
- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` -> `overall_status=PASS`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` -> `overall_status=PASS`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` -> `axis_overall_status=PASS`

### Step 8: Start All Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Step 9: Verify Services

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test backend health
curl https://yourdomain.com/api/health/

# Test frontend
curl https://yourdomain.com/
```

---

## 🔍 Verification Commands

### Check RLS Middleware

```bash
# Check logs for RLS context setting
docker-compose -f docker-compose.prod.yml logs backend | grep "RLS context set"
```

### Test Farm Isolation

```sql
-- In psql, set user context
SET app.user_id = '1';

-- Query should only show farms for user 1
SELECT * FROM core_farm;

-- Change context
SET app.user_id = '2';

-- Should show different farms
SELECT * FROM core_farm;
```

### Check Migration Status

```bash
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py showmigrations
```

---

## 🐛 Troubleshooting

### Issue: RLS Not Working

**Symptoms:** Users can see all farms regardless of membership

**Solution:**
1. Check middleware is registered:
   ```python
   # settings.py
   MIDDLEWARE = [
       ...
       'smart_agri.core.middleware.rls_middleware.RLSMiddleware',
       ...
   ]
   ```

2. Verify user has FarmMembership:
   ```sql
   SELECT * FROM accounts_farmmembership WHERE user_id = X;
   ```

3. Check PostgreSQL session variable:
   ```sql
   SELECT current_setting('app.user_id', true);
   ```

### Issue: Migration 0092 Fails

**Symptoms:** Migration dependency errors

**Solution:**
```bash
# For fresh database installations
python manage.py migrate core 0092 --fake-initial
python manage.py migrate core 0093
python manage.py migrate core 0094
```

### Issue: Security Warnings

**Symptoms:** `python manage.py check --deploy` shows warnings

**Solution:**
1. Ensure production settings loaded:
   ```bash
   export DJANGO_SETTINGS_MODULE=smart_agri.production_settings
   ```

2. Set required security variables:
   ```bash
   export ALLOWED_HOSTS="yourdomain.com"
   export SECURE_SSL_REDIRECT=True
   ```

---

## 📊 Monitoring

### Health Checks

```bash
# Backend health endpoint
curl https://yourdomain.com/api/health/

# Database connection
docker-compose exec db pg_isready

# Check container status
docker-compose ps
```

### Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Database only
docker-compose logs -f db
```

---

## 🔄 Updates & Maintenance

### Apply New Migrations

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Backup Database

```bash
# Create backup
docker-compose exec db pg_dump -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T db psql -U $DB_USER $DB_NAME < backup_20260128.sql
```

---

## ✅ Production Readiness Checklist

- [ ] All migrations applied successfully
- [ ] RLS enabled on 9 critical tables
- [ ] 8 RLS policies created
- [ ] Security check passes (0 warnings)
- [ ] Superuser created
- [ ] Static files collected
- [ ] Environment variables set
- [ ] SSL/HTTPS configured
- [ ] Database backup automated
- [ ] Monitoring configured
- [ ] Logs accessible
- [ ] Health checks passing

---

**Deployment Complete!** 🎉

Your AgriAsset V21 system is now production-ready with:
Current V21 score claims are evidence-gated. Use `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` as the live authority for any `100/100` statement.
- ✅ Row Level Security (RLS) enabled
- ✅ Farm isolation enforced
- ✅ Financial ledger protection
- ✅ Django security hardened
- ✅ Evidence-gated release status; use the latest canonical axis-complete summary for any score statement
