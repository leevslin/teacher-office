# -*- coding: utf-8 -*-
"""
教師辦公室：指令台

在老師的電腦上跑一個小網站（http://127.0.0.1:8780），
老師在網頁上對員工下指令，這個程式就呼叫 Claude Code（claude 指令）去做事，
並把過程、狀態板（辦公室狀態.js）即時更新。

只用 Python 內建模組。由 開辦公室.bat 啟動。
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PORT = 8780
OFFICE = Path(__file__).resolve().parent.parent
TOOLS = OFFICE / 'tools'
SESSION_FILE = TOOLS / 'console_session.json'
BOARD_FILE = OFFICE / '辦公室狀態.js'
IS_WIN = os.name == 'nt'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

STAFF = [
    # 省額度：平常都用 Sonnet，排版只是跑工具用 Haiku。需要最聰明的時候再在畫面上換成 Opus。
    {'key': 'beike', 'name': '芋圓', 'role': '備課', 'model': 'sonnet'},
    {'key': 'chuti', 'name': '珍奶', 'role': '出題', 'model': 'sonnet'},
    {'key': 'shenti', 'name': '仙草', 'role': '審題', 'model': 'sonnet'},
    {'key': 'paiban', 'name': '豆花', 'role': '排版', 'model': 'haiku'},
    {'key': 'shuxue', 'name': '阿穎', 'role': '數學', 'model': 'sonnet'},
]
STAFF_BY_KEY = {s['key']: s for s in STAFF}
ROLE_TO_KEY = {s['role']: s['key'] for s in STAFF}
ROLE_TO_KEY.update({s['name']: s['key'] for s in STAFF})
MODELS = [
    {'id': 'sonnet', 'label': 'Sonnet（平常用）'},
    {'id': 'haiku', 'label': 'Haiku（最省，簡單的事）'},
    {'id': 'opus', 'label': 'Opus（最聰明、最耗額度）'},
]
MODEL_IDS = {m['id'] for m in MODELS}

# 員工可以讀的翰林資料夾（電腦上有才加）
EXTRA_DIRS = [d for d in (r'C:\hanlin',) if os.path.isdir(d)]   # 翰林電子教科書是程式檔，讀了也沒用，不開放

# 員工不用問就能用的工具。其他（例如刪檔、執行別的程式）一律不准。
ALLOWED_TOOLS = [
    'Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'Grep', 'LS', 'TodoWrite',
    'WebSearch', 'WebFetch',
    'Bash(python:*)', 'Bash(py:*)', 'Bash(python3:*)', 'Bash(pip:*)',
    'Bash(ls:*)', 'Bash(dir:*)', 'Bash(pdftotext:*)',
    # 沒裝 Git for Windows 時，Claude Code 改用 PowerShell 執行指令
    'PowerShell(python:*)', 'PowerShell(py:*)', 'PowerShell(pip:*)', 'PowerShell(Get-ChildItem:*)',
]

NOTE = ('\n\n（指令台附註：這件工作從辦公室指令台來。辦公室狀態.js 的 staff 和 log 由指令台自動更新，你不用改。'
        '回覆最後一行寫「【完成】做完了什麼」，需要老師決定時寫「【待確認】要確認什麼」（20 字以內）。'
        '要交給同事時，在那一行上面另起一行寫「【交接】備課／出題／審題／排版／數學：要做的事和檔案路徑」。）')

LONG_CONTEXT = 60_000    # 對話超過這麼多 token，就不再自動接著聊、改開新對話

_lock = threading.RLock()
_board_lock = threading.Lock()
_version = [1]
_running = {}           # key -> Popen
_stop_flags = set()
_flags = {'prompt_file_ok': True}


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')


def hm():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%H:%M')


def brief(text, n=20):
    t = re.sub(r'\s+', ' ', str(text or '')).strip()
    return t if len(t) <= n else t[:n - 1] + '…'


def find_claude():
    for name in ('claude', 'claude.exe', 'claude.cmd'):
        p = shutil.which(name)
        if p:
            return p
    if IS_WIN:
        home = Path.home()
        for c in (home / '.local' / 'bin' / 'claude.exe',
                  home / 'AppData' / 'Roaming' / 'npm' / 'claude.cmd',
                  home / 'AppData' / 'Local' / 'Programs' / 'claude' / 'claude.exe'):
            if c.exists():
                return str(c)
    return None


def docx_ok():
    try:
        import docx  # noqa: F401
        return True
    except Exception:
        return False


CLAUDE = find_claude()
DOCX_OK = docx_ok()


# ---------------- 對話紀錄 ----------------

def new_conv(title='新對話'):
    return {'id': uuid.uuid4().hex[:10], 'title': title, 'created': now(), 'session_id': None,
            'events': [], 'context': 0}


def load_sessions():
    data = {}
    try:
        data = json.loads(SESSION_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    chans = data.get('channels') if isinstance(data, dict) else None
    chans = chans if isinstance(chans, dict) else {}
    for s in STAFF:
        ch = chans.get(s['key'])
        if not isinstance(ch, dict) or not ch.get('convs'):
            c = new_conv()
            ch = {'model': s['model'], 'active': c['id'], 'convs': [c]}
        if ch.get('model') not in MODEL_IDS:
            ch['model'] = s['model']
        if not any(c['id'] == ch.get('active') for c in ch['convs']):
            ch['active'] = ch['convs'][-1]['id']
        chans[s['key']] = ch
    data = {'channels': chans, 'cfg_rev': data.get('cfg_rev', 0) if isinstance(data, dict) else 0}
    if data['cfg_rev'] < 2:              # 改成省額度的預設模型（只做一次，之後老師自己換的會保留）
        for s in STAFF:
            chans[s['key']]['model'] = s['model']
    if data['cfg_rev'] < 3:              # 以前的「對話長度」算錯（把每一步加總），歸零重算
        for ch in chans.values():
            for c in ch['convs']:
                c['context'] = 0
    data['cfg_rev'] = 3
    return data


SESS = load_sessions()


def save_sessions():
    with _lock:
        tmp = SESSION_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(SESS, ensure_ascii=False, indent=1), encoding='utf-8')
        for _ in range(5):
            try:
                os.replace(tmp, SESSION_FILE); break
            except PermissionError:
                time.sleep(0.2)
        _version[0] += 1


def active_conv(key):
    ch = SESS['channels'][key]
    for c in ch['convs']:
        if c['id'] == ch['active']:
            return c
    return ch['convs'][-1]


def add_event(key, kind, text, conv=None, **extra):
    with _lock:
        c = conv or active_conv(key)
        ev = {'k': kind, 'text': text, 'time': hm(), 'ts': int(time.time())}
        ev.update(extra)
        c['events'].append(ev)
        if len(c['events']) > 400:
            c['events'] = c['events'][-400:]
        _version[0] += 1


# ---------------- 狀態板 ----------------

def read_board():
    raw = BOARD_FILE.read_text(encoding='utf-8-sig')
    head, sep, rest = raw.partition('=')
    body = rest.strip()
    if not sep or 'OFFICE_STATE' not in head:
        raise ValueError('格式不對')
    if body.endswith(';'):
        body = body[:-1]
    return json.loads(body)


def board_update(staff, status=None, task=None, log=None):
    with _board_lock:
        try:
            data = read_board()
        except Exception as e:
            print('狀態板讀不到，這次先不更新：', e)
            return
        t = now()
        if status:
            data.setdefault('staff', {})[staff] = {'status': status, 'task': brief(task, 24), 'since': t}
        if log:
            who, text = log
            lg = data.get('log') if isinstance(data.get('log'), list) else []
            lg.insert(0, {'time': t, 'who': who, 'text': brief(text, 60)})
            data['log'] = lg[:20]
        data['updated'] = t
        tmp = BOARD_FILE.with_name(BOARD_FILE.name + '.tmp')
        try:
            tmp.write_text('window.OFFICE_STATE = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n',
                           encoding='utf-8')
            for _ in range(5):
                try:
                    os.replace(tmp, BOARD_FILE); break
                except PermissionError:
                    time.sleep(0.2)
        except Exception as e:
            print('狀態板寫入失敗：', e)


def parse_ending(reply, fallback):
    """看回覆最後的【完成】【待確認】【交接】"""
    status, task = 'done', '完成：' + brief(fallback, 18)
    m = re.findall(r'【(待確認|完成)】\s*([^\n]+)', reply or '')
    if m:
        kind, text = m[-1]
        status = 'waiting' if kind == '待確認' else 'done'
        task = ('待確認：' if kind == '待確認' else '完成：') + brief(text, 18)
    handoffs = []
    for role, what in re.findall(r'【交接】\s*([^\s：:]{1,4})\s*[：:]\s*([^\n]+)', reply or ''):
        k = ROLE_TO_KEY.get(role.strip())
        if k:
            handoffs.append((k, what.strip()))
    return status, task, handoffs


# ---------------- 叫員工做事 ----------------

def rel(p):
    try:
        return Path(p).resolve().relative_to(OFFICE).as_posix()
    except Exception:
        return Path(str(p)).name or str(p)


def describe_tool(name, inp):
    inp = inp if isinstance(inp, dict) else {}
    fp = inp.get('file_path') or inp.get('path') or inp.get('notebook_path') or ''
    if name == 'Read':
        return f'讀 {rel(fp)}'
    if name == 'Write':
        return f'寫 {rel(fp)}'
    if name in ('Edit', 'MultiEdit'):
        return f'改 {rel(fp)}'
    if name in ('Glob', 'Grep'):
        return f'找 {brief(inp.get("pattern", ""), 40)}'
    if name == 'LS':
        return f'看資料夾 {rel(fp)}'
    if name in ('Bash', 'PowerShell'):
        return f'執行 {brief(inp.get("command", ""), 70)}'
    if name == 'WebSearch':
        return f'上網查：{brief(inp.get("query", ""), 40)}'
    if name == 'WebFetch':
        return f'看網頁：{brief(inp.get("url", ""), 50)}'
    if name == 'TodoWrite':
        return '整理待辦清單'
    return name


def build_cmd(key, model, session_id, staff_file, use_prompt_file):
    cmd = [CLAUDE, '-p', '--output-format', 'stream-json', '--verbose',
           '--model', model, '--permission-mode', 'acceptEdits']
    if use_prompt_file:
        cmd += ['--append-system-prompt-file', str(staff_file)]
    if EXTRA_DIRS:
        cmd += ['--add-dir'] + EXTRA_DIRS
    cmd += ['--allowedTools', ','.join(ALLOWED_TOOLS)]
    if session_id:
        cmd += ['--resume', session_id]
    return cmd


def run_job(key, text, conv):
    staff = STAFF_BY_KEY[key]
    staff_file = OFFICE / '員工' / f'{key}.md'
    model = SESS['channels'][key]['model']
    board_update(key, 'working', text, log=('teacher', f'叫{staff["name"]}：' + brief(text, 40)))
    final_text = ''
    retried_resume = False
    try:
        while True:
            use_file = _flags['prompt_file_ok']
            prompt = text + NOTE
            if not use_file and not conv.get('session_id'):
                prompt = ('（以下是你的員工設定，請照著做）\n\n'
                          + staff_file.read_text(encoding='utf-8') + '\n\n---\n\n老師的指示：\n' + prompt)
            cmd = build_cmd(key, model, conv.get('session_id'), staff_file, use_file)
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
            try:
                proc = subprocess.Popen(cmd, cwd=str(OFFICE), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env=env, creationflags=NO_WINDOW if IS_WIN else 0)
            except Exception as e:
                with _lock:
                    _running.pop(key, None)
                add_event(key, 'error', f'叫不動 Claude Code：{e}', conv)
                board_update(key, 'idle', '', log=(key, '出錯：叫不動 Claude Code'))
                save_sessions()
                return
            with _lock:
                _running[key] = proc
                _version[0] += 1
            err_buf = []
            threading.Thread(target=lambda: err_buf.append(proc.stderr.read().decode('utf-8', 'replace')),
                             daemon=True).start()
            try:
                proc.stdin.write(prompt.encode('utf-8')); proc.stdin.close()
            except Exception:
                pass
            got_result = False
            texts = []
            steps = 0
            for raw in proc.stdout:
                line = raw.decode('utf-8', 'replace').strip()
                if not line.startswith('{'):
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                typ = ev.get('type')
                if ev.get('session_id') and conv.get('session_id') != ev['session_id']:
                    with _lock:
                        conv['session_id'] = ev['session_id']
                if typ == 'assistant':
                    u = (ev.get('message') or {}).get('usage') or {}
                    ctx_now = sum(int(u.get(k) or 0) for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
                    if ctx_now:
                        with _lock:
                            conv['context'] = ctx_now      # 真正的對話長度＝最後一次送給 Claude 的量
                    for part in (ev.get('message') or {}).get('content') or []:
                        if part.get('type') == 'text' and part.get('text', '').strip():
                            texts.append(part['text'])
                            add_event(key, 'text', part['text'], conv)
                        elif part.get('type') == 'tool_use':
                            steps += 1
                            add_event(key, 'tool', describe_tool(part.get('name'), part.get('input')), conv)
                elif typ == 'user':
                    for part in (ev.get('message') or {}).get('content') or []:
                        if isinstance(part, dict) and part.get('type') == 'tool_result' and part.get('is_error'):
                            c = part.get('content')
                            c = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                            if 'permission' in c.lower() or '權限' in c:
                                add_event(key, 'sys', '這一步需要權限，指令台沒有開放，員工會改用別的方法：' + brief(c, 120), conv)
                elif typ == 'result':
                    got_result = True
                    ctx = conv.get('context', 0)
                    secs = round((ev.get('duration_ms') or 0) / 1000)
                    if ev.get('is_error'):
                        add_event(key, 'error', '做到一半出錯了：' + brief(ev.get('result') or ev.get('subtype'), 200), conv)
                    add_event(key, 'done', f'花了 {secs // 60} 分 {secs % 60} 秒・{steps} 個步驟・對話長度約 {round(ctx / 1000)}k', conv, context=ctx)
                    final_text = ev.get('result') or '\n'.join(texts)
            proc.wait()
            time.sleep(0.1)
            err = ''.join(err_buf)
            with _lock:
                _running.pop(key, None)
                _version[0] += 1
            if key in _stop_flags:
                _stop_flags.discard(key)
                add_event(key, 'sys', '老師按了停止，這件工作中斷了。', conv)
                board_update(key, 'idle', '', log=(key, '工作被停止：' + brief(text, 30)))
                save_sessions()
                return
            if got_result:
                break
            low = err.lower()
            if use_file and 'append-system-prompt-file' in err and ('unknown' in low or 'error' in low):
                _flags['prompt_file_ok'] = False   # 舊版 Claude Code，改用別的方式給員工設定
                continue
            if conv.get('session_id') and not retried_resume and ('no conversation found' in low or 'session' in low and 'not found' in low):
                retried_resume = True
                with _lock:
                    conv['session_id'] = None
                add_event(key, 'sys', '之前的對話接不上了，改用新的對話重做一次。', conv)
                continue
            if 'login' in low or 'api key' in low or 'authenticat' in low:
                msg = 'Claude Code 還沒登入。請開一個命令列視窗輸入 claude，照畫面登入一次，再回來重送。'
            else:
                msg = 'Claude Code 沒有正常結束。' + (('訊息：' + brief(err, 300)) if err.strip() else '')
            add_event(key, 'error', msg, conv)
            board_update(key, 'idle', '', log=(key, '出錯：' + brief(text, 30)))
            save_sessions()
            return
    except Exception as e:
        add_event(key, 'error', f'指令台出錯：{e}', conv)
        board_update(key, 'idle', '', log=(key, '出錯'))
        with _lock:
            _running.pop(key, None)
        save_sessions()
        return

    if key == 'beike':
        update_poster()          # 芋圓可能改了進度清單，海報跟著更新
    status, task, handoffs = parse_ending(final_text, text)
    for to, what in handoffs:
        add_event(key, 'handoff', what, conv, to=to)
    board_update(key, status, task, log=(key, task))
    save_sessions()


# ---------------- 檔案 ----------------

FILE_GROUPS = [('收件匣', '收件匣'), ('題庫', '題庫'), ('審題紀錄', '審題紀錄'), ('備課', '備課'),
               ('成品', '成品'), ('教學進度', '教學進度')]


def list_files():
    groups = []
    for label, sub in FILE_GROUPS:
        base = OFFICE / sub
        items = []
        if base.exists():
            for p in base.rglob('*'):
                if p.is_file() and not p.name.startswith(('.', '~$')) and p.name != 'README.md':
                    st = p.stat()
                    items.append({'path': p.relative_to(OFFICE).as_posix(), 'size': st.st_size,
                                  'mtime': st.st_mtime})
        items.sort(key=lambda x: -x['mtime'])
        groups.append({'name': label, 'files': items[:80]})
    return groups


# ---------------- 附件上傳 ----------------

MAX_UPLOAD = 100 * 1024 * 1024


def save_upload(name, raw):
    name = os.path.basename(name.replace('\\', '/')).strip() or '附件'
    name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', name)[:120]
    if name.startswith('.'):
        name = '_' + name
    day = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')
    folder = OFFICE / '收件匣' / '附件' / day
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / name
    stem, ext = os.path.splitext(name)
    k = 2
    while dest.exists():
        dest = folder / f'{stem}({k}){ext}'; k += 1
    dest.write_bytes(raw)
    return dest.relative_to(OFFICE).as_posix()


# ---------------- 每日回報各班進度 ----------------

PROGRESS_JSON = OFFICE / '教學進度' / '各班進度.json'
PROGRESS_MD = OFFICE / '教學進度' / '每日回報.md'
DEFAULT_CLASSES = {'五年級': ['508', '509', '511'], '六年級': ['602', '603', '604', '605']}
WEEKDAY = '一二三四五六日'


def class_list():
    try:
        c = read_board().get('board', {}).get('classes')
        if isinstance(c, dict) and c:
            return c
    except Exception:
        pass
    return DEFAULT_CLASSES


def load_progress():
    try:
        d = json.loads(PROGRESS_JSON.read_text(encoding='utf-8'))
        if isinstance(d, dict):
            d.setdefault('latest', {}); d.setdefault('history', [])
            return d
    except Exception:
        pass
    return {'latest': {}, 'history': []}


def save_progress(date, entries):
    """entries: [{cls, text, note}]；寫進 各班進度.json、每日回報.md，並更新黑板旁的班級海報"""
    d = load_progress()
    rows = [e for e in entries if (e.get('text') or '').strip() or (e.get('note') or '').strip()]
    if not rows:
        return 0
    for e in rows:
        rec = {'date': date, 'text': (e.get('text') or '').strip(), 'note': (e.get('note') or '').strip()}
        d['latest'][str(e['cls'])] = rec
        d['history'].append({'cls': str(e['cls']), **rec})
    d['history'] = d['history'][-600:]
    PROGRESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    try:
        wd = WEEKDAY[datetime.date.fromisoformat(date).weekday()]
    except Exception:
        wd = ''
    lines = [f'\n## {date}' + (f'（{wd}）' if wd else ''), '', '| 班級 | 上到哪 | 備註 |', '|---|---|---|']
    for e in rows:
        lines.append(f"| {e['cls']} | {(e.get('text') or '').strip().replace('|', '／')} | {(e.get('note') or '').strip().replace('|', '／')} |")
    if not PROGRESS_MD.exists():
        PROGRESS_MD.write_text('# 每日回報：各班上到哪裡\n\n> 老師在辦公室「進度」分頁填的紀錄，最新的在最下面。芋圓排進度、對照落後時讀這份。\n', encoding='utf-8')
    with PROGRESS_MD.open('a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    # 黑板旁海報顯示每班最新進度
    with _board_lock:
        try:
            data = read_board()
            data.setdefault('board', {})['classProgress'] = {k: (v['text'] or v['note'])[:16] + f"（{v['date'][5:].replace('-', '/')}）"
                                                             for k, v in d['latest'].items()}
            data['updated'] = now()
            BOARD_FILE.write_text('window.OFFICE_STATE = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
        except Exception as e:
            print('海報更新失敗：', e)
    update_poster()
    board_update('beike', None, None, log=('teacher', '回報進度：' + '、'.join(str(e['cls']) for e in rows)))
    return len(rows)


# ---------------- 進度清單（教學進度/進度計畫.json，從老師的 Excel 匯入） ----------------

PLAN_JSON = OFFICE / '教學進度' / '進度計畫.json'
_plan_lock = threading.Lock()
PLAN_FIELDS = ('content', 'date', 'period', 'note', 'workbook', 'homework', 'wd')


def load_plan():
    try:
        return json.loads(PLAN_JSON.read_text(encoding='utf-8'))
    except Exception:
        return None


def save_plan(plan):
    plan['updated'] = now()
    tmp = PLAN_JSON.with_suffix('.tmp')
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, PLAN_JSON)
    _version[0] += 1


def poster_from_plan(plan):
    out = {}
    for cls, c in plan.get('classes', {}).items():
        ss = c.get('sessions', [])
        done = [x for x in ss if x.get('done')]
        if done:
            last = done[-1]
            txt = re.sub(r'（[^）]*）', '', last.get('content', ''))
            out[cls] = f"{len(done)}/{len(ss)}堂 {txt}"[:22]
    return out


def update_poster():
    plan = load_plan()
    if not plan:
        return
    with _board_lock:
        try:
            data = read_board()
            cp = data.setdefault('board', {}).setdefault('classProgress', {})
            cp.update(poster_from_plan(plan))
            data['updated'] = now()
            BOARD_FILE.write_text('window.OFFICE_STATE = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
        except Exception as e:
            print('海報更新失敗：', e)


def plan_session(plan, cls, sid):
    c = plan.get('classes', {}).get(str(cls))
    if not c:
        raise KeyError('沒有這個班')
    for x in c.get('sessions', []):
        if x.get('id') == sid:
            return x
    raise KeyError('找不到這一堂')


def run_plan_tool(*args):
    r = subprocess.run([sys.executable, str(TOOLS / 'plan_tool.py'), *args], cwd=str(OFFICE), capture_output=True,
                       timeout=120, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'),
                       creationflags=NO_WINDOW if IS_WIN else 0)
    return r.returncode == 0, ((r.stdout or '') + (r.stderr or '')).strip()


def safe_path(p):
    q = (OFFICE / p).resolve()
    q.relative_to(OFFICE)   # 不在辦公室裡會出錯
    return q


def run_docx(path):
    q = safe_path(path)
    r = subprocess.run([sys.executable, str(TOOLS / 'make_docx.py'), str(q)], cwd=str(OFFICE),
                       capture_output=True, timeout=180, encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'),
                       creationflags=NO_WINDOW if IS_WIN else 0)
    out = (r.stdout or '') + (r.stderr or '')
    board_update('paiban', None, None, log=('teacher', '轉 Word＋PDF：' + q.name))
    return r.returncode == 0, out.strip()


def run_pdf(path):
    q = safe_path(path)
    r = subprocess.run([sys.executable, str(TOOLS / 'to_pdf.py'), str(q)], cwd=str(OFFICE),
                       capture_output=True, timeout=240, encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'),
                       creationflags=NO_WINDOW if IS_WIN else 0)
    return r.returncode == 0, ((r.stdout or '') + (r.stderr or '')).strip()


# ---------------- 網站 ----------------

def state_payload():
    with _lock:
        chans = {}
        for s in STAFF:
            ch = SESS['channels'][s['key']]
            c = active_conv(s['key'])
            chans[s['key']] = {
                'model': ch['model'], 'active': ch['active'],
                'convs': [{'id': x['id'], 'title': x['title'], 'created': x['created'], 'n': len(x['events'])}
                          for x in ch['convs']],
                'events': c['events'], 'context': c.get('context', 0),
                'running': s['key'] in _running,
            }
        return {'v': _version[0], 'staff': STAFF, 'models': MODELS, 'channels': chans,
                'claude_ok': bool(CLAUDE), 'docx_ok': DOCX_OK, 'is_win': IS_WIN,
                'extra_dirs': EXTRA_DIRS, 'long_context': LONG_CONTEXT,
                'plan_mtime': PLAN_JSON.stat().st_mtime if PLAN_JSON.exists() else None}


STATIC = {'/': ('辦公室.html', 'text/html'), '/辦公室.html': ('辦公室.html', 'text/html'),
          '/office3d.js': ('office3d.js', 'text/javascript'),
          '/辦公室狀態.js': ('辦公室狀態.js', 'text/javascript'),
          '/lib/three.module.js': ('lib/three.module.js', 'text/javascript'),
          '/lib/OrbitControls.js': ('lib/OrbitControls.js', 'text/javascript')}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        qs = parse_qs(u.query)
        if path in STATIC:
            name, ctype = STATIC[path]
            f = OFFICE / name
            if not f.exists():
                self.send_error(404); return
            body = f.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', ctype + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == '/api/state':
            v = qs.get('v', ['0'])[0]
            if v == str(_version[0]):
                self.send_json({'v': _version[0], 'same': True}); return
            self.send_json(state_payload()); return
        if path == '/api/conv':
            key, cid = qs.get('staff', [''])[0], qs.get('id', [''])[0]
            ch = SESS['channels'].get(key)
            c = next((x for x in (ch or {}).get('convs', []) if x['id'] == cid), None)
            if not c:
                self.send_json({'error': '找不到這段對話'}, 404); return
            self.send_json({'events': c['events'], 'title': c['title']}); return
        if path == '/api/files':
            self.send_json({'groups': list_files()}); return
        if path == '/api/plan':
            self.send_json({'plan': load_plan(), 'today': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()}); return
        if path == '/api/progress':
            d = load_progress()
            self.send_json({'classes': class_list(), 'latest': d['latest'], 'history': d['history'][-60:]}); return
        self.send_error(404)

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        if path == '/api/upload':
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_UPLOAD:
                self.send_json({'error': '檔案太大了（上限 100MB）'}, 413); return
            raw = self.rfile.read(n)
            name = unquote(parse_qs(urlparse(self.path).query).get('name', ['附件'])[0])
            try:
                rel_path = save_upload(name, raw)
            except Exception as e:
                self.send_json({'error': f'存不進去：{e}'}, 500); return
            self.send_json({'ok': True, 'path': rel_path}); return
        try:
            n = int(self.headers.get('Content-Length') or 0)
            data = json.loads(self.rfile.read(n).decode('utf-8') or '{}') if n else {}
        except Exception:
            self.send_json({'error': '看不懂送來的資料'}, 400); return
        key = data.get('staff')
        if path.startswith('/api/') and path not in ('/api/open', '/api/reveal', '/api/docx', '/api/pdf', '/api/progress') and not path.startswith('/api/plan') and key not in STAFF_BY_KEY:
            self.send_json({'error': '沒有這位員工'}, 400); return

        if path == '/api/send':
            text = (data.get('text') or '').strip()
            if not text:
                self.send_json({'error': '指令是空的'}, 400); return
            if not CLAUDE:
                self.send_json({'error': '這台電腦找不到 Claude Code（claude 指令），請看 開始使用.md 安裝。'}, 400); return
            with _lock:
                if key in _running:
                    self.send_json({'error': f'{STAFF_BY_KEY[key]["name"]}還在忙上一件事'}, 409); return
                conv = active_conv(key)
                if data.get('fresh') and conv['events']:      # 新工作：自動開一段新對話，不帶前面的內容（省額度）
                    ch = SESS['channels'][key]
                    conv = new_conv(); ch['convs'].append(conv); ch['active'] = conv['id']
                    if len(ch['convs']) > 30:
                        ch['convs'] = ch['convs'][-30:]
                if not conv['events']:
                    conv['title'] = brief(data.get('title') or text, 14)
                add_event(key, 'me', text, conv)
                _running[key] = None   # 先佔位，避免連按兩次
            threading.Thread(target=run_job, args=(key, text, conv), daemon=True).start()
            save_sessions()
            self.send_json({'ok': True}); return

        if path == '/api/stop':
            with _lock:
                p = _running.get(key)
            if p:
                _stop_flags.add(key)
                try:
                    if IS_WIN:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True,
                                       creationflags=NO_WINDOW)
                    else:
                        p.kill()
                except Exception:
                    pass
            self.send_json({'ok': True}); return

        if path == '/api/new':
            with _lock:
                if key in _running:
                    self.send_json({'error': '工作做完才能開新對話'}, 409); return
                ch = SESS['channels'][key]
                cur = active_conv(key)
                if cur['events']:
                    c = new_conv(); ch['convs'].append(c); ch['active'] = c['id']
                    if len(ch['convs']) > 30:
                        ch['convs'] = ch['convs'][-30:]
            board_update(key, 'idle', '')
            save_sessions()
            self.send_json({'ok': True}); return

        if path == '/api/switch':
            with _lock:
                if key in _running:
                    self.send_json({'error': '工作做完才能換對話'}, 409); return
                ch = SESS['channels'][key]
                if any(c['id'] == data.get('id') for c in ch['convs']):
                    ch['active'] = data['id']
            save_sessions()
            self.send_json({'ok': True}); return

        if path == '/api/delconv':
            with _lock:
                ch = SESS['channels'][key]
                cid = data.get('id')
                if key in _running and cid == ch['active']:
                    self.send_json({'error': '正在用的對話不能刪'}, 409); return
                ch['convs'] = [c for c in ch['convs'] if c['id'] != cid]
                if not ch['convs']:
                    ch['convs'] = [new_conv()]
                if not any(c['id'] == ch['active'] for c in ch['convs']):
                    ch['active'] = ch['convs'][-1]['id']
            save_sessions()
            self.send_json({'ok': True}); return

        if path == '/api/model':
            if data.get('model') not in MODEL_IDS:
                self.send_json({'error': '沒有這個模型'}, 400); return
            with _lock:
                SESS['channels'][key]['model'] = data['model']
            save_sessions()
            self.send_json({'ok': True}); return

        if path in ('/api/open', '/api/reveal'):
            try:
                q = safe_path(data.get('path') or '')
            except Exception:
                self.send_json({'error': '只能開辦公室裡的檔案'}, 400); return
            if not q.exists():
                self.send_json({'error': '找不到這個檔案'}, 404); return
            if not IS_WIN:
                self.send_json({'error': '只有在 Windows 上才能直接開檔'}, 400); return
            try:
                if path == '/api/open':
                    os.startfile(str(q))
                else:
                    subprocess.Popen(['explorer', '/select,', str(q)])
            except Exception as e:
                self.send_json({'error': f'開不起來：{e}'}, 500); return
            self.send_json({'ok': True}); return

        if path in ('/api/plan/check', '/api/plan/edit'):
            with _plan_lock:
                plan = load_plan()
                if not plan:
                    self.send_json({'error': '還沒有進度清單'}, 404); return
                try:
                    x = plan_session(plan, data.get('cls'), data.get('id'))
                except KeyError as e:
                    self.send_json({'error': str(e)}, 404); return
                if path == '/api/plan/check':
                    x['done'] = bool(data.get('done'))
                    x['doneDate'] = (data.get('date') or datetime.date.today().isoformat()) if x['done'] else ''
                else:
                    for k in PLAN_FIELDS:
                        if k in data and isinstance(data[k], str):
                            x[k] = data[k].strip()
                save_plan(plan)
            if path == '/api/plan/check':
                update_poster()
            self.send_json({'ok': True, 'session': x}); return

        if path == '/api/plan/export':
            ok, out = run_plan_tool('export')
            self.send_json({'ok': ok, 'output': out, 'path': '教學進度/期中到期末進度表_最新.xlsx'}); return

        if path == '/api/plan/import':
            ok, out = run_plan_tool('import', str(safe_path(data.get('path') or '')))
            update_poster()
            self.send_json({'ok': ok, 'output': out}); return

        if path == '/api/progress':
            date = (data.get('date') or '').strip() or datetime.date.today().isoformat()
            entries = data.get('entries') if isinstance(data.get('entries'), list) else []
            try:
                n_saved = save_progress(date, entries)
            except Exception as e:
                self.send_json({'error': f'存不進去：{e}'}, 500); return
            self.send_json({'ok': True, 'saved': n_saved}); return

        if path == '/api/pdf':
            p = data.get('path') or ''
            if not p.lower().endswith('.docx'):
                self.send_json({'error': '只有 Word 檔（.docx）可以轉 PDF'}, 400); return
            try:
                ok, out = run_pdf(p)
            except Exception as e:
                self.send_json({'error': f'轉 PDF 失敗：{e}'}, 500); return
            self.send_json({'ok': ok, 'output': out}); return

        if path == '/api/docx':
            p = data.get('path') or ''
            if not p.endswith('.md'):
                self.send_json({'error': '只有 .md 原稿可以轉 Word'}, 400); return
            try:
                ok, out = run_docx(p)
            except Exception as e:
                self.send_json({'error': f'轉檔失敗：{e}'}, 500); return
            self.send_json({'ok': ok, 'output': out}); return

        self.send_error(404)


def cloud_loop():
    """連了雲端（GitHub）的話，每 5 分鐘同步一次：電腦的改動上傳、雲端的改動拉回來"""
    try:
        sys.path.insert(0, str(TOOLS))
        import cloud_sync
    except Exception as e:
        print('雲端同步程式載入失敗：', e); return
    last = None
    while True:
        try:
            ok, msg = cloud_sync.sync()
        except Exception as e:
            ok, msg = False, f'雲端同步出錯：{e}'
        if ok is None:
            return                       # 沒連雲端就不做
        if msg != last or not ok:
            print(f'[{hm()}] 雲端：{msg}')
        if (not ok and msg != last) or (ok and '另存成' in msg):
            board_update('paiban', None, None, log=('teacher', '雲端同步：' + msg))
        last = msg
        time.sleep(300)


def main():
    no_browser = '--no-browser' in sys.argv
    url = f'http://127.0.0.1:{PORT}/'
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    except OSError:
        print('辦公室好像已經開著了，直接打開網頁。')
        if not no_browser:
            webbrowser.open(url)
        return
    print('=' * 50)
    print('  教師辦公室 指令台')
    print('  網址：' + url)
    print('  Claude Code：' + (CLAUDE or '找不到！請看 開始使用.md'))
    print('  Word 排版工具：' + ('可以用' if DOCX_OK else '還沒裝 python-docx'))
    print('  翰林資料夾：' + ('、'.join(EXTRA_DIRS) if EXTRA_DIRS else '沒找到'))
    try:
        sys.path.insert(0, str(TOOLS)); import cloud_sync as _cs
        _u = _cs.remote_url()
        print('  雲端同步：' + (('每 5 分鐘同步到 ' + _u) if _u else '還沒連接（要用請點兩下 連接雲端.bat）'))
    except Exception:
        pass
    print('  要關掉辦公室：關掉這個視窗')
    print('=' * 50)
    # 上次沒做完就關掉的員工，狀態改回閒著
    try:
        data = read_board()
        for k, v in (data.get('staff') or {}).items():
            if isinstance(v, dict) and v.get('status') == 'working':
                board_update(k, 'idle', '')
    except Exception:
        pass
    if not no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    threading.Thread(target=cloud_loop, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
