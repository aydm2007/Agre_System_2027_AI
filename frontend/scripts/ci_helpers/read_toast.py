import codecs

try:
    with codecs.open(r"c:\tools\workspace\Agre_ERP_2027-main\frontend\src\components\ToastProvider.jsx", "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    with codecs.open(r"c:\tools\workspace\Agre_ERP_2027-main\frontend\toast_clean.txt", "w", encoding="utf-8") as out:
        out.write(text)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
