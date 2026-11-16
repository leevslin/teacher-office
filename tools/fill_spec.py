# -*- coding: utf-8 -*-
"""
教師辦公室：把考卷的雙向細目表填進學校的「試卷檢核表與雙向細目表」Word 範本。

用法：
    python tools/fill_spec.py 題庫/數學_四上_第6-10單元_期末考_細目表.json

細目表 JSON 的寫法（阿穎出題時一起寫，放在題庫/，和考卷原稿同名加「_細目表」）：
{
  "範本": "佩穎數學檔案/114學年度定期評量試卷檢核表與雙向細目表.docx",
  "學年度": "115", "年級": "四", "類別": "期末", "領域": "數學",
  "範圍": {"起": "六", "迄": "十", "頁起": "82", "頁迄": "149"},
  "時間": "40", "難易度": "適中",
  "素養題": "第五大題第3小題、第七大題第1小題",
  "單元": [
    {"名稱": "第六單元\\n分數", "列": [
      {"題型": "是非題", "記憶": [1, 2], "理解": [1, 2], "高層次": [0, 0]},
      {"題型": "選擇題", "記憶": [1, 2], "理解": [2, 4], "高層次": [0, 0]}
    ]}
  ]
}
每一格是 [題數, 配分]。輸出到 成品/考卷/<JSON 檔名去掉「_細目表」>_檢核表與雙向細目表.docx。
檢核表的勾選欄（□）留給老師自己勾。
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
try:
    import docx
except ImportError:
    print('需要先安裝 python-docx：python -m pip install python-docx'); sys.exit(2)

OFFICE = Path(__file__).resolve().parent.parent


def set_text(cell, text):
    """改格子的字，保留原本第一段第一個字的字型大小"""
    paras = cell.paragraphs
    lines = str(text).split('\n')
    p0 = paras[0]
    runs = p0.runs
    if runs:
        runs[0].text = lines[0]
        for r in runs[1:]:
            r.text = ''
    else:
        p0.add_run(lines[0])
    for p in paras[1:]:
        p._p.getparent().remove(p._p)
    for ln in lines[1:]:
        np_ = cell.add_paragraph()
        r = np_.add_run(ln)
        if runs:
            r.font.size = runs[0].font.size; r.font.name = runs[0].font.name
            rpr = runs[0]._r.rPr
            if rpr is not None:
                r._r.insert(0, __import__('copy').deepcopy(rpr))
        np_.alignment = p0.alignment


def replace_in_par(par, old, new):
    if old not in par.text:
        return False
    full = par.text.replace(old, new)
    runs = par.runs
    if runs:
        runs[0].text = full
        for r in runs[1:]:
            r.text = ''
    return True


def uniq(row):
    out, prev = [], None
    for i, c in enumerate(row.cells):
        if c._tc is prev:
            continue
        prev = c._tc
        out.append((i, c))
    return out


def tick(text, choice):
    """把「□適中□偏難□偏易」裡選的那個改成 ■，其他保持 □"""
    text = text.replace('■', '□')
    return text.replace('□' + choice, '■' + choice)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = Path(sys.argv[1])
    if not src.is_absolute():
        src = OFFICE / src
    spec = json.loads(src.read_text(encoding='utf-8'))
    tpl = OFFICE / spec.get('範本', '佩穎數學檔案/114學年度定期評量試卷檢核表與雙向細目表.docx')
    d = docx.Document(str(tpl))
    year, grade, kind, field = spec.get('學年度', '115'), spec['年級'], spec.get('類別', '期末'), spec.get('領域', '數學')
    rg = spec['範圍']
    rng = f"第  {rg['起']}  單元至第  {rg['迄']}  單元(課本第  {rg.get('頁起', '   ')}  頁~  {rg.get('頁迄', '   ')}  頁)"
    kind_txt = '■期中評量  □期末評量' if kind == '期中' else '□期中評量  ■期末評量'
    fields = '國語 英語 數學 社會 自然科學'.split()
    field_txt = ''.join(('■' if f == field else '□') + f for f in fields)

    for p in d.paragraphs:
        replace_in_par(p, '114學年度', f'{year}學年度')
        if '※試卷抬頭' in p.text:
            replace_in_par(p, p.text, f'※試卷抬頭：桃園市八德國小{year}學年度第1學期{grade}年級{field}領域{kind}評量試卷')

    t0, t3 = d.tables[0], d.tables[3]
    c = dict(uniq(t0.rows[0])); set_text(c[1], f'  {grade}  年級'); set_text(c[4], kind_txt)
    c = dict(uniq(t0.rows[1])); set_text(c[1], field_txt)
    c = dict(uniq(t0.rows[2])); set_text(c[1], rng)

    c = dict(uniq(t3.rows[0])); set_text(c[2], f'___{grade}___年級'); set_text(c[8], kind_txt)
    c = dict(uniq(t3.rows[1])); set_text(c[2] if 2 in c else list(c.values())[1], field_txt)
    c = dict(uniq(t3.rows[2])); set_text(c[2], rng)
    c = dict(uniq(t3.rows[3])); set_text(c[2], f"___{spec.get('時間', '40')}___分鐘"); set_text(c[8], tick(c[8].text, spec.get('難易度', '適中')))
    if spec.get('素養題'):
        c = dict(uniq(t3.rows[4])); set_text(c[2], spec['素養題'])

    # 單元列：範本第 8 列起到「合計」前，第一欄合併成一組一組
    first, last = 8, len(t3.rows) - 2
    groups = []
    for ri in range(first, last + 1):
        tc = t3.rows[ri].cells[0]._tc
        if groups and groups[-1][0] is tc:
            groups[-1][1].append(ri)
        else:
            groups.append([tc, [ri]])
    units = spec['單元']
    if len(units) > len(groups):
        print(f'注意：範本只有 {len(groups)} 組單元列，多的單元沒有填進去'); units = units[:len(groups)]
    tot = {'記憶': [0, 0], '理解': [0, 0], '高層次': [0, 0]}
    COLS = {'題型': 1, '記憶': (3, 5), '理解': (7, 9), '高層次': (10, 11), '合計': 12}
    for gi, (tc, rows) in enumerate(groups):
        u = units[gi] if gi < len(units) else {'名稱': '', '列': []}
        set_text(t3.rows[rows[0]].cells[0], u['名稱'])
        lines = list(u.get('列', []))
        if len(lines) > len(rows):        # 題型比格子多：多的併成「其他」
            extra = lines[len(rows) - 1:]
            merged = {'題型': '其他（' + '、'.join(x['題型'] for x in extra) + '）'}
            for k in ('記憶', '理解', '高層次'):
                merged[k] = [sum(x.get(k, [0, 0])[0] for x in extra), sum(x.get(k, [0, 0])[1] for x in extra)]
            lines = lines[:len(rows) - 1] + [merged]
        unit_sum = 0
        for k, ri in enumerate(rows):
            cells = dict(uniq(t3.rows[ri]))
            if k >= len(lines):
                for col in (1, 3, 5, 7, 9, 10, 11):
                    if col in cells: set_text(cells[col], '')
                continue
            ln = lines[k]
            set_text(cells[1], ln.get('題型', ''))
            s = 0
            for key in ('記憶', '理解', '高層次'):
                n, pts = (ln.get(key) or [0, 0])
                a, b = COLS[key]
                set_text(cells[a], str(n) if n else ''); set_text(cells[b], str(pts) if pts else '')
                tot[key][0] += n; tot[key][1] += pts; s += pts
            unit_sum += s
        # 「合計」欄在範本裡是一個單元合併成一格，填這個單元的總分
        set_text(dict(uniq(t3.rows[rows[0]]))[12], str(unit_sum) if unit_sum else '')
    total = sum(v[1] for v in tot.values())
    c = dict(uniq(t3.rows[len(t3.rows) - 1]))
    keys = sorted(k for k in c if k > 0)
    for col, key in zip(keys[:3], ('記憶', '理解', '高層次')):
        set_text(c[col], f'{tot[key][0]} 題／{tot[key][1]} 分')
    if len(keys) >= 4:
        set_text(c[keys[3]], f'{total} 分')

    name = src.stem.replace('_細目表', '')
    out = OFFICE / '成品' / '考卷' / f'{name}_檢核表與雙向細目表.docx'
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out))
    print('輸出：' + str(out.relative_to(OFFICE)))
    print(f"記憶 {tot['記憶'][1]} 分、理解 {tot['理解'][1]} 分、高層次 {tot['高層次'][1]} 分，合計 {total} 分")
    if total != 100:
        print(f'注意：合計是 {total} 分，不是 100 分')
    if tot['高層次'][1] > 10:
        print(f"注意：高層次（素養）題 {tot['高層次'][1]} 分，超過學校上限 10 分")


if __name__ == '__main__':
    main()
