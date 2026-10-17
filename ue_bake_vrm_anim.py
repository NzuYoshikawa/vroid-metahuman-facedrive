"""変換済みカーブ（vrm_curves.json）を、VRoid のスケルトン用 AnimSequence にベイクする。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}

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

D = _CFG['vroid_dir']
OUT_PKG = '/Game/FaceDrive'
OUT_NAME = os.environ.get('FD_ANIM_NAME', 'AS_vrm_face')
SRC = os.environ.get('FD_MORPHS', _os.path.join(_HERE, 'vrm_curves.json'))
MH = os.environ.get('FD_MH_CURVES', _os.path.join(_HERE, 'mh_curves.json'))

skel = unreal.load_asset(D + _CFG['skeleton'])
data = json.load(open(SRC))
fps, nfr = data['fps'], data['frames']
mh = json.load(open(MH))

# 参考: VRM4U が作った ARKit 名アニメの頭カーブの範囲
ref = unreal.load_asset(D + _CFG['face_pose_anim'])
for nm in ('HeadYaw', 'HeadPitch', 'HeadRoll', 'LeftEyeYaw'):
    t, v = unreal.AnimationLibrary.get_float_keys(ref, nm)
    print('REF', nm, 'n=%d' % len(v), 'min=%.3f max=%.3f' % (min(v) if v else 0, max(v) if v else 0))
for nm in ('HeadYaw', 'HeadPitch', 'HeadRoll'):
    v = mh['curves'][nm]['v']
    print('MH ', nm, 'n=%d' % len(v), 'min=%.3f max=%.3f' % (min(v) if v else 0, max(v) if v else 0))

if unreal.EditorAssetLibrary.does_asset_exist(OUT_PKG + '/' + OUT_NAME):
    unreal.EditorAssetLibrary.delete_asset(OUT_PKG + '/' + OUT_NAME)
fac = unreal.AnimSequenceFactory()
fac.set_editor_property('target_skeleton', skel)
anim = unreal.AssetToolsHelpers.get_asset_tools().create_asset(OUT_NAME, OUT_PKG, unreal.AnimSequence, fac)
print('created', anim)

ctrl = None
for getter in (lambda: anim.get_editor_property('controller'), lambda: anim.controller):
    try:
        ctrl = getter()
        if ctrl:
            break
    except Exception as e:
        print('controller getter failed:', e)
print('controller:', ctrl)
ctrl.set_frame_rate(unreal.FrameRate(int(fps), 1))
ctrl.set_number_of_frames(unreal.FrameNumber(nfr - 1))
print('len after set:', unreal.AnimationLibrary.get_sequence_length(anim))

times = [i / fps for i in range(nfr)]
added = 0
for name, vals in data['morphs'].items():
    try:
        unreal.AnimationLibrary.add_curve(anim, name, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    except Exception as e:
        print('add_curve failed', name, e)
    unreal.AnimationLibrary.add_float_curve_keys(anim, name, times, [float(x) for x in vals])
    added += 1
# 頭の動き（度）。骨への適用は未実装のため、名前つきカーブとして持たせる。
#   HeadNodDeg  : +で下向き（MetaHumanの HeadYaw 値）
#   HeadTurnDeg : +で画面右（MetaHumanの HeadRoll 値）
for nm, src in (('HeadNodDeg', 'HeadYaw'), ('HeadTurnDeg', 'HeadRoll')):
    c = mh['curves'][src]
    if c['t']:
        unreal.AnimationLibrary.add_curve(anim, nm, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
        unreal.AnimationLibrary.add_float_curve_keys(anim, nm, c['t'], c['v'])
        added += 1
print('curves added:', added)
unreal.EditorAssetLibrary.save_asset(OUT_PKG + '/' + OUT_NAME)

chk = unreal.load_asset(OUT_PKG + '/' + OUT_NAME)
names = unreal.AnimationLibrary.get_animation_curve_names(chk, unreal.RawCurveTrackTypes.RCT_FLOAT)
print('CHECK curves:', len(names), 'length:', unreal.AnimationLibrary.get_sequence_length(chk))
