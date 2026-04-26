import os

cleanup_targets = [
    '.bak', '.tmp', '.log', '.original', '.old', '__pycache__', '.pytest_cache'
]

def scan_for_garbage():
    print("--- Scanning for temporary/junk files (Sanitization) ---")
    garbage_found = []
    for root, dirs, files in os.walk('.'):
        # Skip node_modules and .git
        if 'node_modules' in root or '.git' in root:
            continue
            
        for d in dirs:
            if d == '__pycache__' or d == '.pytest_cache':
                garbage_found.append(os.path.join(root, d))
                
        for f in files:
            if any(f.endswith(suffix) for suffix in cleanup_targets):
                garbage_found.append(os.path.join(root, f))
                
    if garbage_found:
        print(f"Found {len(garbage_found)} items to clean:")
        for item in sorted(garbage_found):
            print(f" - {item}")
    else:
        print("Codebase is clean of common temporary files.")

if __name__ == '__main__':
    scan_for_garbage()
