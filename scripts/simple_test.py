
import os
import sys
import datetime

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")

try:
    with open('test_output.txt', 'w') as f:
        f.write(f"Hello from Python! Time: {datetime.datetime.now()}\n")
    print("Successfully wrote to test_output.txt")
except Exception as e:
    print(f"Failed to write to file: {e}")
