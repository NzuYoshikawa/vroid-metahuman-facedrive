"""確認用のデモレベル /Game/FaceDrive/Demo_VRoid を作る（VRoid 1体、光、カメラ）。
VRM4U で取り込んだ VRoid は +Y を向くので、カメラと光は +Y 側に置く。
体の動きは ue_make_sequence.py の LevelSequence で与える。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import unreal

LEVEL = '/Game/FaceDrive/Demo_VRoid'
unreal.EditorLevelLibrary.new_level(LEVEL)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0)):
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

actor = spawn(unreal.SkeletalMeshActor)
actor.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh'])))
actor.set_actor_label('VRoid_Demo')

sun = spawn(unreal.DirectionalLight, (0, 300, 300), (0, -30, -90))
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', 10.0)
spawn(unreal.SkyLight, (0, 0, 400))

cam = spawn(unreal.CineCameraActor, (0, 140, 148), (0, 0, -90))
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
unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
