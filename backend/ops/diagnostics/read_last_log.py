import os

LOG_FILE = "backend/logs/app_sales.log"

def read_tail(lines=300):
    try:
        with open(LOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            seek_pos = max(0, file_size - 50000) # Read last 50KB
            f.seek(seek_pos)
            content = f.read().decode('utf-8', errors='ignore')
            print(content)
    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    read_tail()
