import os
import re

# StandardUOM mapping
UOM_MAP = {
    r"uom\s*=\s*['\"]ltr['\"]": "uom='L'",
    r"uom\s*=\s*['\"]Ltr['\"]": "uom='L'",
    r"uom\s*=\s*['\"]Liter['\"]": "uom='L'",
    r"uom\s*=\s*['\"]كجم['\"]": "uom='kg'",
    r"uom\s*=\s*['\"]KG['\"]": "uom='kg'",
    r"uom\s*=\s*['\"]M2['\"]": "uom='m2'",
    r"uom\s*=\s*['\"]M3['\"]": "uom='m3'",
    r"planted_uom\s*=\s*['\"]ha['\"]": "planted_uom='hectare'",
    r"planted_uom\s*=\s*['\"]M2['\"]": "planted_uom='m2'",
    r"water_uom\s*=\s*['\"]M3['\"]": "water_uom='m3'",
    r"pack_uom\s*=\s*['\"]KG['\"]": "pack_uom='kg'",
    r"pack_uom\s*=\s*['\"]kg['\"]": "pack_uom='kg'",
    r"['\"]uom['\"]\s*:\s*['\"]ltr['\"]": "'uom': 'L'",
    r"['\"]uom['\"]\s*:\s*['\"]Liter['\"]": "'uom': 'L'",
    r"['\"]uom['\"]\s*:\s*['\"]kg['\"]": "'uom': 'kg'",
    r"['\"]uom['\"]\s*:\s*['\"]KG['\"]": "'uom': 'kg'",
}

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, replacement in UOM_MAP.items():
        new_content = re.sub(pattern, replacement, new_content)
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {path}")

def main():
    base_dir = r"c:\tools\workspace\AgriAsset_v44\backend"
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py') and ('test' in file or 'seed' in file or 'uat' in file):
                fix_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
