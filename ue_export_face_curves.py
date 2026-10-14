"""MetaHuman Performance から顔の AnimSequence を書き出し、全カーブを JSON に保存する。
UnrealEditor-Cmd で実行する（-ExecutePythonScript）。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, os
import unreal

# 環境変数で差し替え可（無ければ既定＝先生のテイク4）
PERF = os.environ.get('FD_PERF', _CFG.get('performance', ''))
SKEL = _CFG.get('mh_face_skeleton', '/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton')
OUT_PKG = '/Game/FaceDrive'
OUT_NAME = os.environ.get('FD_MH_ANIM_NAME', 'AS_mh_face')
OUT_JSON = os.environ.get('FD_MH_JSON', _os.path.join(_HERE, 'mh_curves.json'))

perf = unreal.load_asset(PERF)
skel = unreal.load_asset(SKEL)
print('perf:', perf, ' skel:', skel)

U = unreal.MetaHumanPerformanceExportUtils
s = U.get_export_animation_sequence_settings(perf)
s.show_export_dialog = False
s.auto_save_anim_sequence = True
s.export_face = True
s.enable_head_movement = True
s.target_skeleton_or_skeletal_mesh = skel
s.asset_name = OUT_NAME
s.package_path = OUT_PKG
if unreal.EditorAssetLibrary.does_asset_exist(OUT_PKG + '/' + OUT_NAME):
    anim = unreal.load_asset(OUT_PKG + '/' + OUT_NAME)   # 既に書き出し済み
else:
    anim = U.export_animation_sequence(perf, s)
print('anim:', anim)

if anim:
    print('AnimationLibrary curve fns:', [n for n in dir(unreal.AnimationLibrary) if 'curve' in n.lower() and 'key' in n.lower() or n == 'get_animation_curve_names'])
    print('track enums:', [n for n in dir(unreal) if 'RawCurveTrack' in n])
    ftype = unreal.RawCurveTrackTypes.RCT_FLOAT
    names = unreal.AnimationLibrary.get_animation_curve_names(anim, ftype)
    curves = {}
    for n in names:
        t, v = unreal.AnimationLibrary.get_float_keys(anim, n)
        curves[str(n)] = {'t': list(t), 'v': list(v)}
    data = {
        'source': PERF,
        'length': anim.get_play_length(),
        'frames': unreal.AnimationLibrary.get_num_frames(anim),
        'curves': curves,
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    print('curves:', len(curves), ' length:', data['length'], ' frames:', data['frames'])
else:
    print('EXPORT FAILED')
