# -*- coding: utf-8 -*-
"""
教師辦公室：和雲端（GitHub 私人倉庫）同步。

    python tools/cloud_sync.py setup https://github.com/帳號/倉庫.git   第一次連接（由 連接雲端.bat 執行）
    python tools/cloud_sync.py sync                                   手動同步一次
    python tools/cloud_sync.py status                                 看有沒有連上

連上之後，指令台（開辦公室.bat）開著時每 5 分鐘自動同步一次：
先把電腦上的改動存起來上傳，再把雲端（手機、網頁上的 Claude）改過的檔案拉回來。
哪些檔案不上傳寫在 .gitignore（課本 PDF、指令台對話紀錄、狀態板）。
"""
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

OFFICE = Path(__file__).resolve().parent.parent
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def git_exe():
    g = shutil.which('git')
    if g:
        return g
    for c in (r'C:\Program Files\Git\cmd\git.exe', r'C:\Program Files (x86)\Git\cmd\git.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\cmd\git.exe')):
        if os.path.exists(c):
            return c
    return None


def git(*args, interactive=False, timeout=180):
    exe = git_exe()
    if not exe:
        return 127, '這台電腦沒有裝 Git'
    env = dict(os.environ)
    if not interactive:                       # 背景同步時不要跳出登入視窗
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GCM_INTERACTIVE'] = 'never'
    try:
        r = subprocess.run([exe, *args], cwd=str(OFFICE), capture_output=not interactive, timeout=timeout,
                           encoding='utf-8', errors='replace', env=env,
                           creationflags=0 if interactive else NO_WINDOW)
    except subprocess.TimeoutExpired:
        return 124, '等太久沒有回應（網路可能不通）'
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip() if not interactive else ''


def remote_url():
    if not (OFFICE / '.git').exists():
        return None
    code, out = git('remote', 'get-url', 'origin')
    return out.strip() if code == 0 and out.strip() else None


def has_changes():
    code, out = git('status', '--porcelain')
    return code == 0 and bool(out.strip())


def commit_local(msg):
    git('add', '-A')
    if has_changes():
        code, out = git('commit', '-m', msg)
        return code == 0, out
    return True, ''


def setup(url):
    if not git_exe():
        print('這台電腦還沒有裝 Git。請先執行「連接雲端.bat」，它會幫你安裝。'); return 1
    first = not (OFFICE / '.git').exists()
    if first:
        git('init', '-b', 'main')
    git('config', 'user.name', '教師辦公室')
    git('config', 'user.email', 'teacher-office@users.noreply.github.com')
    git('config', 'core.quotepath', 'false')
    git('config', 'pull.rebase', 'true')
    if remote_url():
        git('remote', 'set-url', 'origin', url)
    else:
        git('remote', 'add', 'origin', url)
    print('整理要上傳的檔案……')
    commit_local('教師辦公室：第一次上傳' if first else '教師辦公室：重新連接雲端')
    print('連到 GitHub（第一次會跳出登入視窗，請登入你的 GitHub 帳號）……')
    code, _ = git('fetch', 'origin', interactive=True)
    if code != 0:
        print('連不上這個倉庫。請確認網址對不對、倉庫已經建好，而且你有登入。'); return 1
    code, out = git('ls-remote', '--heads', 'origin', 'main')
    if out.strip():          # 雲端已經有東西：先合併
        code, _ = git('pull', '--rebase', '--allow-unrelated-histories', 'origin', 'main', interactive=True)
        if code != 0:
            git('rebase', '--abort')
            print('雲端倉庫裡已經有不一樣的檔案，合併不起來。建議在 GitHub 開一個新的空倉庫再連一次。'); return 1
    print('上傳中（第一次檔案比較多，請稍等）……')
    code, _ = git('push', '-u', 'origin', 'main', interactive=True, timeout=1800)
    if code != 0:
        print('上傳失敗。請確認網路，再執行一次「連接雲端.bat」。'); return 1
    print('完成！之後開著辦公室時，每 5 分鐘會自動同步。')
    return 0


def sync():
    """回傳 (ok, 說明)。沒連雲端時回傳 (None, '')。"""
    if not git_exe() or not remote_url():
        return None, ''
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    ok, out = commit_local(f'電腦自動同步 {stamp}')
    if not ok:
        return False, '存檔失敗：' + out[-200:]
    code, out = git('pull', '--rebase', '--autostash', 'origin', 'main')
    kept = []
    if code != 0:
        if not (OFFICE / '.git' / 'rebase-merge').exists() and not (OFFICE / '.git' / 'rebase-apply').exists():
            return False, '從雲端拉檔案失敗（網路不通或還沒登入）：' + out[-160:]
        kept = resolve_conflicts(stamp)
        if kept is None:
            git('rebase', '--abort')
            return False, '雲端和電腦同一個檔案都改過，自動處理失敗。請跟 Claude 說「雲端同步有衝突」。'
    code, out = git('push', 'origin', 'main')
    if code != 0:
        return False, '上傳失敗（網路不通或還沒登入）：' + out[-160:]
    if kept:
        return True, '已同步。有檔案雲端和電腦都改過：用雲端的版本，電腦的版本另存成 ' + '、'.join(kept)
    return True, '已同步'


def resolve_conflicts(stamp):
    """同一個檔案兩邊都改過：留雲端的版本，電腦的版本另存一份「（電腦版 時間）」，不丟掉任何東西"""
    tag = stamp.replace('-', '').replace(' ', '-').replace(':', '')
    kept = []
    env = dict(os.environ, GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0')
    for _ in range(50):
        code, out = git('diff', '--name-only', '--diff-filter=U')
        files = [f for f in out.splitlines() if f.strip()] if code == 0 else []
        if not files:
            if (OFFICE / '.git' / 'rebase-merge').exists() or (OFFICE / '.git' / 'rebase-apply').exists():
                r = subprocess.run([git_exe(), 'rebase', '--continue'], cwd=str(OFFICE), capture_output=True,
                                   encoding='utf-8', errors='replace', env=env, creationflags=NO_WINDOW)
                if r.returncode != 0 and 'nothing to commit' not in (r.stdout + r.stderr):
                    subprocess.run([git_exe(), 'rebase', '--skip'], cwd=str(OFFICE), capture_output=True, env=env,
                                   creationflags=NO_WINDOW)
                continue
            return kept
        for f in files:
            p = OFFICE / f
            copy = p.with_name(f'{p.stem}（電腦版 {tag}）{p.suffix}')
            r = subprocess.run([git_exe(), 'show', f':3:{f}'], cwd=str(OFFICE), capture_output=True,
                               creationflags=NO_WINDOW)      # 重新套用的那一份＝電腦上改的
            if r.returncode == 0:
                copy.write_bytes(r.stdout)
                kept.append(copy.relative_to(OFFICE).as_posix())
            c2, _ = git('checkout', '--ours', '--', f)      # 雲端的版本
            if c2 != 0:
                git('rm', '-q', '--', f)
            git('add', '-A', '--', f, copy.relative_to(OFFICE).as_posix())
    return None


def main(argv):
    if not argv:
        print(__doc__); return 1
    if argv[0] == 'setup' and len(argv) > 1:
        return setup(argv[1].strip())
    if argv[0] == 'sync':
        ok, msg = sync()
        print('還沒連接雲端，請先執行「連接雲端.bat」。' if ok is None else msg)
        return 0 if ok else 1
    if argv[0] == 'status':
        u = remote_url()
        print(('已連接：' + u) if u else '還沒連接雲端。' + ('' if git_exe() else '（這台電腦也還沒裝 Git）'))
        return 0
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
