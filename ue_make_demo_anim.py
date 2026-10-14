"""Mixamo 由来の体アニメ（接地補正済み）に、別テイクの顔の表情カーブを足したデモ用アニメを作る。
環境変数: FD_BODY（体アニメのパス）, FD_DEMO（出力パス）, FD_T0（顔カーブの開始秒）"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, os
import unreal
BODY = os.environ.get('FD_BODY', '/Game/FaceDrive/Mixamo/VRM_Talking2_2_Fixed')
DEMO = os.environ.get('FD_DEMO', '/Game/FaceDrive/AS_Mixamo_Talking_Face')
T0 = float(os.environ.get('FD_T0', '8.0'))
MORPHS = _os.path.join(_HERE, 'vrm_curves.json')
if unreal.EditorAssetLibrary.does_asset_exist(DEMO):
    unreal.EditorAssetLibrary.delete_asset(DEMO)
demo = unreal.EditorAssetLibrary.duplicate_asset(BODY, DEMO)
length = float(unreal.AnimationLibrary.get_sequence_length(demo))
d = json.load(open(MORPHS))
fps = d['fps']
i0 = int(T0 * fps)
n = int(length * fps)
times = [k / fps for k in range(n)]
for name, vals in d['morphs'].items():
    seg = [float(v) for v in vals[i0:i0 + n]]
    unreal.AnimationLibrary.add_curve(demo, name, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    unreal.AnimationLibrary.add_float_curve_keys(demo, name, times, seg)
unreal.EditorAssetLibrary.save_asset(DEMO)
print('MIXDEMO', DEMO, 'length %.2f' % length, 'curves', len(d['morphs']))
unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
