# -*- coding: utf-8 -*-
"""
教師辦公室：把 Word 檔轉成 PDF（學校要 Word 檔＋PDF 檔）。

用法：
    python tools/to_pdf.py 成品/考卷/xxx.docx            一個檔
    python tools/to_pdf.py 成品/考卷/a.docx 成品/考卷/b.docx
    python tools/to_pdf.py 成品/考卷                     整個資料夾裡的 .docx

PDF 存在 Word 檔旁邊、同檔名。用這台電腦的 Microsoft Word 轉（排出來和在 Word 裡看到的一樣）；
沒有 Word 時改用 LibreOffice（有裝才行）。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

OFFICE = Path(__file__).resolve().parent.parent
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def word_batch(paths, pdf=True, timeout=240):
    """用 Word 打開每個檔：回傳 {正規化路徑: 頁數}；pdf=True 時順便存一份 PDF 在旁邊。
    Word 叫不動就回傳空的 dict。"""
    if os.name != 'nt' or not paths:
        return {}
    items = []
    for p in paths:
        p = str(Path(p).resolve())
        items.append("'" + p.replace("'", "''") + "'")
    script = (
        "$ErrorActionPreference='Stop';"
        "$w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0;"
        f"foreach($p in @({','.join(items)})){{"
        "try{$d=$w.Documents.Open($p,$false,$true);"
        "$n=$d.ComputeStatistics(2);"
        + ("$o=[IO.Path]::ChangeExtension($p,'.pdf');$d.ExportAsFixedFormat($o,17);" if pdf else "")
        + "Write-Output ($p+'|'+$n);$d.Close($false)}catch{Write-Output ($p+'|ERR '+$_.Exception.Message)}};"
        "$w.Quit()"
    )
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                           capture_output=True, timeout=timeout, encoding='utf-8', errors='replace',
                           creationflags=NO_WINDOW)
    except Exception:
        return {}
    out = {}
    for line in (r.stdout or '').splitlines():
        if '|' in line:
            p, n = line.rsplit('|', 1)
            n = n.strip()
            out[os.path.normcase(os.path.abspath(p.strip()))] = int(n) if n.isdigit() else n
    return out


def libreoffice_pdf(paths):
    exe = shutil.which('soffice') or shutil.which('soffice.exe')
    if not exe and os.name == 'nt':
        for c in (r'C:\Program Files\LibreOffice\program\soffice.exe', r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'):
            if os.path.exists(c):
                exe = c
    if not exe:
        return False
    ok = True
    for p in paths:
        p = Path(p).resolve()
        r = subprocess.run([exe, '--headless', '--convert-to', 'pdf', '--outdir', str(p.parent), str(p)],
                           capture_output=True, timeout=180, creationflags=NO_WINDOW)
        ok = ok and r.returncode == 0 and p.with_suffix('.pdf').exists()
    return ok


def to_pdf(paths):
    """回傳 (成功的 PDF 路徑清單, 錯誤訊息清單)"""
    paths = [Path(p) for p in paths]
    done, errs = [], []
    res = word_batch(paths, pdf=True)
    if res:
        for p in paths:
            v = res.get(os.path.normcase(os.path.abspath(p.resolve())))
            if isinstance(v, int) and p.with_suffix('.pdf').exists():
                done.append(p.with_suffix('.pdf'))
            else:
                errs.append(f'{p.name}：Word 轉不出來' + (f'（{v}）' if v else '（檔案可能正在 Word 裡開著，先關掉再試）'))
        return done, errs
    if libreoffice_pdf(paths):
        return [p.with_suffix('.pdf') for p in paths], []
    return [], ['這台電腦叫不動 Word，也沒有 LibreOffice，沒辦法轉 PDF。請用 Word 打開檔案，按「檔案 → 另存新檔 → PDF」。']


def main(argv):
    if not argv:
        print(__doc__); return 1
    files = []
    for a in argv:
        p = Path(a)
        if not p.is_absolute():
            p = OFFICE / p
        if p.is_dir():
            files += sorted(x for x in p.glob('*.docx') if not x.name.startswith('~$'))
        elif p.suffix.lower() == '.docx' and p.exists():
            files.append(p)
        else:
            print(f'找不到 Word 檔：{a}')
    if not files:
        return 1
    done, errs = to_pdf(files)
    for p in done:
        try:
            print('PDF：' + p.relative_to(OFFICE).as_posix())
        except ValueError:
            print('PDF：' + str(p))
    for e in errs:
        print('注意：' + e)
    return 0 if done and not errs else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
