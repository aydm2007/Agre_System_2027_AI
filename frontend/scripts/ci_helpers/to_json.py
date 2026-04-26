import json
with open("src/components/ToastProvider.jsx", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()
with open("toast.json", "w", encoding="utf-8") as out:
    json.dump({"content": text}, out, ensure_ascii=True)
