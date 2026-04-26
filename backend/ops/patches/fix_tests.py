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
            for root, _, files in os.walk(d):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        files_to_process.append(os.path.join(root, file))

    updated_count = 0
    for file in files_to_process:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Add mode='STRICT' to Farm.objects.create(
        content = re.sub(
            r'Farm\.objects\.create\((.*?)\)',
            lambda m: f"Farm.objects.create({m.group(1)})" if 'mode' in m.group(1) else f"Farm.objects.create({m.group(1)}, mode='STRICT')",
            content,
            flags=re.DOTALL
        )

        # Add HTTP_X_IDEMPOTENCY_KEY to self.client.post / patch
        content = re.sub(
            r'(self\.client\.(?:post|patch|put)\([^)]+)',
            lambda m: m.group(1) if 'HTTP_X_IDEMPOTENCY_KEY' in m.group(1) else m.group(1) + ", HTTP_X_IDEMPOTENCY_KEY='test-123'",
            content
        )

        # Fix missing imports that Pyre warned about previously
        if "from django.core.exceptions import ValidationError" not in content and "ValidationError" in content:
            content = "from django.core.exceptions import ValidationError\n" + content
        if "import pytest" not in content and "pytest" in content:
            content = "import pytest\n" + content

        if content != original_content:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1

    print(f"Patched {updated_count} test files.")

if __name__ == '__main__':
    patch_tests()
