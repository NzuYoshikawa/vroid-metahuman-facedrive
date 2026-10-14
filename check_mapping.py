"""mapping_*.json の名前が、実在する MetaHuman コントロールと VRM モーフかを検査する。
使い方: python -I check_mapping.py mapping_v1.json
"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, os, re, sys, fnmatch

here = os.path.dirname(os.path.abspath(__file__))
mp = json.load(open(sys.argv[1], encoding='utf-8'))
mh = set(json.load(open(os.path.join(here, 'mh_controls.json'), encoding='utf-8'))['controls'])
vm = json.load(open(os.path.join(here, 'vrm_morphs.json'), encoding='utf-8'))['morphs']

def curves(expr):
    m = re.fullmatch(r'avg\((.+)\)', expr)
    return m.group(1).split(',') if m else [expr]

bad = []
for tgt, d in mp['targets'].items():
    if tgt not in vm:
        bad.append(f'VRMに無いモーフ: {tgt}')
    for key in ('terms', 'gate'):
        for item in d.get(key, []):
            for c in curves(item[0]):
                if 'CTRL_expressions_' + c not in mh:
                    bad.append(f'MetaHumanに無いコントロール: {c} (in {tgt})')

vz = mp.get('visemes')
if vz:
    for tgt, terms in list(vz['scores'].items()) + [('aperture', vz['aperture'])]:
        if tgt != 'aperture' and tgt not in vm:
            bad.append(f'VRMに無いモーフ: {tgt}')
        for item in terms:
            for c in curves(item[0]):
                if 'CTRL_expressions_' + c not in mh:
                    bad.append(f'MetaHumanに無いコントロール: {c} (in {tgt})')
used = set(mp['targets']) | (set(vz['scores']) if vz else set())
skipped = set()
for pat in mp['deliberately_unmapped']:
    skipped |= {m for m in vm if fnmatch.fnmatch(m, pat)}
rest = [m for m in vm if m not in used and m not in skipped]

print(f'対象 {len(used)} / VRMモーフ {len(vm)} / 意図的に未対応 {len(skipped)}')
print('どこにも入っていないVRMモーフ:', rest or 'なし')
print('エラー:', len(bad))
for b in bad:
    print('  ', b)
sys.exit(1 if bad else 0)
