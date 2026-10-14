"""Mixamo のアニメだけの FBX を、T-Pose_Skeleton に取り込む（従来の FBX インポーター）。
UnrealEditor-Cmd に  -ExecCmds="Interchange.FeatureFlags.Import.FBX 0"  を付けて実行する。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import os
import unreal

SRC_DIR = _CFG['mixamo_dir']
DEST = '/Game/Mixamo'
# フォルダ内の FBX（T-Pose 以外）を全部取り込む
ANIMS = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith('.fbx') and f.lower() != 'tpose.fbx' and not f.lower().startswith('t-pose'))
skel = unreal.load_asset(DEST + '/T-Pose_Skeleton')
print('skeleton', skel)
tools = unreal.AssetToolsHelpers.get_asset_tools()
for f in ANIMS:
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', False)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_as_skeletal', True)
    ui.set_editor_property('import_animations', True)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property('skeleton', skel)
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', os.path.join(SRC_DIR, f))
    t.set_editor_property('destination_path', DEST)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', True)
    t.set_editor_property('options', ui)
    tools.import_asset_tasks([t])
    print('imported', f, '->', [str(p) for p in t.get_editor_property('imported_object_paths')])
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path(DEST, recursive=True):
    print('ASSET', a.asset_class_path.asset_name, a.package_name)
unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
