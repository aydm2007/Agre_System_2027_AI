import os
from pathlib import Path

def get_indent(line):
    return len(line) - len(line.lstrip())

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    modified = False

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        stripped = line.strip()
        if stripped.startswith("except Exception") and ":" in stripped:
            except_indent = get_indent(line)
            block_indent = None
            
            # Read the contents of the except block
            block_lines = []
            j = i + 1
            has_return_or_raise = False
            
            while j < len(lines):
                next_line = lines[j]
                if not next_line.strip():
                    block_lines.append(next_line)
                    j += 1
                    continue
                
                curr_indent = get_indent(next_line)
                if curr_indent <= except_indent:
                    break
                    
                if block_indent is None:
                    block_indent = curr_indent
                
                if next_line.strip().startswith("return") or next_line.strip().startswith("raise"):
                    has_return_or_raise = True
                    
                block_lines.append(next_line)
                j += 1
            
            # Append all block lines to new_lines
            new_lines.extend(block_lines)
            
            # If no return or raise, we inject `raise` at the end of the block
            if not has_return_or_raise and block_indent is not None:
                # Add raise
                # Make sure the last line of the block wasn't a pass we want to replace, but appending is fine
                raise_line = (" " * block_indent) + "raise\n"
                new_lines.append(raise_line)
                modified = True
            
            i = j
        else:
            i += 1

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

def main():
    root_dir = Path(r"c:\tools\workspace\Agre_ERP_2027-main\backend\smart_agri")
    
    modified_count = 0
    # Specifically target service and API files, or all files except tests
    for py_file in root_dir.rglob("*.py"):
        if "test" in py_file.name.lower() or "migrations" in str(py_file).lower():
            continue
            
        if process_file(py_file):
            print(f"Refactored: {py_file.relative_to(root_dir)}")
            modified_count += 1
            
    print(f"Total files modified: {modified_count}")

if __name__ == "__main__":
    main()
