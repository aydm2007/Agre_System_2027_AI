import os
import ast
import sys

BACKEND_ROOT = "c:\\tools\\workspace\\saradud2027\\backend"
EXCLUDE_DIRS = ['venv', '__pycache__', 'migrations']

def load_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.readlines()

def save_file(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
         f.writelines(lines)

def fix_file(path):
    MAX_RETRIES = 10
    for attempt in range(MAX_RETRIES):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            # If it parses, we are good!
            if attempt > 0:
                print(f"✅ Fixed {path} after {attempt} attempts.")
            return True
        except (IndentationError, SyntaxError) as e:
            lineno = e.lineno
            if not lineno:
                print(f"❌ Failed to fix {path}: No line number in error.")
                return False
            
            print(f"🔧 Fixing {path} at line {lineno}: {e.msg}")
            
            lines = load_file(path)
            # Check line at lineno-1 (0-indexed)
            # Insert 'pass' at the correct indentation
            # Usually the error points to the line *after* the empty block, or the block header depending on python version
            
            # If "expected an indented block", it points to the line *after* the block?
            # Or the line that *should* be indented.
            
            target_idx = lineno - 1
            if target_idx >= len(lines):
                target_idx = len(lines) - 1
            
            # Simple heuristic:
            # If line is valid code, maybe the PREVIOUS line was the block opener and it's empty.
            # We need to find the indentation of the block opener.
            
            # Let's try to insert 'pass' before the error line with indentation?
            # Or append 'pass' to the previous line?
            
            # Actually, standard behavior:
            # if x:
            # y = 1  <-- Error here: expected indented block
            
            # We should insert '    pass\n' before 'y = 1'?
            # But we need to know the indentation of 'if x:'.
            
            # Let's scan backwards for the colon line
            offset = 1
            colon_line_idx = -1
            while target_idx - offset >= 0:
                l = lines[target_idx - offset]
                if l.strip().endswith(':'):
                    colon_line_idx = target_idx - offset
                    break
                # Only skip comments/empty lines
                if not l.strip() or l.strip().startswith('#'):
                    offset += 1
                    continue
                else:
                    # Found code but not colon? Abort search?
                    # Maybe the error line IS the one after the block.
                    break
            
            if colon_line_idx != -1:
                # Found the header!
                header_line = lines[colon_line_idx]
                indent = header_line[:len(header_line) - len(header_line.lstrip())]
                # Default indentation is 4 spaces usually
                pass_indent = indent + "    "
                
                # Insert pass after the colon line (and potentially after comments)
                # Ideally just after colon line is safest?
                lines.insert(colon_line_idx + 1, f"{pass_indent}pass # [AG-FIX]\n")
                save_file(path, lines)
                continue # Retry parse
            
            # If we couldn't find a colon line, verify if the error is "unexpected indent" vs "expected indented block"
            if "expected an indented block" in e.msg:
                # Fallback: inspect the line reported. If it's effectively empty or comment, maybe we insert pass there?
                # Actually, usually inserting pass at the error line index with +4 spaces of previous line helps?
                prev_line = lines[target_idx - 1] if target_idx > 0 else ""
                prev_indent = prev_line[:len(prev_line) - len(prev_line.lstrip())]
                lines.insert(target_idx, f"{prev_indent}    pass # [AG-FIX-FALLBACK]\n")
                save_file(path, lines)
            else:
                print(f"❌ Unhandled Syntax Error type in {path}: {e.msg}")
                return False

    print(f"❌ Could not fix {path} after {MAX_RETRIES} attempts.")
    return False

def scan_and_fix():
    print("🔧 Scanning SMART_AGRI for syntax errors...")
    target_dir = os.path.join(BACKEND_ROOT, "smart_agri")
    for root, dirs, files in os.walk(target_dir):
        # Default behavior is recursive
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                fix_file(path)

if __name__ == '__main__':
    scan_and_fix()
