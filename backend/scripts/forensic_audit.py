
import os
import django
import inspect
import sys
from collections import defaultdict
from django.conf import settings
from django.apps import apps
from rest_framework import serializers

# Setup Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
    django.setup()

def audit_serializers():
    print("Scanning Serializers...")
    issues = []
    
    # Iterate over all installed apps
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith('smart_agri'):
            continue
            
        # Try to import serializers module
        try:
            # Common patterns: app.api.serializers, app.serializers
            module_names = [
                f"{app_config.name}.api.serializers",
                f"{app_config.name}.serializers",
                # Handle split files like core.api.serializers.activity
                f"{app_config.name}.api.serializers.activity",
                f"{app_config.name}.api.serializers.daily_log",
                f"{app_config.name}.api.serializers.tree",
                f"{app_config.name}.api.serializers.farm",
                f"{app_config.name}.api.serializers.crop",
            ]
            
            for mod_name in module_names:
                try:
                    __import__(mod_name)
                    mod = sys.modules[mod_name]
                    
                    for name, obj in inspect.getmembers(mod):
                        if inspect.isclass(obj) and issubclass(obj, serializers.ModelSerializer) and obj.__module__ == mod_name:
                            # Check 1: ImproperlyConfigured candidates
                            model = obj.Meta.model
                            meta_fields = getattr(obj.Meta, 'fields', [])
                            if meta_fields == '__all__':
                                # Inspect model fields vs serializer decls
                                pass 
                            else:
                                for field_name in meta_fields:
                                    # Check if field exists on model
                                    model_field = None
                                    try:
                                        model_field = model._meta.get_field(field_name)
                                    except Exception:
                                        pass
                                        
                                    # Check if declared on serializer
                                    declared_field = obj._declared_fields.get(field_name)
                                    
                                    if not model_field and not declared_field:
                                        issues.append(f"[Serializer Config] {obj.__name__} in {mod_name}: Field '{field_name}' in Meta.fields but NOT in Model '{model.__name__}' and NOT explicitly declared. (Risk: ImproperlyConfigured/500 Error)")

                except ImportError:
                    continue
        except Exception as e:
            print(f"Error scanning app {app_config.name}: {e}")

    return issues

def audit_models_vs_sql(sql_path):
    print("Comparing Models to SQL Schema...")
    if not os.path.exists(sql_path):
        return ["SQL file not found"]

    issues = []
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Simple heuristic check for tables
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith('smart_agri'):
            continue
            
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if f"CREATE TABLE public.{table_name}" not in sql_content and f"CREATE TABLE {table_name}" not in sql_content:
                # Check for managed=False
                if model._meta.managed:
                     issues.append(f"[DB Mismatch] Table '{table_name}' for model '{model.__name__}' NOT FOUND in SQL dump.")
                else:
                     pass # Managed=False, expected possibly
            else:
                # Check columns? Too complex for regex, trust table existence implies mostly correct version for now
                pass

    return issues

def run_audit():
    serializer_issues = audit_serializers()
    db_issues = audit_models_vs_sql('workspace_v3.1.1.8.8.2.sql')
    
    report = "# Forensic System Audit Report\n\n"
    
    report += "## 1. API Serializer Integrity\n"
    if serializer_issues:
        for issue in serializer_issues:
            report += f"- 🔴 {issue}\n"
    else:
        report += "- ✅ All scanned serializers appear valid.\n"
        
    report += "\n## 2. Database Schema Alignment\n"
    if db_issues:
        for issue in db_issues:
            report += f"- 🔴 {issue}\n"
    else:
        report += "- ✅ All managed Django models have corresponding tables in the provided SQL schema.\n"
        
    print(report)
    
    # Save to file
    with open('FORENSIC_AUDIT_RESULT.md', 'w') as f:
        f.write(report)

if __name__ == '__main__':
    run_audit()
