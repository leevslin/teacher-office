# -*- coding: utf-8 -*-
"""排版後處理：把第三、四大題（計算題）改成「一列兩格」的表格，左右並排，
整列不跨頁（照去年三年級期末卷的做法）。
用法：make_docx.py 重新產生 Word 之後再跑一次：
    python 題庫/數學四上期末_計算題並排.py
"""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OFFICE = Path(__file__).resolve().parent.parent
FILES = ['成品/考卷/數學_四上_第6-10單元_期末考.docx',
         '成品/考卷/數學_四上_第6-10單元_期末考_答案.docx']
# 大題開頭 → 下一大題開頭、格子高度（公分）
SECTIONS = [('三、', '四、', 5.6), ('四、', '五、', 5.0)]


def ptext(d, e):
    return Paragraph(e, d).text if e.tag == qn('w:p') else None


def set_borders(tbl):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), '8')
        el.set(qn('w:space'), '0'); el.set(qn('w:color'), '000000')
        b.append(el)
    tblPr.append(b)


def process(path):
    d = docx.Document(path)
    sect = d.sections[-1]
    col_w = (sect.page_width - sect.left_margin - sect.right_margin - Cm(1.0)) / 2
    body = d.element.body
    for start, end, height in SECTIONS:
        els = list(body)
        si = next(i for i, e in enumerate(els) if (ptext(d, e) or '').startswith(start))
        ei = next(i for i, e in enumerate(els) if i > si and (ptext(d, e) or '').startswith(end))
        head, chunk = els[si], els[si + 1:ei]
        if any(e.tag == qn('w:tbl') for e in chunk):
            print(f'{path.name} {start} 已經是表格，略過'); continue
        k = next(i for i, e in enumerate(chunk) if (ptext(d, e) or '').startswith('2．'))
        groups = [chunk[:k], chunk[k:]]
        tbl = d.add_table(rows=1, cols=2)
        set_borders(tbl)
        tbl.autofit = False
        row = tbl.rows[0]
        row.height = Cm(height)
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement('w:cantSplit'); trPr.append(cs)   # 整列不跨頁
        w = int(col_w / 2)
        for ci, g in enumerate(groups):
            cell = row.cells[ci]
            cell.width = w
            tc = cell._tc
            for p in list(tc.iterchildren(qn('w:p'))):
                tc.remove(p)
            for e in g:
                if e.tag == qn('w:p') and not (ptext(d, e) or '').strip():
                    body.remove(e); continue        # 空白行改由格子高度提供
                tc.append(e)
                p = Paragraph(e, d)
                p.paragraph_format.left_indent = Cm(0)
                p.paragraph_format.first_line_indent = Cm(0)
        for c in tbl.columns:
            for cell in c.cells:
                cell.width = w
        Paragraph(head, d).paragraph_format.keep_with_next = True
        head.addnext(tbl._tbl)
        sp = copy.deepcopy(head)                         # 表格後空一行
        for r in sp.findall(qn('w:r')):
            sp.remove(r)
        tbl._tbl.addnext(sp)
        print(f'{path.name} {start} 改成左右並排（格高 {height} 公分）')
    for start, end, h in BOXES:
        add_boxes(d, start, end, h)
    min_font(d)
    d.save(path)


MIN_PT = 14        # 老師規定：字最小 14 級
FRAC_PT = 19       # Word 會把行內分數的分子分母縮小約 3/4，設 19 印出來約 14


def min_font(d):
    M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
    body = d.element.body
    for sz in body.iter(qn('w:sz')):
        if int(sz.get(qn('w:val'))) < MIN_PT * 2:
            sz.set(qn('w:val'), str(MIN_PT * 2))
    # 抬頭「班級 座號 姓名 得分」改成 14 級後放不下兩個字：標籤格加寬，從姓名格扣
    t = d.tables[0]
    if t.rows[0].cells[0].text == '班級':
        widths = [Cm(w) for w in (1.7, 2.6, 1.7, 2.2, 1.7, 4.8, 1.7, 3.0)]
        for c, w in zip(t.rows[0].cells, widths):
            c.width = w
        for g, w in zip(t._tbl.tblGrid.findall(qn('w:gridCol')), widths):
            g.set(qn('w:w'), str(int(w.twips)))
    for f in body.iter(M + 'f'):
        for part in (M + 'num', M + 'den'):
            for sz in f.find(part).iter(qn('w:sz')):
                sz.set(qn('w:val'), str(FRAC_PT * 2))


# 應用題：題目下面加「算式／答」書寫框（大題開頭, 下一大題開頭, 算式格高公分）
BOXES = [('六、', '七、', 4.6), ('八、', '【寫完', 4.0)]
QNUM = re.compile(r'^\d+．')


def add_boxes(d, start, end, h):
    body = d.element.body
    els = list(body)
    si = next(i for i, e in enumerate(els) if (ptext(d, e) or '').startswith(start))
    ei = next((i for i, e in enumerate(els) if i > si and (ptext(d, e) or '').startswith(end)), len(els) - 1)
    chunk = els[si + 1:ei]
    if any(e.tag == qn('w:tbl') and '算式：' in ''.join(e.itertext()) for e in chunk):
        print(f'{start} 已經有書寫框，略過'); return
    qs = [i for i, e in enumerate(chunk) if QNUM.match(ptext(d, e) or '')]
    sect = d.sections[-1]
    col_w = (sect.page_width - sect.left_margin - sect.right_margin - Cm(1.0)) / 2
    for n, qi in enumerate(qs):
        group = chunk[qi:(qs[n + 1] if n + 1 < len(qs) else len(chunk))]
        blanks = [e for e in group if e.tag == qn('w:p') and not (ptext(d, e) or '').strip()
                  and not e.findall('.//' + qn('w:drawing'))]
        if len(blanks) < 4:          # 原本留白 4 行以上的才是要寫算式的題目
            continue
        for e in blanks:
            body.remove(e)
        keep = [e for e in group if e not in blanks]
        for e in keep:
            if e.tag == qn('w:p'):
                Paragraph(e, d).paragraph_format.keep_with_next = True
        size = next((r.font.size for r in Paragraph(group[0], d).runs if r.font.size), None)
        tbl = d.add_table(rows=2, cols=1)
        set_borders(tbl)
        tbl.autofit = False
        w = int(col_w - Cm(0.2))
        for ri, (txt, hh) in enumerate((('算式：', h), ('答：', 1.0))):
            row = tbl.rows[ri]
            row.height = Cm(hh)
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            cell = row.cells[0]
            cell.width = w
            p = cell.paragraphs[0]
            r = p.add_run(txt)
            if size:
                r.font.size = size
            if ri == 0:
                p.paragraph_format.keep_with_next = True
        keep[-1].addnext(tbl._tbl)
        sp = OxmlElement('w:p')
        tbl._tbl.addnext(sp)
        print(f'{start}{(ptext(d, group[0]) or "")[:3]} 加上書寫框')


for f in FILES:
    process(OFFICE / f)
