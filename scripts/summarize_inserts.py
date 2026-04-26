import re

INPUT_FILE = "found_inserts.txt"
OUTPUT_FILE = "tables_list.txt"

def summarize():
    tables = set()
    try:
        with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re.search(r"INSERT INTO (public\.)?(\w+)", line, re.IGNORECASE)
                if match:
                    tables.add(match.group(2))
    except FileNotFoundError:
        print("found_inserts.txt not found")
        return

    with open(OUTPUT_FILE, "w") as f:
        for t in sorted(tables):
            f.write(f"{t}\n")
    print(f"Found {len(tables)} tables.")

if __name__ == "__main__":
    summarize()
