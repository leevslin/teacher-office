# -*- coding: utf-8 -*-
"""
社會科辦公室：期中到期末進度表 ⇄ 辦公室的進度清單（教學進度/進度計畫.json）

用法（員工請用這些指令，不要直接讀整個 進度計畫.json，檔案很大很耗額度）：
    python tools/plan_tool.py show 605            看 605 還沒上的堂（加 --all 看全部）
    python tools/plan_tool.py tick 605-02 11/13   把一堂打勾（日期省略＝今天）
    python tools/plan_tool.py untick 605-02       取消打勾
    python tools/plan_tool.py set 605-03 content "新的課程內容"
                                                  改欄位：content date period note workbook homework
    python tools/plan_tool.py check               檢查格式、列出各班已上幾堂、落後幾堂
    python tools/plan_tool.py export              匯出成 Excel（含打勾）
    python tools/plan_tool.py import 檔案.xlsx    把老師的 Excel 轉成進度清單

進度清單每一堂的欄位：
    id（不要改）、n 第幾堂、week 週次、date 日期 YYYY-MM-DD、wd 星期、period 節次、
    content 課程內容、workbook 課堂習作、homework 回家作業、
    done 是否上完、doneDate 哪天上完、note 備註
"""
import copy
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

OFFICE = Path(__file__).resolve().parent.parent
PLAN = OFFICE / '教學進度' / '進度計畫.json'
ORIGINAL = OFFICE / '教學進度' / '期中到期末進度表_原始.xlsx'
EXPORT = OFFICE / '教學進度' / '期中到期末進度表_最新.xlsx'


def need_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return openpyxl
    except ImportError:
        print('需要先安裝 openpyxl：python -m pip install openpyxl'); sys.exit(2)


def tw_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()


def to_iso(md, year_start):
    """'11/12' → 2026-11-12（8～12 月算上半年，1～7 月算隔年）"""
    m = re.match(r'\s*(\d{1,2})\s*/\s*(\d{1,2})', str(md or ''))
    if not m:
        return ''
    mo, d = int(m.group(1)), int(m.group(2))
    y = year_start if mo >= 8 else year_start + 1
    try:
        return datetime.date(y, mo, d).isoformat()
    except ValueError:
        return ''


def s(v):
    return '' if v is None else str(v).strip()


def do_import(xlsx):
    openpyxl = need_openpyxl()
    src = Path(xlsx)
    if not src.is_absolute():
        src = OFFICE / src
    wb = openpyxl.load_workbook(src)
    today = tw_today()
    year_start = today.year if today.month >= 8 else today.year - 1
    plan = {'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'source': ORIGINAL.name,
            'year_start': year_start, 'summary': {'lines': [], 'classes': [], 'notes': []}, 'classes': {}}
    old = {}
    if PLAN.exists():
        try:
            old = json.loads(PLAN.read_text(encoding='utf-8')).get('classes', {})
        except Exception:
            old = {}
    for ws in wb.worksheets:
        rows = [[s(c) for c in r] for r in ws.iter_rows(values_only=True)]
        if ws.title == '總表':
            mode = 'lines'
            for r in rows:
                if not any(r):
                    continue
                if r[0] == '班級':
                    mode = 'classes'; continue
                if r[0].startswith('說明'):
                    mode = 'notes'; continue
                if mode == 'classes' and re.fullmatch(r'\d{3}', r[0]):
                    plan['summary']['classes'].append({'cls': r[0], 'weekly': r[1], 'slots': r[2], 'total': r[3], 'review': r[4], 'remark': r[5]})
                elif mode == 'notes':
                    plan['summary']['notes'].append(r[0])
                else:
                    plan['summary']['lines'].append(r[0])
            continue
        if not re.fullmatch(r'\d{3}', ws.title.strip()):
            continue
        cls = ws.title.strip()
        title = rows[0][0] if rows and rows[0] else cls
        slots = re.search(r'上課時段：([^\s]+)', title)
        sessions, footer = [], []
        for r in rows[2:]:
            if not any(r):
                continue
            if re.fullmatch(r'\d+', r[4] or ''):
                n = int(r[4])
                sessions.append({'id': f'{cls}-{n:02d}', 'n': n, 'week': r[0], 'date': to_iso(r[1], year_start), 'wd': r[2],
                                 'period': r[3], 'content': r[5], 'workbook': r[6], 'homework': r[7] if len(r) > 7 else '',
                                 'done': False, 'doneDate': '', 'note': ''})
            elif r[0]:
                footer.append([r[0], r[5]])
        # 重新匯入時保留已打勾的紀錄
        prev = {x.get('id'): x for x in old.get(cls, {}).get('sessions', [])}
        for x in sessions:
            p = prev.get(x['id'])
            if p:
                x['done'], x['doneDate'], x['note'] = p.get('done', False), p.get('doneDate', ''), p.get('note', '')
        plan['classes'][cls] = {'title': title, 'grade': '六' if '六年級' in title else '五', 'slots': slots.group(1) if slots else '',
                                'total': len(sessions), 'sessions': sessions, 'footer': footer}
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != ORIGINAL.resolve():
        shutil.copy(src, ORIGINAL)
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'已匯入 {len(plan["classes"])} 班：' + '、'.join(f'{k}（{v["total"]} 堂）' for k, v in plan['classes'].items()))
    print(f'進度清單：{PLAN.relative_to(OFFICE).as_posix()}')


def load():
    if not PLAN.exists():
        print('還沒有進度清單，請先 import 老師的 Excel。'); sys.exit(1)
    return json.loads(PLAN.read_text(encoding='utf-8'))


def status(c, day):
    ss = c['sessions']
    done = sum(1 for x in ss if x.get('done'))
    overdue = [x for x in ss if not x.get('done') and x.get('date') and x['date'] < day]
    ahead = sum(1 for x in ss if x.get('done') and x.get('date') and x['date'] > day)
    return done, overdue, ahead


def do_check():
    plan = load()
    day = tw_today().isoformat()
    ok = True
    for cls, c in plan['classes'].items():
        ids = [x.get('id') for x in c['sessions']]
        if len(ids) != len(set(ids)):
            print(f'⚠ {cls}：有重複的 id'); ok = False
        dates = [x.get('date') for x in c['sessions'] if x.get('date')]
        if dates != sorted(dates):
            print(f'⚠ {cls}：日期沒有照順序'); ok = False
        for x in c['sessions']:
            if x.get('date') and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', x['date']):
                print(f'⚠ {cls} 第{x.get("n")}堂：日期格式要是 YYYY-MM-DD'); ok = False
        done, overdue, ahead = status(c, day)
        msg = f'落後 {len(overdue)} 堂' if overdue else (f'超前 {ahead} 堂' if ahead else '進度正常')
        print(f'{cls}：已上 {done}/{len(c["sessions"])} 堂，{msg}')
    print('格式檢查：' + ('沒問題' if ok else '有問題，請修正'))


def do_export():
    openpyxl = need_openpyxl()
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    plan = load()
    if ORIGINAL.exists():
        wb = openpyxl.load_workbook(ORIGINAL)
    else:
        wb = openpyxl.Workbook(); wb.active.title = '總表'
    thin = Side(style='thin', color='999999')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fill = {'exam': PatternFill('solid', fgColor='FFF2CC'), 'flex': PatternFill('solid', fgColor='DDEBF7'),
            'note': PatternFill('solid', fgColor='FCE4D6'), 'done': PatternFill('solid', fgColor='E2F0D9'),
            'late': PatternFill('solid', fgColor='F8CBAD')}
    day = tw_today().isoformat()
    for cls, c in plan['classes'].items():
        if cls in wb.sheetnames:
            ws = wb[cls]
            base_font = copy.copy(ws.cell(3, 6).font) if ws.max_row >= 3 else Font(name='標楷體', size=12)
            for rng in list(ws.merged_cells.ranges):
                if rng.min_row >= 3:
                    ws.unmerge_cells(str(rng))
            if ws.max_row >= 3:
                ws.delete_rows(3, ws.max_row)
        else:
            ws = wb.create_sheet(cls); base_font = Font(name='標楷體', size=12)
            ws.append([c.get('title', cls)])
            ws.append(['週次', '日期', '星期', '節次', '累計堂數', '課程內容（課本頁次）', '課堂習作（約15分鐘）', '回家作業（社會作業簿）'])
        hdr = ws.cell(2, 1)
        for col, name in ((9, '完成'), (10, '老師備註')):
            cell = ws.cell(2, col, name); cell.font = copy.copy(hdr.font); cell.fill = copy.copy(hdr.fill)
            cell.border = copy.copy(hdr.border); cell.alignment = copy.copy(hdr.alignment)
        ws.column_dimensions['I'].width = 12; ws.column_dimensions['J'].width = 26
        r = 3
        for x in c['sessions']:
            md = ''
            if x.get('date'):
                d = datetime.date.fromisoformat(x['date']); md = f'{d.month}/{d.day}'
            dd = ''
            if x.get('doneDate'):
                d2 = datetime.date.fromisoformat(x['doneDate']); dd = f'✓ {d2.month}/{d2.day}'
            vals = [x.get('week', ''), md, x.get('wd', ''), x.get('period', ''), x.get('n', ''), x.get('content', ''),
                    x.get('workbook', ''), x.get('homework', ''), dd if x.get('done') else '', x.get('note', '')]
            for col, v in enumerate(vals, 1):
                cell = ws.cell(r, col, v if v != '' else None)
                cell.font = copy.copy(base_font); cell.border = border
                cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='left' if col in (6, 7, 8, 10) else 'center')
            content = x.get('content', '')
            row_fill = fill['exam'] if '考' in content[:3] or '★考' in content else fill['flex'] if '機動' in content else None
            if row_fill:
                for col in range(1, 9):
                    ws.cell(r, col).fill = row_fill
            if x.get('done'):
                ws.cell(r, 9).fill = fill['done']
            elif x.get('date') and x['date'] < day:
                ws.cell(r, 9, '未上'); ws.cell(r, 9).fill = fill['late']
            r += 1
        for a, b in c.get('footer', []):
            ws.cell(r, 1, a).fill = fill['note']; ws.cell(r, 6, b).fill = fill['note']
            ws.cell(r, 1).font = copy.copy(base_font); ws.cell(r, 6).font = copy.copy(base_font)
            ws.cell(r, 6).alignment = Alignment(wrap_text=True, vertical='center')
            ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=10)
            r += 1
    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(EXPORT)
    except PermissionError:
        print(f'存不進 {EXPORT.name}：這個檔案可能正在 Excel 裡開著，請先關掉再試一次。'); sys.exit(1)
    print(f'輸出：{EXPORT.relative_to(OFFICE).as_posix()}')


def save(plan):
    plan['updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    tmp = PLAN.with_suffix('.tmp')
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(PLAN)


def find(plan, sid):
    cls = sid.split('-')[0]
    c = plan['classes'].get(cls)
    if not c:
        print(f'沒有 {cls} 班'); sys.exit(1)
    for x in c['sessions']:
        if x['id'] == sid:
            return c, x
    print(f'找不到 {sid}'); sys.exit(1)


def parse_date(v, plan):
    v = v.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return v
    d = to_iso(v, plan.get('year_start', tw_today().year))
    if not d:
        print(f'看不懂日期：{v}（用 11/16 或 2026-11-16）'); sys.exit(1)
    return d


def line(x):
    d = datetime.date.fromisoformat(x['date']) if x.get('date') else None
    when = f"{d.month}/{d.day}{'一二三四五六日'[d.weekday()]} {x.get('period', '')}" if d else '（未排日期）'
    mark = ('✓' + x['doneDate'][5:].replace('-', '/')) if x.get('done') and x.get('doneDate') else ('✓' if x.get('done') else '　')
    extra = '｜'.join(v for v in (x.get('workbook'), x.get('homework')) if v)
    s = f"{x['id']} {mark} {when}｜{x.get('content', '')}"
    if extra:
        s += f"｜{extra}"
    if x.get('note'):
        s += f"｜備註：{x['note']}"
    return s


def do_show(cls, all_rows):
    plan = load()
    c = plan['classes'].get(cls)
    if not c:
        print(f'沒有 {cls} 班，可用：' + '、'.join(plan['classes'])); sys.exit(1)
    done, overdue, ahead = status(c, tw_today().isoformat())
    print(f"{cls}｜{c.get('slots', '')}｜已上 {done}/{len(c['sessions'])}｜" + (f'落後 {len(overdue)} 堂' if overdue else '進度正常'))
    rows = c['sessions'] if all_rows else [x for x in c['sessions'] if not x.get('done')]
    for x in rows:
        print(line(x))
    if not all_rows:
        for a, b in c.get('footer', []):
            print(f'〔{a}〕{b}')


def do_tick(sid, date, on=True):
    plan = load()
    c, x = find(plan, sid)
    x['done'] = on
    x['doneDate'] = parse_date(date, plan) if on and date else (tw_today().isoformat() if on else '')
    save(plan)
    print(line(x))


def do_set(sid, field, value):
    if field not in ('content', 'date', 'period', 'note', 'workbook', 'homework'):
        print('只能改：content date period note workbook homework'); sys.exit(1)
    plan = load()
    c, x = find(plan, sid)
    if x.get('done') and field in ('date',):
        print('這堂已經打勾了，日期不能改'); sys.exit(1)
    if field == 'date':
        value = parse_date(value, plan)
        x['wd'] = '一二三四五六日'[datetime.date.fromisoformat(value).weekday()]
    x[field] = value
    save(plan)
    print(line(x))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    a = sys.argv[2:]
    if cmd == 'show' and a:
        do_show(a[0], '--all' in a); sys.exit(0)
    if cmd in ('tick', 'untick') and a:
        do_tick(a[0], a[1] if len(a) > 1 else '', cmd == 'tick'); sys.exit(0)
    if cmd == 'set' and len(a) >= 3:
        do_set(a[0], a[1], ' '.join(a[2:])); sys.exit(0)
    if cmd not in ('import', 'export', 'check'):
        print(__doc__); sys.exit(1)
    if sys.argv[1] == 'import':
        if len(sys.argv) < 3:
            print('請給 Excel 檔的路徑'); sys.exit(1)
        do_import(sys.argv[2])
    elif sys.argv[1] == 'export':
        do_export()
    else:
        do_check()
