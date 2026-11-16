# -*- coding: utf-8 -*-
"""
社會科辦公室：一次把 Word／Excel 檔的文字印出來（省得一步一步摸索）。

用法：python tools/read_doc.py 檔案路徑 [最多幾個字，預設 12000]
支援 .docx .xlsx .xlsm .txt .md .csv；PDF 和圖片請直接用 Read 工具讀。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def docx_text(p):
    import docx
    d = docx.Document(str(p))
    out = []
    body = d.element.body
    for el in body.iterchildren():
        tag = el.tag.split('}')[-1]
        if tag == 'p':
            t = ''.join(n.text or '' for n in el.iter() if n.tag.endswith('}t'))
            if t.strip():
                out.append(t)
        elif tag == 'tbl':
            for tr in el.iter():
                if tr.tag.endswith('}tr'):
                    cells = []
                    for tc in tr:
                        if tc.tag.endswith('}tc'):
                            cells.append(''.join(n.text or '' for n in tc.iter() if n.tag.endswith('}t')).strip())
                    if any(cells):
                        out.append('| ' + ' | '.join(cells) + ' |')
            out.append('')
    return '\n'.join(out)


def xlsx_text(p):
    import openpyxl
    wb = openpyxl.load_workbook(str(p), data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f'=== 工作表：{ws.title} ===')
        for row in ws.iter_rows(values_only=True):
            vals = ['' if v is None else str(v) for v in row]
            if any(v.strip() for v in vals):
                while vals and not vals[-1].strip():
                    vals.pop()
                out.append(' | '.join(vals))
    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    p = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
    if not p.exists():
        print(f'找不到檔案：{p}'); return 1
    ext = p.suffix.lower()
    try:
        if ext == '.docx':
            t = docx_text(p)
        elif ext in ('.xlsx', '.xlsm'):
            t = xlsx_text(p)
        elif ext in ('.txt', '.md', '.csv'):
            t = p.read_text(encoding='utf-8', errors='replace')
        elif ext == '.doc':
            print('這是舊版 .doc，讀不了。請老師另存成 .docx，或直接用同名的 .pdf。'); return 1
        else:
            print('這個格式請直接用 Read 工具讀（PDF、圖片）。'); return 1
    except ImportError as e:
        print(f'缺少套件：{e}。請執行 python -m pip install python-docx openpyxl'); return 1
    print(f'【{p.name}】共 {len(t)} 字' + (f'，只印前 {limit} 字' if len(t) > limit else ''))
    print(t[:limit])
    return 0


if __name__ == '__main__':
    sys.exit(main())
