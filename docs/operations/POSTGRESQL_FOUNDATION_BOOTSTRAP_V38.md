# PostgreSQL Foundation Bootstrap (V38)

## الهدف
تجهيز نسخة PostgreSQL مرجعية متكاملة تحتوي على:
- المهاجرات
- الأدوار والمجموعات والصلاحيات
- المزارع المرجعية والبيانات الأولية
- FarmSettings وFarmGovernanceProfile حسب الشريحة SMALL/MEDIUM/LARGE
- قوالب RACI المرجعية
- snapshot محفوظ داخل `docs/evidence/bootstrap/`

## المسار المعتمد
1. انسخ `backend/.env.postgres.example` إلى ملف `.env` مناسب وعدّل كلمات المرور.
2. شغّل PostgreSQL وRedis.
3. نفّذ:
   - `bash scripts/bootstrap/bootstrap_postgres_foundation.sh`

## بديل Docker Compose
- `docker compose -f docker-compose.postgres-bootstrap.yml up --build`

## ناتج الإغلاق المتوقع
- ملف JSON داخل `docs/evidence/bootstrap/` يتضمن:
  - vendor = postgresql
  - farms/users/groups/memberships counts
  - حالة المزارع الثلاث وmode/approval_profile
  - وجود finance lead للمزارع MEDIUM/LARGE
