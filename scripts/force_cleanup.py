
import os
import time

files = ['seeding.log', 'simulation.log', 'step1.log', 'step1_error.log', 'step2.log', 'step2_error.log', 'execution_trace.log']
print("Starting Cleanup...")
for f in files:
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"✅ Deleted {f}")
        except Exception as e:
            print(f"❌ Failed to delete {f}: {e}")
    else:
        print(f"ℹ️ {f} does not exist.")

print("Cleanup Finished.")
