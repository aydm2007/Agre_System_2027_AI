import os
import sys

def run_test():
    with open("ping_output.txt", "w", encoding="utf-8") as f:
        try:
            f.write("Setting up Django...\n")
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
            import django
            django.setup()
            f.write("Django setup complete.\n")
            
            from smart_agri.core.models import CropPlan
            plan = CropPlan.objects.filter(name__icontains='خطة التدقيق').last()
            
            if plan:
                f.write(f"DB Connected. Plan Found: {plan.name}\n")
            else:
                f.write("DB Connected. Plan Not Found.\n")
                
        except Exception as e:
            f.write(f"Error occurred: {e}\n")

if __name__ == "__main__":
    run_test()
