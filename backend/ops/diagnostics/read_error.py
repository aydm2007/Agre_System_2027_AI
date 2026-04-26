import sys

try:
    print("Reading migration_error.txt...")
    with open('migration_error.txt', 'r', encoding='utf-16') as f:
        lines = f.readlines()
        print(f"Total lines: {len(lines)}")
        
        with open('found_error.txt', 'w', encoding='utf-8') as out:
            for i, line in enumerate(lines):
                if "History" in line or "Error" in line or "Exception" in line:
                    out.write(f"LINE {i}: {line.strip()}\n")
            # Also write last 5 lines
            out.write("\n--- LAST 5 LINES ---\n")
            for line in lines[-5:]:
                out.write(line.strip() + "\n")
                
    print("Wrote found_error.txt")

except Exception as e:
    print(f"Error: {e}")

