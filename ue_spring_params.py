"""髪・服の揺れを spring_params.json の値で VrmMetaObject に書き込む。
元の値は *_original.json に保存し、常にその元の値に対する倍率で適用する（何度実行しても累積しない）。
環境変数 FD_SWAY（全体 sway の上書き）、FD_GROUPS='hair=2.0,skirt=0.5'（グループ別 sway の上書き）。

spring_params.json の構造:
  sway                : 全体の揺れやすさ（stiffness と drag を 1/sway に）
  groups.<名前>       : match（骨名の部分一致）, sway, stiffness_scale, drag_scale, gravity_scale, hit_radius_scale
  overrides[]         : 個別の揺れ物（骨名の部分一致で、グループの結果にさらに上書き）。
                        { "match": "CoatSkirtBack_01", "sway": 0.2, "hit_radius_scale": 2.0, ... }（項目は省略可）
  colliders[]         : 体のコライダー（球）の半径。{ "match": "UpperLeg", "radius_scale": 1.2 }
  clamp               : stiffness / drag / gravity の範囲
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

# --- 共通: エディタのメニューから実行したときに、エディタを閉じない／config.json の "env" を環境変数の既定値にする ---
for _k, _v in (_CFG.get('env') or {}).items():
    _os.environ.setdefault(str(_k), str(_v))

def _fd_finish():
    """コマンドライン（-run=pythonscript）のときだけエディタを終了する。"""
    if _os.environ.get('FD_NO_QUIT'):       # ue_run_all.py から呼ばれたときは終了しない
        return
    try:
        import unreal as _u
        _cl = str(_u.SystemLibrary.get_command_line()).lower()
        if '-run=pythonscript' in _cl or '-executepythonscript' in _cl:
            _u.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
    except BaseException:
        pass
import json, os
import unreal

ROOT = _HERE
P = json.load(open(os.path.join(ROOT, 'spring_params.json'), encoding='utf-8-sig'))
ORIG = os.path.join(ROOT, 'spring_params_original.json')
ORIG_COL = os.path.join(ROOT, 'spring_collider_original.json')
META = (_CFG['vroid_dir'] + _CFG['meta'])

if os.environ.get('FD_SWAY'):
    P['sway'] = float(os.environ['FD_SWAY'])
if os.environ.get('FD_GROUPS'):
    for kv in os.environ['FD_GROUPS'].split(','):
        k, v = kv.split('=')
        P['groups'][k.strip()]['sway'] = float(v)

meta = unreal.load_asset(META)
sb = meta.get_editor_property('vrm1_spring_bone_meta')
springs = list(sb.get_editor_property('springs'))
colliders = list(sb.get_editor_property('colliders'))

# 元の値を保存（初回のみ）。[stiffness, gravity_power, drag_force, hit_radius]
if not os.path.exists(ORIG):
    orig = []
    for sp in springs:
        orig.append([[float(j.get_editor_property('stiffness')), float(j.get_editor_property('gravity_power')),
                      float(j.get_editor_property('drag_force')), float(j.get_editor_property('hit_radius'))]
                     for j in sp.get_editor_property('joints')])
    json.dump(orig, open(ORIG, 'w'))
    print('original values saved:', ORIG)
orig = json.load(open(ORIG))
# 旧形式（3値）なら、hit_radius は一度も変えていないので現在値を元の値として補う
changed = False
for si, sp in enumerate(springs):
    js = list(sp.get_editor_property('joints'))
    for ji, j in enumerate(js):
        if len(orig[si][ji]) == 3:
            orig[si][ji].append(float(j.get_editor_property('hit_radius')))
            changed = True
if changed:
    json.dump(orig, open(ORIG, 'w'))
    print('original file upgraded with hit_radius')
if not os.path.exists(ORIG_COL):
    json.dump([float(c.get_editor_property('radius')) for c in colliders], open(ORIG_COL, 'w'))
orig_col = json.load(open(ORIG_COL))

def group_of(name):
    low = name.lower()
    for g, d in P['groups'].items():
        for m in d['match']:
            if m != '*' and m.lower() in low:
                return g
    return 'other'

def clamp(x, lohi):
    return max(lohi[0], min(lohi[1], x))

counts, ov_used = {}, {}
for si, sp in enumerate(springs):
    joints = list(sp.get_editor_property('joints'))
    if not joints:
        continue
    bone0 = str(joints[0].get_editor_property('bone_name'))
    g = group_of(bone0)
    d = dict(P['groups'][g])
    d.setdefault('hit_radius_scale', 1.0)
    sway = P['sway'] * d['sway']
    st, dr, gr, hr = d['stiffness_scale'], d['drag_scale'], d['gravity_scale'], d['hit_radius_scale']
    for k, ov in enumerate(P.get('overrides', [])):
        if ov['match'].lower() in bone0.lower():
            sway = P['sway'] * ov.get('sway', d['sway'])
            st, dr = ov.get('stiffness_scale', st), ov.get('drag_scale', dr)
            gr, hr = ov.get('gravity_scale', gr), ov.get('hit_radius_scale', hr)
            ov_used[k] = ov_used.get(k, 0) + 1
    sway = max(1e-3, sway)
    counts[g] = counts.get(g, 0) + 1
    for ji, j in enumerate(joints):
        s0, g0, d0, h0 = orig[si][ji]
        j.set_editor_property('stiffness', clamp(s0 * st / sway, P['clamp']['stiffness']))
        j.set_editor_property('drag_force', clamp(d0 * dr / sway, P['clamp']['drag']))
        j.set_editor_property('gravity_power', clamp(g0 * gr, P['clamp']['gravity']))
        j.set_editor_property('hit_radius', max(0.0, h0 * hr))
        joints[ji] = j
    sp.set_editor_property('joints', joints)
    springs[si] = sp
sb.set_editor_property('springs', springs)

col_used = 0
for ci, c in enumerate(colliders):
    scale = 1.0
    bn = str(c.get_editor_property('bone_name'))
    for cs in P.get('colliders', []):
        if cs['match'].lower() in bn.lower():
            scale = cs.get('radius_scale', 1.0)
    c.set_editor_property('radius', orig_col[ci] * scale)
    colliders[ci] = c
    if scale != 1.0:
        col_used += 1
sb.set_editor_property('colliders', colliders)
meta.set_editor_property('vrm1_spring_bone_meta', sb)
unreal.EditorAssetLibrary.save_loaded_asset(meta)

# 読み戻して確認
chk = unreal.load_asset(META).get_editor_property('vrm1_spring_bone_meta')
vals = {}
for sp in chk.get_editor_property('springs'):
    js = list(sp.get_editor_property('joints'))
    if js:
        g = group_of(str(js[0].get_editor_property('bone_name')))
        vals.setdefault(g, []).append((float(js[0].get_editor_property('stiffness')), float(js[0].get_editor_property('drag_force')),
                                       float(js[0].get_editor_property('hit_radius'))))
for g, v in vals.items():
    print('SPRING group=%s n=%d  stiffness(mean)=%.3f drag(mean)=%.3f hit_radius(mean)=%.4f' %
          (g, len(v), sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v), sum(x[2] for x in v) / len(v)))
print('overrides used:', ov_used, ' colliders scaled:', col_used)
_fd_finish()
