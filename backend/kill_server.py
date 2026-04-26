import psutil
import os

killed = 0
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = p.info.get('cmdline')
        if cmdline and 'manage.py' in cmdline and 'runserver' in cmdline:
            print(f"killing {p.info['pid']} - {cmdline}")
            # we try to terminate
            p.terminate()
            killed += 1
    except Exception as e:
        pass

if killed > 0:
    print(f"Killed {killed} runserver processes")
else:
    print("No runserver processes found")
