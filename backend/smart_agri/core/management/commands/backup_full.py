import shutil
import os
import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Creates a full backup (Database + Media) for Offline Recovery'

    def handle(self, *args, **options):
        # 1. Setup Backup Directory
        backup_root = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_root, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_folder = os.path.join(backup_root, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # 2. Backup SQLite Database
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            shutil.copy2(db_path, os.path.join(backup_folder, "db.sqlite3"))
            self.stdout.write(self.style.SUCCESS(f"✅ Database copied to {backup_folder}"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Database file not found (Are you using PostgreSQL?)"))

        # 3. Backup Media Files (Attachments)
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
             # Zip media to save space
             shutil.make_archive(
                 os.path.join(backup_folder, "media"), 
                 'zip', 
                 media_root
             )
             self.stdout.write(self.style.SUCCESS(f"✅ Media zipped to {backup_folder}"))
        
        # 4. Create Manifest
        with open(os.path.join(backup_folder, "manifest.txt"), "w") as f:
            f.write(f"Backup Date: {timestamp}\n")
            f.write(f"System Version: 1.0 (Sanaa Strict)\n")
            
        self.stdout.write(self.style.SUCCESS("🚀 FULL BACKUP COMPLETE."))
