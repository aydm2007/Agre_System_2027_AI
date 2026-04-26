#!/usr/bin/env python
"""
🚑 Startup Sentinel - Pre-flight Check
يفحص جميع المتطلبات قبل تشغيل الخادم.
"""
import os
import sys
from pathlib import Path

# Load .env before imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / '.env')
except ImportError:
    pass


def check_environment():
    """Run all pre-flight checks."""
    errors = []
    warnings = []
    
    print("🚑 Startup Sentinel - Pre-flight Check")
    print("=" * 50)
    
    # 1. Check .env file
    print("1️⃣  Checking .env file...", end=" ")
    env_file = backend_dir / '.env'
    if not env_file.exists():
        errors.append("ملف .env غير موجود")
        print("❌ FAIL")
    else:
        print("✅ OK")
    
    # 2. Check required environment variables
    print("2️⃣  Checking environment variables...", end=" ")
    required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        errors.append(f"متغيرات البيئة التالية مفقودة: {', '.join(missing)}")
        print("❌ FAIL")
    else:
        print("✅ OK")
    
    # 3. Check database connection
    print("3️⃣  Checking database connection...", end=" ")
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            connect_timeout=5
        )
        conn.close()
        print("✅ OK")
    except ImportError:
        warnings.append("psycopg2 غير مثبت - استخدم: pip install psycopg2-binary")
        print("⚠️ SKIP (psycopg2 not installed)")
    except Exception as e:
        errors.append(f"فشل الاتصال بقاعدة البيانات: {e}")
        print("❌ FAIL")
    
    # 4. Check Django settings
    print("4️⃣  Checking Django configuration...", end=" ")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
        import django
        django.setup()
        from django.conf import settings as django_settings
        
        if django_settings.DEBUG:
            warnings.append("DEBUG=True - لا ينبغي استخدامه في الإنتاج")
        
        print("✅ OK")
    except Exception as e:
        errors.append(f"فشل تهيئة Django: {e}")
        print("❌ FAIL")
    
    # Summary
    print("=" * 50)
    
    if warnings:
        print("\n⚠️  تحذيرات:")
        for w in warnings:
            print(f"   - {w}")
    
    if errors:
        print("\n❌ فشل الفحص:")
        for err in errors:
            print(f"   - {err}")
        print("\n💡 نصيحة: تحقق من تشغيل PostgreSQL وصحة بيانات .env")
        sys.exit(1)
    else:
        print("\n✅ جميع الفحوصات ناجحة. النظام جاهز للتشغيل.")
        print("   شغّل: python manage.py runserver 0.0.0.0:8000")
        sys.exit(0)


if __name__ == "__main__":
    check_environment()
