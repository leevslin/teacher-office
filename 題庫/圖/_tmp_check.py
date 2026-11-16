# -*- coding: utf-8 -*-
from fractions import Fraction as F
from decimal import Decimal as D
import datetime

def mixed(fr):
    q, r = divmod(fr.numerator, fr.denominator)
    return '%d又%d/%d' % (q, r, fr.denominator)

print('--是非')
print('1', F(9, 9) >= 1, '9/9 是假分數 → ×')
print('2', 135 * 47, (135 * 47) % 2 == 1, '○')
print('3', 60 - 24 // 6, 24 % 6, (60 - 24) // 6, '先算除 → ×')
print('4 5.92 百分位', str(D('5.92'))[-1], '○')
print('5 1km=cm', 1000 * 100, '○')
print('--選擇')
print('1 4=?/7', 4 * 7)
print('2 17片 6片一個', divmod(17, 6), mixed(F(17, 6)))
d3, d24 = datetime.date(2026, 12, 3), datetime.date(2026, 12, 24)
print('3', d3.isoweekday(), d24.isoweekday(), (24 - 3) % 7)
print('4', 246 + 138, 357 + 481, 124 * 35, 573 - 218, [x % 2 for x in (246 + 138, 357 + 481, 124 * 35, 573 - 218)])
print('5', 96 // 3 + 28, 96 % 3, '其他:', (96 + 28) / 3, 96 + 28 / 3, 96 * 3 + 28)
print('6', 72 // (4 * 2), 72 // 4 * 2, 72 // 4 // 2, 72 * 4 // 2, 72 // 4 + 2)
print('7', D('4.3') - D('0.6'), D('4.3') + D('0.6'), D('4.3') - D('0.06'))
print('8', sorted([D('1.7'), D('1.68'), D('1.07'), D('1.69')]))
print('9', 200 * 5)
t = 2650 + 1480
print('10', t, divmod(t, 1000))
print('--直式')
print(D('3.47') + D('5.86'), D('12') - D('4.65'))
print('--算算看')
print(500 - 36 * 12, 36 * 12, 384 // (20 - 8), 384 % 12)
print('--填')
print('1', F(3) + F(4, 9), divmod(38, 7))
print('2', F(19, 6))
print('3', divmod(29, 8))
print('4', F(7, 6), mixed(F(11, 6)), F(17, 6))
print('5', [4 + 7 * i for i in range(6)], [95 - 9 * i for i in range(5)])
print('6 百數表 46 下面', 46 + 10)
print('7', D('0.01') * 205, D(107) / 100)
print('8', 6 * 1000 + 45, divmod(7080, 1000))
print('--應用')
print('1', 35 * (18 + 12))
print('2', (500 - 148) // 8, (500 - 148) % 8)
print('3', 5200 // 4, 5200 % 4, divmod(5200 // 4, 1000))
print('4', D('3.2') + D('0.65'))
print('--素養')
print('櫃 第4列第9行', 4 * 9, ' 46號', divmod(46, 4), '→第%d行第%d列' % (46 // 4 + 1, 46 % 4))
# 用排列規則直接驗
def pos(n, rows=4):
    return ((n - 1) // rows + 1, (n - 1) % rows + 1)
print(pos(36), pos(46))
a = 1280 + 865; b = 940 + 1370
print('地圖', a, divmod(a, 1000), b, divmod(b, 1000), b - a)
