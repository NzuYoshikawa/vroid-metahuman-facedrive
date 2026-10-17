"""MetaHuman のコントロール名と VRM のモーフ名を書き出す。
使い方: python -I build_lists.py <UEのバージョンフォルダ> <vrm>
例:     python -I build_lists.py "C:\\Program Files\\Epic Games\\UE_5.8" <モデル>.vrm
"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
try:
    _CFG = _json.load(open(_CFG_PATH, encoding='utf-8-sig')) if _os.path.exists(_CFG_PATH) else {}
except ValueError as _e:
    raise SystemExit('config.json の書き方が正しくありません: %s （パスの区切りは / にするか、\\\\ と2つ重ねます）' % _e)
import json, re, struct, sys, os

ue, vrm = sys.argv[1], sys.argv[2]
out = os.path.dirname(os.path.abspath(__file__))
mh = os.path.join(ue, 'Engine', 'Plugins', 'MetaHuman')

names = []
# 発話由来（口・顎・舌・歯・首・鼻・頭）
p = os.path.join(mh, 'MetaHumanAnimator', 'Source', 'MetaHumanSpeech2Face', 'Private', 'DataDefs.h')
for m in re.finditer(r'TEXT\("(CTRL_expressions_\w+)"\)', open(p, encoding='utf-8', errors='replace').read()):
    names.append(m.group(1))
# 目・眉を含む全体
p = os.path.join(mh, 'MetaHumanCoreTechLib', 'Source', 'MetaHumanCoreTech', 'Private', 'GuiToRawControlsUtils.cpp')
for m in re.finditer(r'CTRL_expressions_\w+', open(p, encoding='utf-8', errors='replace').read()):
    names.append(m.group(0))
names = sorted(set(names))
json.dump({'engine': ue, 'count': len(names), 'controls': names},
          open(os.path.join(out, 'mh_controls.json'), 'w', encoding='utf-8'), indent=1)

with open(vrm, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<I4s', f.read(8))
    j = json.loads(f.read(clen).decode('utf-8'))
morphs = []
for m in j['meshes']:
    t = (m.get('extras') or {}).get('targetNames')
    if t:
        morphs = t
        break
json.dump({'vrm': vrm, 'count': len(morphs), 'morphs': morphs},
          open(os.path.join(out, 'vrm_morphs.json'), 'w', encoding='utf-8'), indent=1)
print('MH controls:', len(names), ' VRM morphs:', len(morphs))
