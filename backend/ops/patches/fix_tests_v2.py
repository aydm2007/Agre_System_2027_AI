import os
import re

TEST_DIRS = [
    r"c:\tools\workspace\AgriAsset_v44\backend\smart_agri\finance\tests",
    r"c:\tools\workspace\AgriAsset_v44\backend\smart_agri\core\tests",
    r"c:\tools\workspace\AgriAsset_v44\backend\smart_agri\accounts\tests"
]

def patch_tests():
    files_to_process = []
    for d in TEST_DIRS:
        if os.path.exists(d):
            filenames = os.listdir(d)
            for file in filenames:
                if file.startswith("test_") and file.endswith(".py"):
                    files_to_process.append(os.path.join(d, file))

    updated_count = 0
    for file in files_to_process:
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        changed = False
        new_lines = []
        
        # We need to catch `Farm.objects.create(` and `.post(`/`.patch(`
        
        inside_farm_create = False
        farm_create_buffer = []

        for line in lines:
            if inside_farm_create:
                farm_create_buffer.append(line)
                if ')' in line:
                    inside_farm_create = False
                    block = "".join(farm_create_buffer)
                    if 'mode=' not in block:
                        block = block.replace(')', ", mode='STRICT')", 1)
                        changed = True
                    new_lines.append(block)
                    farm_create_buffer = []
                continue

            if 'Farm.objects.create(' in line:
                if ')' in line:
                    if 'mode=' not in line:
                        line = line.replace(')', ", mode='STRICT')", 1)
                        changed = True
                    new_lines.append(line)
                else:
                    inside_farm_create = True
                    farm_create_buffer.append(line)
                continue
                
            # naive client methods patching
            if re.search(r'\bclient\.(post|patch|put)\(', line) or re.search(r'self\.client\.(post|patch|put)\(', line):
                if 'HTTP_X_IDEMPOTENCY_KEY' not in line:
                    line = line.replace(')', ", HTTP_X_IDEMPOTENCY_KEY='test-12b23')", 1)
                    changed = True
            
            new_lines.append(line)
            
        if changed:
            with open(file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            updated_count += 1

    print(f"Patched {updated_count} test files robustly.")

if __name__ == '__main__':
    patch_tests()
