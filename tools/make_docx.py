# -*- coding: utf-8 -*-
"""
教師辦公室：把題目原稿（Markdown）排成可以印的 Word 檔。

用法：
    python tools/make_docx.py 題庫/五上_第2單元_小考.md
    python tools/make_docx.py 題庫/xxx.md --out 成品/考卷
    python tools/make_docx.py 題庫/xxx.md --no-pages      （不用 Word 算頁數、不轉 PDF，比較快）
    python tools/make_docx.py 題庫/xxx.md --no-pdf        （算頁數，但不轉 PDF）

原稿格式見 範例/考卷寫法範例.md。
輸出：學生版 <檔名>.docx、答案版 <檔名>_答案.docx（教案只有一份），旁邊各一份同名的 PDF。
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
    from docx.enum.section import WD_SECTION
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
except ImportError:
    print('需要先安裝 python-docx，請在命令列執行：python -m pip install python-docx')
    sys.exit(2)

OFFICE = Path(__file__).resolve().parent.parent
OUT_DIR = {'考卷': '成品/考卷', '學習單': '成品/學習單', '教案': '成品/教案'}
RED = RGBColor(0xC0, 0x1C, 0x1C)
GRAY = RGBColor(0x55, 0x55, 0x55)
CJK_FONT = '標楷體'
HEAD_FONT = '微軟正黑體'
LATIN_FONT = 'Times New Roman'
PAPER = {'A4': (21.0, 29.7), 'B4': (25.7, 36.4), 'A3': (29.7, 42.0)}
# 老師學校的預設：考卷 B4 雙欄 14 號固定行高 17pt；學習單 A4 13pt；教案 A4 12pt
DEFAULTS = {
    '考卷': {'紙張': 'B4', '欄數': '2', '字級': '14', '行高': '17'},
    '學習單': {'紙張': 'A4', '欄數': '1', '字級': '13', '行距': '1.3'},
    '教案': {'紙張': 'A4', '欄數': '1', '字級': '12', '行距': '1.3'},
}


# ---------------- 讀原稿 ----------------

def parse_source(text):
    text = text.replace('\r\n', '\n').replace('﻿', '')
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    meta = {}
    m = re.match(r'\s*---\n(.*?)\n---\n', text, flags=re.S)
    if m:
        for line in m.group(1).split('\n'):
            if ':' in line or '：' in line:
                k, v = re.split(r'[:：]', line, maxsplit=1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text.split('\n')


Q_RE = re.compile(r'^(\d+)[.．、]\s*(.*)$')
ANS_RE = re.compile(r'^\s*答\s*[:：]\s*(.*)$')
EXP_RE = re.compile(r'^\s*解析\s*[:：]\s*(.*)$')
IMG_RE = re.compile(r'^\s*!\[(.*?)\]\((.*?)\)\s*$')


def build_blocks(lines):
    """把原稿切成一塊一塊：heading / question / para / quote / table / image / answer / pagebreak / bullet"""
    blocks = []
    i = 0
    cur_q = None
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()
        indented = line.startswith('  ') or line.startswith('\t') or line.startswith('　')

        if not s:
            # 空行不結束題目（選項可能隔一行）
            i += 1
            continue
        if s in ('<分頁>', '<換頁>'):
            blocks.append({'t': 'pagebreak'}); cur_q = None; i += 1; continue
        ms = re.fullmatch(r'<留白\s*(\d+)\s*行?>', s)
        if ms:      # 數學直式、算式要留給學生寫的空白
            blocks.append({'t': 'space', 'n': min(int(ms.group(1)), 30)}); cur_q = None; i += 1; continue
        if s.startswith('### '):
            blocks.append({'t': 'h3', 'text': s[4:].strip()}); cur_q = None; i += 1; continue
        if s.startswith('## '):
            blocks.append({'t': 'h2', 'text': s[3:].strip()}); cur_q = None; i += 1; continue
        if s.startswith('# '):
            blocks.append({'t': 'h1', 'text': s[2:].strip()}); cur_q = None; i += 1; continue

        ma, me = ANS_RE.match(line), EXP_RE.match(line)
        if ma or me:
            target = cur_q if (cur_q is not None and (indented or True)) else None
            key = 'ans' if ma else 'exp'
            val = (ma or me).group(1).strip()
            if target is not None:
                target[key] = (target.get(key, '') + ('；' if target.get(key) else '') + val)
            else:
                blocks.append({'t': 'answer', 'kind': key, 'text': val})
            i += 1
            continue

        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                r = lines[i].strip().strip('|')
                cells = [c.strip() for c in r.split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c or '--') for c in cells):
                    rows.append(cells)
                i += 1
            blk = {'t': 'table', 'rows': rows}
            if cur_q is not None and indented:
                cur_q['extra'].append(blk)
            else:
                blocks.append(blk); cur_q = None
            continue

        if s.startswith('>'):
            qs = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                qs.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({'t': 'quote', 'lines': qs}); cur_q = None
            continue

        mi = IMG_RE.match(line)
        if mi:
            blk = {'t': 'image', 'alt': mi.group(1), 'path': mi.group(2)}
            if cur_q is not None and indented:
                cur_q['extra'].append(blk)
            else:
                blocks.append(blk)
            i += 1
            continue

        mq = Q_RE.match(s)
        if mq and not indented:
            cur_q = {'t': 'q', 'num': mq.group(1), 'text': mq.group(2), 'extra': []}
            blocks.append(cur_q)
            i += 1
            continue

        if cur_q is not None and indented:
            cur_q['extra'].append({'t': 'line', 'text': s})
            i += 1
            continue

        if s.startswith('- ') or s.startswith('* '):
            blocks.append({'t': 'bullet', 'text': s[2:].strip()}); cur_q = None; i += 1; continue

        blocks.append({'t': 'para', 'text': s}); cur_q = None
        i += 1
    return blocks


# ---------------- Word 工具 ----------------

def set_run_font(run, size=None, bold=None, color=None, underline=None, font=None):
    run.font.name = LATIN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts'); rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), font or CJK_FONT)
    rfonts.set(qn('w:ascii'), LATIN_FONT)
    rfonts.set(qn('w:hAnsi'), LATIN_FONT)
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if color is not None: run.font.color.rgb = color
    if underline is not None: run.underline = underline


FRAC_RE = re.compile(r'\{\{\s*(?:(\d+)\s+)?([^{}/\s]+)\s*/\s*([^{}/\s]+)\s*\}\}')


def add_frac(par, whole, num, den, size, color=None):
    """數學用：在段落裡放一個上下疊的分數（Word 方程式），帶分數把整數放在前面"""
    M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'

    def mrun(text):
        r = OxmlElement('m:r')
        rpr = OxmlElement('w:rPr')
        sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(round(size * 2)))); rpr.append(sz)
        if color is not None:
            c = OxmlElement('w:color'); c.set(qn('w:val'), str(color)); rpr.append(c)
        r.append(rpr)
        t = OxmlElement('m:t'); t.text = text; r.append(t)
        return r
    om = OxmlElement('m:oMath')
    if whole:
        om.append(mrun(whole))
    f = OxmlElement('m:f')
    for tag, val in (('m:num', num), ('m:den', den)):
        e = OxmlElement(tag); e.append(mrun(val)); f.append(e)
    om.append(f)
    par._p.append(om)


def add_rich(par, text, size, color=None, bold=False, font=None):
    """支援 **粗體**（粗體加底線，用在「不是」這類否定字），以及 {{3/5}}、{{2 3/5}} 這種上下疊的分數"""
    if '{{' in text:
        pos = 0
        for m in FRAC_RE.finditer(text):
            if m.start() > pos:
                add_rich(par, text[pos:m.start()], size, color, bold, font)
            add_frac(par, m.group(1), m.group(2), m.group(3), size, color)
            pos = m.end()
        if pos < len(text):
            _add_plain(par, text[pos:], size, color, bold, font)
        return
    _add_plain(par, text, size, color, bold, font)


def _add_plain(par, text, size, color=None, bold=False, font=None):
    parts = re.split(r'(\*\*.+?\*\*)', text)
    for p in parts:
        if not p:
            continue
        if p.startswith('**') and p.endswith('**'):
            r = par.add_run(p[2:-2]); set_run_font(r, size, True, color, True, font)
        else:
            r = par.add_run(p); set_run_font(r, size, bold, color, None, font)


def para_fmt(par, line_spacing, left=0.0, first=0.0, before=0, after=2, keep_next=False):
    pf = par.paragraph_format
    if isinstance(line_spacing, tuple):        # ('exact', 17) → 固定行高 17pt
        # 有上下疊分數的那一行改成「最小行高」，不然分數會被切掉看不見
        pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST if par._p.find(qn('m:oMath')) is not None else WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(line_spacing[1])
    else:
        pf.line_spacing = line_spacing
    pf.left_indent = Cm(left)
    pf.first_line_indent = Cm(first)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.keep_with_next = keep_next


def add_field(par, instr, size):
    r = par.add_run(); set_run_font(r, size)
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
    r._element.append(f1); r._element.append(it); r._element.append(f2)


def cell_border(cell, sz=8):
    tcPr = cell._element.get_or_add_tcPr()
    b = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement(f'w:{side}')
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:color'), '000000')
        b.append(e)
    tcPr.append(b)


def fix_table_width(t, total_cm, ncol):
    """表格固定寬度（雙欄時才不會超出欄外）"""
    t.autofit = False
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    tblPr = t._tbl.tblPr
    w = tblPr.find(qn('w:tblW'))
    if w is None:
        w = OxmlElement('w:tblW'); tblPr.append(w)
    w.set(qn('w:w'), str(int(total_cm * 567))); w.set(qn('w:type'), 'dxa')
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    cw = total_cm / ncol
    grid = t._tbl.tblGrid
    for gc in grid.findall(qn('w:gridCol')):
        gc.set(qn('w:w'), str(int(cw * 567)))
    for row in t.rows:
        for c in row.cells:
            c.width = Cm(cw)


def cell_shade(cell, fill):
    tcPr = cell._element.get_or_add_tcPr()
    sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), fill)
    tcPr.append(sh)


# ---------------- 排版 ----------------

class Builder:
    def __init__(self, meta, blocks, src_dir, answer):
        self.meta, self.blocks, self.src_dir, self.answer = meta, blocks, src_dir, answer
        self.kind = meta.get('類型', '考卷').strip() or '考卷'
        d = DEFAULTS.get(self.kind, DEFAULTS['考卷'])
        get = lambda k: (meta.get(k) or '').strip() or d.get(k, '')
        self.size = float(get('字級') or 12)
        self.paper = get('紙張').upper() if get('紙張').upper() in PAPER else 'A4'
        self.cols = max(1, min(3, int(float(get('欄數') or 1))))
        if (meta.get('行高') or '').strip() or (not (meta.get('行距') or '').strip() and d.get('行高')):
            self.ls = ('exact', float(get('行高') or 17))
        else:
            self.ls = float(get('行距') or 1.3)
        pw, ph = PAPER[self.paper]
        self.margin = 2.0 if self.paper != 'A4' else 1.8
        self.col_gap = 1.0
        self.text_w = pw - 2 * self.margin
        self.col_w = (self.text_w - self.col_gap * (self.cols - 1)) / self.cols
        self.doc = Document()
        self.warnings = []
        self.bracket = False

    def setup(self):
        sec = self.doc.sections[0]
        pw, ph = PAPER[self.paper]
        sec.page_width, sec.page_height = Cm(pw), Cm(ph)
        sec.left_margin = sec.right_margin = Cm(self.margin)
        sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.6)
        st = self.doc.styles['Normal']
        st.font.name = LATIN_FONT; st.font.size = Pt(self.size)
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts'); rpr.append(rf)
        rf.set(qn('w:eastAsia'), CJK_FONT)
        fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run('第 '); set_run_font(r, 9)
        add_field(fp, 'PAGE', 9)
        r = fp.add_run(' 頁／共 '); set_run_font(r, 9)
        add_field(fp, 'NUMPAGES', 9)
        r = fp.add_run(' 頁'); set_run_font(r, 9)

    def header(self):
        m = self.meta
        title = m.get('標題', '')
        if self.answer and self.kind != '教案':
            title += '（答案卷）'
        school = m.get('學校', '')
        if school:
            p = self.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_rich(p, school, self.size + 1, bold=True); para_fmt(p, 1.0, after=0)
        p = self.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_rich(p, title, self.size + 4, RED if self.answer and self.kind != '教案' else None, True, HEAD_FONT)
        para_fmt(p, 1.1, after=4)
        if self.kind == '教案':
            return
        info = []
        if m.get('年級'): info.append(m['年級'])
        if m.get('時間'): info.append('作答時間 ' + m['時間'])
        if m.get('總分'): info.append('總分 ' + m['總分'] + ' 分')
        if info and self.kind == '考卷':
            p = self.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_rich(p, '　'.join(info), self.size - 1, GRAY); para_fmt(p, 1.0, after=4)
        labels = ['班級', '座號', '姓名'] + (['得分'] if self.kind == '考卷' else [])
        widths = [3.0, 2.6, 6.0, 3.4][:len(labels)]
        t = self.doc.add_table(rows=1, cols=len(labels) * 2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for k, lab in enumerate(labels):
            c1, c2 = t.rows[0].cells[2 * k], t.rows[0].cells[2 * k + 1]
            c1.width, c2.width = Cm(1.3), Cm(widths[k])
            cp = c1.paragraphs[0]; add_rich(cp, lab, self.size - 1, bold=True)
            cell_border(c1); cell_border(c2); cell_shade(c1, 'EEEEEE')
        sp = self.doc.add_paragraph(); para_fmt(sp, 1.0, after=2)

    def start_columns(self):
        """表頭用整頁寬，下面的題目分成雙欄"""
        if self.cols < 2:
            return
        sec = self.doc.add_section(WD_SECTION.CONTINUOUS)
        sp = sec._sectPr
        cols = sp.find(qn('w:cols'))
        if cols is None:
            cols = OxmlElement('w:cols'); sp.append(cols)
        cols.set(qn('w:num'), str(self.cols)); cols.set(qn('w:space'), str(int(self.col_gap * 567)))

    def run(self):
        self.setup(); self.header(); self.start_columns()
        for b in self.blocks:
            getattr(self, 'b_' + b['t'])(b)
        return self.doc

    # --- 各種區塊 ---
    def b_space(self, b):
        for _ in range(b['n']):
            p = self.doc.add_paragraph(); r = p.add_run(''); set_run_font(r, self.size); para_fmt(p, self.ls, after=0)

    def b_pagebreak(self, b):
        p = self.doc.add_paragraph(); p.add_run().add_break(WD_BREAK.PAGE)

    def b_h1(self, b):
        p = self.doc.add_paragraph(); add_rich(p, b['text'], self.size + 3, bold=True, font=HEAD_FONT)
        para_fmt(p, 1.1, before=8, after=4, keep_next=True)

    def b_h2(self, b):
        self.bracket = self.kind != '教案' and ('是非' in b['text'] or '選擇' in b['text'])
        p = self.doc.add_paragraph(); add_rich(p, b['text'], self.size + 2 if self.kind == '考卷' else self.size + 1, bold=True, font=HEAD_FONT)
        para_fmt(p, 1.1, before=8, after=3, keep_next=True)

    def b_h3(self, b):
        p = self.doc.add_paragraph(); add_rich(p, b['text'], self.size, bold=True)
        para_fmt(p, 1.1, before=4, after=2, keep_next=True)

    def b_para(self, b):
        p = self.doc.add_paragraph(); add_rich(p, b['text'], self.size); para_fmt(p, self.ls)

    def b_bullet(self, b):
        p = self.doc.add_paragraph(); add_rich(p, '・' + b['text'], self.size); para_fmt(p, self.ls, left=0.5, first=-0.5)

    def b_answer(self, b):
        if not self.answer:
            return
        p = self.doc.add_paragraph()
        if b['kind'] == 'ans':
            add_rich(p, '答：' + b['text'], self.size - 1, RED, True)
        else:
            add_rich(p, '解析：' + b['text'], self.size - 2, GRAY)
        para_fmt(p, 1.1, left=0.6)

    def b_quote(self, b):
        t = self.doc.add_table(rows=1, cols=1)
        fix_table_width(t, self.col_w - 0.1, 1)
        c = t.rows[0].cells[0]; cell_border(c, 6)
        c.paragraphs[0].text = ''
        for k, line in enumerate(b['lines']):
            p = c.paragraphs[0] if k == 0 else c.add_paragraph()
            add_rich(p, line, self.size - 0.5); para_fmt(p, self.ls, after=1)
        sp = self.doc.add_paragraph(); para_fmt(sp, 1.0, after=0)

    def b_table(self, b, left=0.0):
        rows = b['rows']
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        t = self.doc.add_table(rows=len(rows), cols=ncol)
        fix_table_width(t, self.col_w - 0.1, ncol)
        for ri, r in enumerate(rows):
            for ci in range(ncol):
                cell = t.rows[ri].cells[ci]; cell_border(cell, 6)
                txt = r[ci] if ci < len(r) else ''
                p = cell.paragraphs[0]
                add_rich(p, txt, self.size - 0.5, bold=(ri == 0))
                para_fmt(p, 1.2, after=0)
                if ri == 0:
                    cell_shade(cell, 'F2F2F2'); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif not txt:
                    p.paragraph_format.space_after = Pt(self.size * 1.4)  # 讓學生有地方寫
        sp = self.doc.add_paragraph(); para_fmt(sp, 1.0, after=0)

    def b_image(self, b, left=0.0):
        path = (self.src_dir / b['path']).resolve() if not os.path.isabs(b['path']) else Path(b['path'])
        p = self.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if path.exists():
            try:
                p.add_run().add_picture(str(path), width=Cm(min(11.0, self.col_w - 0.5)))
            except Exception as e:
                add_rich(p, f'〔圖片無法放入：{b["path"]}〕', self.size, RED)
                self.warnings.append(f'圖片無法放入 {b["path"]}：{e}')
        else:
            add_rich(p, f'〔找不到圖片：{b["path"]}〕', self.size, RED)
            self.warnings.append(f'找不到圖片：{b["path"]}')
        if b.get('alt'):
            c = self.doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_rich(c, b['alt'], self.size - 2, GRAY); para_fmt(c, 1.0)

    def b_q(self, b):
        p = self.doc.add_paragraph()
        ans = b.get('ans', '')
        if self.bracket:
            if self.answer and ans:
                add_rich(p, '（', self.size); add_rich(p, ans.center(2, '　'), self.size, RED, True); add_rich(p, '）', self.size)
            else:
                add_rich(p, '（　　）', self.size)
        add_rich(p, f'{b["num"]}．', self.size)
        add_rich(p, b['text'], self.size)
        hang = 2.6 if self.bracket else 0.75
        para_fmt(p, self.ls, left=hang, first=-hang, before=2, after=1,
                 keep_next=bool(b['extra']))
        for k, x in enumerate(b['extra']):
            if x['t'] == 'line':
                xp = self.doc.add_paragraph(); add_rich(xp, x['text'], self.size)
                para_fmt(xp, self.ls, left=hang, after=1, keep_next=k < len(b['extra']) - 1)
            elif x['t'] == 'table':
                self.b_table(x)
            elif x['t'] == 'image':
                self.b_image(x)
        if self.kind != '教案' and not ans:
            self.warnings.append(f'第 {b["num"]} 題（「{b["text"][:12]}…」）沒有寫答案')
        if self.answer and (ans or b.get('exp')):
            if ans and not self.bracket:
                ap = self.doc.add_paragraph(); add_rich(ap, '答：' + ans, self.size - 1, RED, True)
                para_fmt(ap, 1.1, left=hang, after=0)
            if b.get('exp'):
                ep = self.doc.add_paragraph(); add_rich(ep, '解析：' + b['exp'], self.size - 2, GRAY)
                para_fmt(ep, 1.1, left=hang, after=2)


# ---------------- 檢查與頁數 ----------------

def check_scores(meta, blocks):
    msgs = []
    total = 0
    found = False
    for b in blocks:
        if b['t'] == 'h2':
            m = re.search(r'共\s*(\d+)\s*分', b['text'])
            if m:
                total += int(m.group(1)); found = True
    want = meta.get('總分')
    if found and want and want.isdigit() and int(want) != total:
        msgs.append(f'各大題「共○分」加起來是 {total} 分，和總分 {want} 不一樣')
    return msgs, (total if found else None)


def count_pages_with_word(paths):
    """Windows 上有裝 Word 時，用 Word 算頁數（算不出來就回傳空的）"""
    if os.name != 'nt' or not paths:
        return {}
    ps_paths = ','.join("'" + str(p).replace("'", "''") + "'" for p in paths)
    script = (
        "$ErrorActionPreference='Stop';"
        "$w=New-Object -ComObject Word.Application;$w.Visible=$false;"
        f"foreach($p in @({ps_paths})){{"
        "$d=$w.Documents.Open($p,$false,$true);"
        "Write-Output ($p+'|'+$d.ComputeStatistics(2));$d.Close($false)}};"
        "$w.Quit()"
    )
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                           capture_output=True, timeout=90, encoding='utf-8', errors='replace',
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        out = {}
        for line in (r.stdout or '').splitlines():
            if '|' in line:
                p, n = line.rsplit('|', 1)
                if n.strip().isdigit():
                    out[os.path.normcase(os.path.abspath(p.strip()))] = int(n)
        return out
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description='把題目原稿排成 Word')
    ap.add_argument('source')
    ap.add_argument('--out', default=None, help='輸出資料夾（預設依類型放到 成品/…）')
    ap.add_argument('--no-pages', action='store_true', help='不用 Word 計算頁數（也不轉 PDF）')
    ap.add_argument('--no-pdf', action='store_true', help='不要順便轉 PDF')
    a = ap.parse_args(argv)

    src = Path(a.source)
    if not src.is_absolute():
        src = (Path.cwd() / src) if (Path.cwd() / src).exists() else (OFFICE / src)
    if not src.exists():
        print(f'找不到原稿：{a.source}'); return 1
    meta, lines = parse_source(src.read_text(encoding='utf-8-sig'))
    kind = meta.get('類型', '考卷').strip() or '考卷'
    if kind not in OUT_DIR:
        print(f'「類型」寫的是「{kind}」，只能是 考卷、學習單 或 教案。先當成考卷排。'); kind = '考卷'; meta['類型'] = kind
    if not meta.get('標題'):
        meta['標題'] = src.stem
    blocks = build_blocks(lines)

    out_dir = Path(a.out) if a.out else OFFICE / OUT_DIR[kind]
    if not out_dir.is_absolute():
        out_dir = OFFICE / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs, warnings = [], []
    versions = [False] if kind == '教案' else [False, True]
    for ans in versions:
        bld = Builder(meta, blocks, src.parent, ans)
        doc = bld.run()
        name = src.stem + ('_答案' if ans else '') + '.docx'
        path = out_dir / name
        try:
            doc.save(str(path))
        except PermissionError:
            print(f'存不進 {path.name}：這個檔案可能正在 Word 裡開著，請先關掉再試一次。'); return 1
        outputs.append(path)
        if not ans:
            warnings += bld.warnings

    nq = sum(1 for b in blocks if b['t'] == 'q')
    score_msgs, total = check_scores(meta, blocks)
    warnings += score_msgs
    pdf_note = ''
    if a.no_pages:
        pages = {}
    else:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from to_pdf import word_batch, libreoffice_pdf
            pages = word_batch(outputs, pdf=not a.no_pdf)
            pages = {k: v for k, v in pages.items() if isinstance(v, int)}
            if not a.no_pdf and not pages and libreoffice_pdf(outputs):
                pdf_note = '（PDF 用 LibreOffice 轉的，請打開確認版面）'
        except Exception as e:
            pages = count_pages_with_word(outputs); pdf_note = f'（轉 PDF 失敗：{e}）'

    print(f'原稿：{src.name}（{kind}，{nq} 題' + (f'，配分合計 {total} 分' if total is not None else '') + '）')
    for p in outputs:
        n = pages.get(os.path.normcase(os.path.abspath(p)))
        try:
            rel = p.relative_to(OFFICE).as_posix()
        except ValueError:
            rel = str(p)
        print(f'輸出：{rel}' + (f'（{n} 頁）' if n else ''))
        if p.with_suffix('.pdf').exists() and not a.no_pages and not a.no_pdf:
            print('PDF ：' + rel[:-5] + '.pdf')
    if not pages and not a.no_pages and os.name == 'nt':
        print('（沒辦法用 Word 算頁數、轉 PDF，請打開檔案看一下；要 PDF 可以在 Word 裡另存成 PDF。）')
    if pdf_note:
        print(pdf_note)
    seen = set()
    for w in warnings:
        if w not in seen:
            print('注意：' + w); seen.add(w)
    return 0


if __name__ == '__main__':
    sys.exit(main())
