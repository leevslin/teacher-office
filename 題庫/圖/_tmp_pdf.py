# -*- coding: utf-8 -*-
"""暫用：印出 PDF 指定頁的文字。用法: python _tmp_pdf.py 檔案 [起頁 迄頁]"""
import sys
path = sys.argv[1]
a = int(sys.argv[2]) if len(sys.argv) > 2 else 1
b = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
try:
    import fitz
    d = fitz.open(path)
    print('pages', len(d))
    for i in range(a - 1, min(b, len(d))):
        print('=== p%d ===' % (i + 1))
        print(d[i].get_text())
except ImportError:
    import pypdf
    r = pypdf.PdfReader(path)
    print('pages', len(r.pages))
    for i in range(a - 1, min(b, len(r.pages))):
        print('=== p%d ===' % (i + 1))
        print(r.pages[i].extract_text())
