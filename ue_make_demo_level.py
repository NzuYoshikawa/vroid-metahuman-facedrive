"""確認用のデモレベル /Game/FaceDrive/Demo_VRoid を作る（VRoid 1体、光、カメラ）。
VRM4U で取り込んだ VRoid は +Y を向くので、カメラと光は +Y 側に置く。
体の動きは ue_make_sequence.py の LevelSequence で与える。"""
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
import unreal

LEVEL = '/Game/FaceDrive/Demo_VRoid'
unreal.EditorLevelLibrary.new_level(LEVEL)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0)):
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

_mesh = unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh']))
actor = spawn(unreal.SkeletalMeshActor)
actor.skeletal_mesh_component.set_skeletal_mesh_asset(_mesh)
actor.set_actor_label('VRoid_Demo')

sun = spawn(unreal.DirectionalLight, (0, 300, 300), (0, -30, -90))
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', 10.0)
spawn(unreal.SkyLight, (0, 0, 400))

# 背景: 濃い服が黒い背景に溶けないように、キャラの後ろに、明るい灰色の板を置く
_bk = None
try:
    _bk = spawn(unreal.StaticMeshActor, (0, -150, 100), (90, 0, 0))     # 板は +Z を向く。ピッチ 90 度で +Y（カメラ側）に向ける
    _bk.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    _bk.static_mesh_component.set_material(0, unreal.load_asset('/Engine/EngineMaterials/DefaultMaterial'))
    _bk.set_actor_scale3d(unreal.Vector(8, 8, 1))
    _bk.set_actor_label('Backdrop')
except BaseException as e:
    print('backdrop skip', type(e).__name__)

# カメラの位置は、モデルの高さに合わせる（検証したモデルの高さ 162 cm で、前 140 cm・高さ 148 cm）
import sys as _sys
_sys.path.insert(0, _HERE)
import fd_common as _fc
_S = _fc.model_scale(_mesh, (_CFG['vroid_dir'] + _CFG['face_pose_anim']), _fc.bones(_CFG['vroid_dir'] + _CFG['meta'])['head'])
print('FD camera scale', round(_S, 3))
# 上半身（頭と肩）が入る位置。前 200 cm・高さ 140 cm、焦点距離 55 mm（モデルの高さに比例）。画角は 16:9 なので、書き出しは 1280x720 にする
cam = spawn(unreal.CineCameraActor, (0, 200 * _S, 140 * _S), (0, 0, -90))
cam.set_actor_label('Cam_Front')
cc = cam.get_cine_camera_component()
cc.set_editor_property('current_focal_length', 55.0)
try:
    fs = cc.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings', fs)
except BaseException as e:
    print('focus setting skip', type(e).__name__)

unreal.EditorLoadingAndSavingUtils.save_current_level()
print('level saved', LEVEL)
_fd_finish()
