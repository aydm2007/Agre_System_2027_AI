import os
base = "c:/tools/workspace/AgriAsset_v44/docs/evidence/closure/latest"
folders = ["verify_static_v21", "verify_release_gate_v21", "verify_axis_complete_v21", "playwright"]
for d in folders:
    os.makedirs(os.path.join(base, d), exist_ok=True)
print("Directories created successfully!")
