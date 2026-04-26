import re

filepath = 'smart_agri/core/api/reporting.py'
with open(filepath, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace all location__isnull=False
code = code.replace("location__isnull=False", "activity_locations__location__isnull=False")

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(code)

print('Patch location__isnull applied')

