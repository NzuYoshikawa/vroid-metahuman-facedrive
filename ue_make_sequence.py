"""Demo_VRoid レベルのキャラに、指定アニメを繰り返し再生する LevelSequence を作る。
環境変数: FD_SEQ_NAME, FD_ANIM(アセットパス), FD_REPEAT(繰り返し回数), FD_CAM_Y, FD_CAM_Z, FD_FOCAL"""
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
import os
import unreal

SEQ_PATH = '/Game/FaceDrive'
SEQ_NAME = os.environ.get('FD_SEQ_NAME', 'LS_Test')
ANIM = os.environ.get('FD_ANIM', '/Game/FaceDrive/Body/VRM_MF_Unarmed_Jog_Fwd_Grounded')
REPEAT = int(os.environ.get('FD_REPEAT', '4'))
FPS = 30

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/FaceDrive/Demo_VRoid')
by = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
vr, cam = by['VRoid_Demo'], by['Cam_Front']
if os.environ.get('FD_CAM_Y'):
    cam.set_actor_location(unreal.Vector(0, float(os.environ['FD_CAM_Y']), float(os.environ.get('FD_CAM_Z', '110'))), False, False)
    cam.set_actor_rotation(unreal.Rotator(0, 0, -90), False)
    cam.get_cine_camera_component().set_editor_property('current_focal_length', float(os.environ.get('FD_FOCAL', '35')))
    unreal.EditorLoadingAndSavingUtils.save_current_level()

anim = unreal.load_asset(ANIM)
one = int(round(float(unreal.AnimationLibrary.get_sequence_length(anim)) * FPS))
total = one * REPEAT
tools = unreal.AssetToolsHelpers.get_asset_tools()
p = SEQ_PATH + '/' + SEQ_NAME
if unreal.EditorAssetLibrary.does_asset_exist(p):
    unreal.EditorAssetLibrary.delete_asset(p)
ls = tools.create_asset(SEQ_NAME, SEQ_PATH, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
ls.set_display_rate(unreal.FrameRate(FPS, 1))
ls.set_playback_start(0)
ls.set_playback_end(total)
b_vr = ls.add_possessable(vr)
tr = b_vr.add_track(unreal.MovieSceneSkeletalAnimationTrack)
for r in range(REPEAT):
    sec = tr.add_section()
    sec.set_range(r * one, (r + 1) * one)
    params = sec.get_editor_property('params')
    params.set_editor_property('animation', anim)
    sec.set_editor_property('params', params)
b_cam = ls.add_possessable(cam)
cut = ls.add_track(unreal.MovieSceneCameraCutTrack)
cs = cut.add_section()
cs.set_range(0, total)
bs = unreal.MovieSceneObjectBindingID()
bs.set_editor_property('guid', b_cam.get_id())
cs.set_camera_binding_id(bs)
unreal.EditorAssetLibrary.save_asset(p)
print('SEQ ready', SEQ_NAME, 'frames', total)
_fd_finish()
