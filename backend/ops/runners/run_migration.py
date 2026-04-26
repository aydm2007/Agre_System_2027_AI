import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
    import django
    django.setup()
    
    from django.core.management import call_command
    
    try:
        print("Calling makemigrations core...")
        call_command("makemigrations", "core", interactive=False)
        print("Calling migrate...")
        call_command("migrate", interactive=False)
        print("All done!")
    except Exception as e:
        print(f"Error: {e}")
