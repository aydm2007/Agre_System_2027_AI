import os
import shutil

BASE_DIR = os.path.join(os.getcwd(), 'backend', 'smart_agri', 'core', 'migrations')
ARCHIVE_DIR = os.path.join(os.getcwd(), 'backend', 'migrations_archive')

def reset_migrations():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        print(f"Created archive: {ARCHIVE_DIR}")

    print("Moving legacy migrations...")
    count = 0
    for filename in os.listdir(BASE_DIR):
        if filename != '__init__.py' and filename != '__pycache__':
            src = os.path.join(BASE_DIR, filename)
            dst = os.path.join(ARCHIVE_DIR, filename)
            try:
                if os.path.isfile(src):
                    shutil.move(src, dst)
                    count += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")

    print(f"Moved {count} files to archive.")

if __name__ == "__main__":
    reset_migrations()
