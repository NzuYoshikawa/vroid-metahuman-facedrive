"""MetaHumanのカーブJSONに対応表を適用し、VRMモーフのカーブJSONを作る（UEなしで検証できる）。
使い方: python -I apply_mapping.py mh_curves.json mapping_v1.json out_morphs.json [fps]
"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, re, sys
try:
    if _os.environ.get('FD_NO_NUMPY'):
        raise ImportError
    import numpy as np
except ImportError:      # UE のエディタ内の Python など、numpy が無い環境
    import sys as _sys
    _sys.path.insert(0, _HERE)
    import fd_mini_np as np

# 引数なし（エディタのメニューから実行）なら、このフォルダの既定のファイルを使う
_a = sys.argv[1:] if len(sys.argv) > 1 else []
def _p(x):
    return x if _os.path.isabs(x) else _os.path.join(_HERE, x)
src = _p(_a[0] if len(_a) > 0 else 'mh_curves.json')
mp_path = _p(_a[1] if len(_a) > 1 else 'mapping_v2.json')
out_path = _p(_a[2] if len(_a) > 2 else 'vrm_curves.json')
fps = float(_a[3]) if len(_a) > 3 else 30.0
d = json.load(open(src))
mp = json.load(open(mp_path, encoding='utf-8'))
n = int(round(d['length'] * fps)) + 1
t = np.arange(n) / fps

def sample(c):
    if not c['t']:
        return np.zeros(n)   # 変化なしのカーブはキーが消えている
    return np.interp(t, c['t'], c['v'])

curves = {}
for k, c in d['curves'].items():
    curves[k.replace('CTRL_expressions_', '')] = sample(c)
missing = set()
# 自動正規化：待機時の下駄（例：まばたきの基準値）を引き、そのテイクの振れ幅を0..1に広げる
for name in mp.get('auto_norm', []):
    if name in curves:
        lo, hi = np.percentile(curves[name], 20), np.percentile(curves[name], 99.5)
        curves[name] = np.clip((curves[name] - lo) / max(hi - lo, 1e-6), 0, 1)
        print('auto_norm %-14s lo=%.2f hi=%.2f' % (name, lo, hi))

def get(name):
    if name not in curves:
        missing.add(name)
        return np.zeros(n)
    return curves[name]

def ev(expr):
    m = re.fullmatch(r'avg\((.+)\)', expr)
    names = m.group(1).split(',') if m else [expr]
    return np.mean([get(x) for x in names], axis=0)

out = {}
for tgt, spec in mp['targets'].items():
    v = np.zeros(n)
    for expr, w in spec['terms']:
        v += w * ev(expr)
    v = np.clip(v, 0, 1)
    for expr, mode, w in spec.get('gate', []):
        g = ev(expr)
        g = (1 - g) if mode == 'inv' else g
        v = v * np.clip((1 - w) + w * g, 0, 1)   # w=0なら素通し、w=1なら完全に掛ける
    out[tgt] = v

# 母音：開口量(aperture)を、5母音への配分(p_k ∝ score_k^power)で分ける。5つが同時に半端にかかるのを防ぐ
vz = mp.get('visemes')
if vz:
    amp = np.zeros(n)
    for expr, w in vz['aperture']:
        amp += w * ev(expr)
    amp = np.clip(amp, 0, 1)
    sc = {}
    for tgt, terms in vz['scores'].items():
        s = np.zeros(n)
        for expr, w in terms:
            s += w * ev(expr)
        sc[tgt] = np.clip(s, 0, None) ** vz.get('power', 2.0) + vz.get('floor', 1e-4)
    tot = sum(sc.values())
    for tgt, s in sc.items():
        out[tgt] = np.clip(amp * s / tot, 0, 1)

# 個別の微調整（face_tuning.json）: 全体利得・表情ごとの利得/オフセット/上下限・時間の平滑化
import os
tuning_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'face_tuning.json')
if len(sys.argv) > 5:
    tuning_path = sys.argv[5]
if os.path.exists(tuning_path):
    tu = json.load(open(tuning_path, encoding='utf-8'))
    g_all = float(tu.get('expression_gain', 1.0))
    per = tu.get('morphs', {})
    sm = int(tu.get('smooth_frames', 1))
    for k in list(out):
        p = per.get(k, {})
        v = out[k] * g_all * float(p.get('gain', 1.0)) + float(p.get('offset', 0.0))
        if sm > 1:
            kern = np.ones(sm) / sm
            v = np.convolve(np.pad(v, (sm // 2, sm - 1 - sm // 2), mode='edge'), kern, mode='valid')
        out[k] = np.clip(v, float(p.get('min', 0.0)), float(p.get('max', 1.0)))
    print('tuning applied from', tuning_path)

json.dump({'fps': fps, 'frames': n, 'morphs': {k: [round(float(x), 4) for x in v] for k, v in out.items()}},
          open(out_path, 'w'))
print('frames', n, 'fps', fps, 'missing MH curves:', sorted(missing) or 'none')
for k, v in out.items():
    print(f'{k:20s} max={v.max():.2f} mean={v.mean():.2f}')
