"""numpy の代わり（標準ライブラリのみ）。apply_mapping.py が使う最小限の関数だけを実装している。
UE のエディタ内の Python には numpy が無いため、エディタの中でも変換を実行できるようにする。"""
import bisect, math


class Arr(list):
    def _b(self, o, f):
        if isinstance(o, (list, tuple)):
            return Arr(f(a, b) for a, b in zip(self, o))
        return Arr(f(a, o) for a in self)

    def __add__(s, o): return s._b(o, lambda a, b: a + b)
    __radd__ = __add__
    def __sub__(s, o): return s._b(o, lambda a, b: a - b)
    def __rsub__(s, o): return Arr((o - a) if not isinstance(o, (list, tuple)) else 0 for a in s) if not isinstance(o, (list, tuple)) else Arr(b - a for a, b in zip(s, o))
    def __mul__(s, o): return s._b(o, lambda a, b: a * b)
    __rmul__ = __mul__
    def __truediv__(s, o): return s._b(o, lambda a, b: a / b)
    def __rtruediv__(s, o): return Arr(o / a for a in s) if not isinstance(o, (list, tuple)) else Arr(b / a for a, b in zip(s, o))
    def __pow__(s, p): return Arr(a ** p for a in s)
    def __neg__(s): return Arr(-a for a in s)
    # list の += は連結になるため、要素ごとの演算に置き換える
    def __iadd__(s, o): return s.__add__(o)
    def __isub__(s, o): return s.__sub__(o)
    def __imul__(s, o): return s.__mul__(o)
    def __itruediv__(s, o): return s.__truediv__(o)
    def copy(s): return Arr(s)
    @property
    def size(s): return len(s)
    def max(s): return max(s)
    def min(s): return min(s)
    def mean(s): return sum(s) / len(s)
    def tolist(s): return [float(x) for x in s]


def arange(n): return Arr(float(i) for i in range(n))
def zeros(n): return Arr(0.0 for _ in range(n))
def ones(n): return Arr(1.0 for _ in range(n))
def array(x): return Arr(float(v) for v in x)


def interp(x, xp, fp):
    out = Arr()
    n = len(xp)
    for v in x:
        if v <= xp[0]:
            out.append(float(fp[0])); continue
        if v >= xp[-1]:
            out.append(float(fp[-1])); continue
        i = bisect.bisect_right(xp, v) - 1
        a = (v - xp[i]) / (xp[i + 1] - xp[i])
        out.append(fp[i] * (1 - a) + fp[i + 1] * a)
    return out


def percentile(a, q):
    s = sorted(a)
    n = len(s)
    if n == 1:
        return float(s[0])
    pos = (n - 1) * q / 100.0
    lo = int(math.floor(pos)); hi = min(lo + 1, n - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def clip(a, lo, hi):
    f = lambda v: (lo if (lo is not None and v < lo) else (hi if (hi is not None and v > hi) else v))
    if isinstance(a, (list, tuple)):
        return Arr(f(v) for v in a)
    return f(a)


def mean(arrs, axis=None):
    if axis == 0:
        return Arr(sum(col) / len(col) for col in zip(*arrs))
    flat = [v for x in arrs for v in (x if isinstance(x, (list, tuple)) else [x])]
    return sum(flat) / len(flat)


def pad(a, widths, mode='edge'):
    l, r = widths
    return Arr([a[0]] * l + list(a) + [a[-1]] * r)


def convolve(a, k, mode='valid'):
    n, m = len(a), len(k)
    kk = list(k)[::-1]
    return Arr(sum(a[i + j] * kk[j] for j in range(m)) for i in range(n - m + 1))
