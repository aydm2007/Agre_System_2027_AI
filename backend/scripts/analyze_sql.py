import sys

filename = r"c:\tools\workspace\saradud2027\workspace_v3.1.1.8.8.sql"

print(f"Reading {filename}...")
try:
    with open(filename, 'rb') as f:
        header = f.read(100)
        print(f"Header (bytes): {header}")
        try:
            print(f"Header (utf-8): {header.decode('utf-8')}")
        except:
            print("Header not proper utf-8")
        
    print("\nAttempting to find tables...")
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.splitlines()
        tables = [line for line in lines if "CREATE TABLE" in line]
        print(f"Found {len(tables)} tables.")
        for t in tables[:20]:
            print(t)
            
except Exception as e:
    print(f"Error: {e}")
