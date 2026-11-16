# -*- coding: utf-8 -*-
"""四上數學期末考（第6-10單元）的圖。執行：python 題庫/圖/數學四上期末_畫圖.py
黑白、省墨。要改數字就改這裡再重畫。"""
import os
from fractions import Fraction as F
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrow

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False
OUT = os.path.dirname(os.path.abspath(__file__))
PRE = '數學四上期末_'
NL = chr(10)


# 注意：排版工具會把每張圖縮成約 9.8 公分寬（B4 雙欄的一欄），
# 老師規定印出來最小 14 pt。字級要用「印出來 14 pt 以上」來估：印出字級 ≈ 程式字級 × 3.9 ÷ 圖寬（英吋）。
def save(fig, name, tight=True):
    fig.savefig(os.path.join(OUT, PRE + name + '.png'), dpi=220, bbox_inches='tight' if tight else None,
                pad_inches=0.08, facecolor='white')
    plt.close(fig)


def axis_off(ax):
    ax.set_axis_off()


# ---------- 1. 分數數線：0～3，每 1 格是 1/6 ----------
def fig_fraction_line():
    fig, ax = plt.subplots(figsize=(6.0, 2.0))
    ax.plot([-0.08, 3.12], [0, 0], color='k', lw=1.6)
    ax.annotate('', xy=(3.2, 0), xytext=(3.1, 0), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.6))
    for i in range(0, 19):
        x = i / 6
        big = (i % 6 == 0)
        ax.plot([x, x], [0, 0.22 if big else 0.12], color='k', lw=1.6 if big else 1.0)
        if big:
            ax.text(x, -0.14, str(i // 6), ha='center', va='top', fontsize=24)
    for name, v in (('甲', F(7, 6)), ('乙', F(11, 6)), ('丙', F(17, 6))):
        x = float(v)
        ax.annotate('', xy=(x, 0.25), xytext=(x, 0.62), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.4))
        ax.text(x, 0.66, name, ha='center', va='bottom', fontsize=24)
    ax.set_xlim(-0.15, 3.3); ax.set_ylim(-0.5, 1.05)
    axis_off(ax)
    save(fig, '分數數線')


# ---------- 2. 小數數線：3～5，每 1 小格 0.1，箭頭在 4.3 ----------
def fig_decimal_line():
    fig, ax = plt.subplots(figsize=(6.0, 2.0))
    ax.plot([2.93, 5.1], [0, 0], color='k', lw=1.6)
    ax.annotate('', xy=(5.17, 0), xytext=(5.08, 0), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.6))
    for i in range(30, 51):
        x = i / 10
        big = (i % 10 == 0)
        mid = (i % 5 == 0)
        ax.plot([x, x], [0, 0.07 if big else (0.05 if mid else 0.04)], color='k', lw=1.6 if big else 1.0)
        if big:
            ax.text(x, -0.045, str(i // 10), ha='center', va='top', fontsize=24)
    ax.annotate('', xy=(4.3, 0.08), xytext=(4.3, 0.2), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.4))
    ax.text(4.3, 0.215, '柯南', ha='center', va='bottom', fontsize=24)
    ax.set_xlim(2.88, 5.22); ax.set_ylim(-0.16, 0.33)
    axis_off(ax)
    save(fig, '小數數線')


# ---------- 3. 百數表的一小塊 ----------
def fig_hundred_piece():
    # 寬版畫布、不裁白邊：插進 Word 後約 9.8×4.3 公分，不會佔掉半欄
    fig = plt.figure(figsize=(6.0, 2.6))
    ax = fig.add_axes([0, 0, 1, 1])
    cells = {(1, 2): '36', (0, 1): '45', (1, 1): '46', (2, 1): '47', (1, 0): '甲'}
    for (cx, cy), t in cells.items():
        ax.add_patch(Rectangle((cx, cy), 1, 1, fill=False, ec='k', lw=1.6))
        ax.text(cx + 0.5, cy + 0.5, t, ha='center', va='center', fontsize=24)
    half = 3.1 * 6.0 / 2.6 / 2
    ax.set_xlim(1.5 - half, 1.5 + half); ax.set_ylim(-0.05, 3.05); ax.set_aspect('equal')
    axis_off(ax)
    save(fig, '百數表', tight=False)


# ---------- 4. 圖形規律（兩排） ----------
def draw_arrow(ax, cx, cy, d):
    dx, dy = {'U': (0, 1), 'R': (1, 0), 'D': (0, -1), 'L': (-1, 0)}[d]
    L = 0.5
    ax.add_patch(FancyArrow(cx - dx * L / 2, cy - dy * L / 2, dx * L, dy * L, width=0.09, head_width=0.3,
                            head_length=0.2, length_includes_head=True, fc='k', ec='k'))


def draw_shape(ax, cx, cy, s):
    if s == 'O':
        ax.add_patch(Circle((cx, cy), 0.27, fill=False, ec='k', lw=1.8))
    elif s == 'T':
        ax.add_patch(Polygon([(cx - 0.3, cy - 0.25), (cx + 0.3, cy - 0.25), (cx, cy + 0.29)], fill=False, ec='k',
                             lw=1.8))
    elif s == 'S':
        ax.add_patch(Rectangle((cx - 0.26, cy - 0.26), 0.52, 0.52, fill=False, ec='k', lw=1.8))


def fig_pattern():
    # 每排 8 格：插進 Word 後每格約 1.1 公分，學生才有地方畫
    row1 = ['U', 'R', 'D', 'L', 'U', 'R', 'D', '?']   # 答：L（向左）
    row2 = ['O', 'T', 'T', 'S', 'O', 'T', '?', 'S']   # 答：T（三角形）
    fig, ax = plt.subplots(figsize=(8.8, 3.0))
    for r, (row, y, tag) in enumerate(((row1, 1.6, '⑴'), (row2, 0, '⑵'))):
        ax.text(-0.35, y + 0.5, tag, ha='center', va='center', fontsize=34)
        for i, s in enumerate(row):
            ax.add_patch(Rectangle((i, y), 1, 1, fill=False, ec='k', lw=1.4 if s != '?' else 2.4))
            if s == '?':
                continue
            if r == 0:
                draw_arrow(ax, i + 0.5, y + 0.5, s)
            else:
                draw_shape(ax, i + 0.5, y + 0.5, s)
    ax.set_xlim(-0.7, 8.1); ax.set_ylim(-0.1, 2.7); ax.set_aspect('equal')
    axis_off(ax)
    save(fig, '圖形規律')


# ---------- 5. 寄物櫃：4 列，號碼由上到下、再往右一行 ----------
def fig_lockers():
    # 畫成印出來的實際大小（約 3.9 吋寬），字級就是印出來的字級
    rows, shown, cols = 4, 5, 6
    fig, ax = plt.subplots(figsize=(3.9, 2.9))
    for c in range(cols):
        ax.text(c + 0.5, rows + 0.08, NL.join('第%d行' % (c + 1)), ha='center', va='bottom', fontsize=15,
                linespacing=1.0)
        for r in range(rows):
            y = rows - 1 - r
            ax.add_patch(Rectangle((c, y), 1, 1, fill=False, ec='k', lw=1.2))
            if c < shown:
                ax.text(c + 0.5, y + 0.5, str(c * rows + r + 1), ha='center', va='center', fontsize=16)
    for r in range(rows):
        ax.text(-0.1, rows - 1 - r + 0.5, '第%d列' % (r + 1), ha='right', va='center', fontsize=15)
    ax.text(cols + 0.5, rows / 2, '…', ha='center', va='center', fontsize=16)
    ax.set_xlim(-1.5, cols + 0.9); ax.set_ylim(-0.1, rows + 1.75); ax.set_aspect('equal')
    axis_off(ax)
    save(fig, '寄物櫃')


# ---------- 6. 米花町地圖 ----------
def fig_map():
    # 座標單位＝英吋，畫成印出來的大小（約 4 吋寬），字級 15.5 印出來約 14.5 pt。路程標在線的正中間（白底蓋住線）。
    P = {'毛利偵探|事務所': (0.4, 2.5), '帝丹|小學': (0.4, 1.1), '米花|公園': (2.45, 2.5),
         '阿笠|博士家': (2.0, 0.3), '米花|美術館': (3.5, 1.3)}
    E = [('帝丹|小學', '米花|公園', '1 km 280 m'),
         ('米花|公園', '米花|美術館', '865 m'),
         ('帝丹|小學', '阿笠|博士家', '940 m'),
         ('阿笠|博士家', '米花|美術館', '1 km 370 m'),
         ('毛利偵探|事務所', '帝丹|小學', '650 m'),
         ('毛利偵探|事務所', '米花|公園', '1 km 90 m')]
    fig = plt.figure(figsize=(4.15, 3.05))
    ax = fig.add_axes([0, 0, 1, 1])
    for a, b, t in E:
        (x1, y1), (x2, y2) = P[a], P[b]
        ax.plot([x1, x2], [y1, y2], color='k', lw=1.5, zorder=1)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, t, ha='center', va='center', fontsize=15.5, zorder=3,
                bbox=dict(fc='white', ec='none', pad=1.0))
    for name, (x, y) in P.items():
        ax.text(x, y, name.replace('|', NL), ha='center', va='center', fontsize=15.5, zorder=4, linespacing=1.05,
                bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='k', lw=1.3))
    ax.set_xlim(-0.15, 4.0); ax.set_ylim(-0.1, 2.95); ax.set_aspect('equal')
    axis_off(ax)
    save(fig, '米花町地圖', tight=False)


if __name__ == '__main__':
    fig_fraction_line(); fig_decimal_line(); fig_hundred_piece(); fig_pattern(); fig_lockers(); fig_map()
    print('OK')
