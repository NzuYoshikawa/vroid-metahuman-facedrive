"""取り込んだ VRoid モデルが、このパイプラインで扱える形かを調べる（事前チェック）。
表示する内容: 高さ、骨の名前の対応、表情（モーフ）の過不足、揺れ物の構成、検証済みの範囲から外れる点。
結果は model_report.json にも書く。UE 内 Python（エディタのメニューからも、コマンドラインからも実行できる）。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
for _k, _v in (_CFG.get('env') or {}).items():
    _os.environ.setdefault(str(_k), str(_v))

def _fd_finish():
    if _os.environ.get('FD_NO_QUIT'):       # ue_run_all.py から呼ばれたときは終了しない
        return
    try:
        import unreal as _u
        _cl = str(_u.SystemLibrary.get_command_line()).lower()
        if '-run=pythonscript' in _cl or '-executepythonscript' in _cl:
            _u.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
    except BaseException:
        pass

import json, os, sys
import unreal
sys.path.insert(0, _HERE)
import fd_common as _fc

mesh_path = _CFG['vroid_dir'] + _CFG['mesh']
meta_path = _CFG['vroid_dir'] + _CFG['meta']
mesh = unreal.load_asset(mesh_path)
report = {'mesh': mesh_path, 'warnings': []}
warn = report['warnings'].append

# 1) 高さ（頭の骨の高さ。基準姿勢）
b_head = _fc.bones(meta_path)['head']
h = _fc.model_height_cm(mesh, _CFG['vroid_dir'] + _CFG['face_pose_anim'], b_head)
report['head_height_cm'] = round(h, 1)
report['scale_vs_reference'] = round(h / _fc.REF_HEIGHT_CM, 3)
if not 0.85 <= h / _fc.REF_HEIGHT_CM <= 1.15:
    warn('頭の骨の高さが、検証したモデル（%.0f cm）の ±15%% を外れています。手を避ける半径は比例して直しますが、結果を目で確認してください' % _fc.REF_HEIGHT_CM)

# 2) 骨の名前
table = _fc.humanoid_table(meta_path)
report['humanoid_bones'] = len(table)
b = _fc.bones(meta_path)
skel_bones = None
try:   # 骨の一覧は、顔のポーズのアニメ（同じスケルトン）の基準姿勢から取る
    _fa = unreal.load_asset(_CFG['vroid_dir'] + _CFG['face_pose_anim'])
    _o = unreal.AnimPoseEvaluationOptions()
    _o.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    _p = unreal.AnimPoseExtensions.get_anim_pose_at_time(_fa, 0.0, _o)
    skel_bones = set(str(x) for x in unreal.AnimPoseExtensions.get_bone_names(_p))
except BaseException as _e:
    print('FD bone list unavailable', type(_e).__name__)
missing = [k for k, v in b.items() if skel_bones is not None and v not in skel_bones]
report['bones_missing_in_skeleton'] = missing
if not table:
    warn('VRM の人型ボーン対応表が読めません。VRoid Studio の骨の名前を仮定します')
if missing:
    warn('スケルトンに存在しない骨: ' + ', '.join('%s(%s)' % (k, b[k]) for k in missing))

# 3) 表情（モーフ）
try:
    morphs = [str(m.get_name()) for m in mesh.get_editor_property('morph_targets')]
except BaseException:
    morphs = []
report['morph_count'] = len(morphs)
targets = []
mp = os.path.join(_HERE, 'mapping_v2.json')
if os.path.exists(mp):
    m = json.load(open(mp, encoding='utf-8'))
    t = m.get('targets') or {}
    targets = list(t.keys()) if isinstance(t, dict) else [str(x) for x in t]
    _vs = m.get('visemes')
    if isinstance(_vs, dict):
        targets += [str(k) for k in (_vs.get('scores') or {}).keys()]
if morphs and targets:
    miss = [t for t in targets if t not in morphs]
    report['mapping_targets'] = len(targets)
    report['mapping_targets_missing'] = miss
    if miss:
        warn('対応表の変換先の表情がモデルに無い: ' + ', '.join(miss[:12]))
elif not morphs:
    warn('表情（モーフ）が0個です。取り込み時の保存が不完全だった可能性があります。取り込み先のフォルダを削除して、ue_import_vrm.py をやり直してください')

# 4) 揺れ物
groups = {'hair': 0, 'skirt': 0, 'other': 0}
chain_len = []
try:
    meta = unreal.load_asset(meta_path)
    sb = meta.get_editor_property('vrm1_spring_bone_meta')
    springs = list(sb.get_editor_property('springs'))
    colliders = list(sb.get_editor_property('colliders'))
    for sp in springs:
        joints = list(sp.get_editor_property('joints'))
        chain_len.append(len(joints))
        nm = ' '.join(str(j.get_editor_property('bone_name')) for j in joints)
        if 'Hair' in nm:
            groups['hair'] += 1
        elif any(k in nm for k in ('Skirt', 'Coat', 'Cloth')):
            groups['skirt'] += 1
        else:
            groups['other'] += 1
    report['springs'] = {'count': len(springs), 'joints': sum(chain_len), 'colliders': len(colliders),
                         'max_chain': max(chain_len) if chain_len else 0, 'groups': groups}
    if springs and groups['hair'] + groups['skirt'] == 0:
        warn('揺れ物の名前に Hair／Skirt／Coat／Cloth を含むものがありません。すべて「その他」として扱われます。spring_params.json の groups の match を直してください')
except BaseException as e:
    report['springs'] = 'ERR ' + type(e).__name__
    warn('揺れ物の情報を取得できませんでした')

print('FD CHECK', json.dumps({k: v for k, v in report.items() if k != 'warnings'}, ensure_ascii=False))
for w in report['warnings']:
    print('FD WARN', w)
if not report['warnings']:
    print('FD OK: 検証済みの範囲内です')
with open(os.path.join(_HERE, 'model_report.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
_fd_finish()
