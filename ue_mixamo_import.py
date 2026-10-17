"""Mixamo の FBX を /Game/Mixamo に取り込む（UE5.8 の Interchange パイプライン）。
最初の1本でスケルトンとメッシュを作り、残りはそのスケルトンへアニメのみ取り込む。"""
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
import os
import unreal

SRC_DIR = _CFG['mixamo_dir']
DEST = '/Game/Mixamo'
FIRST = 'T-Pose.fbx'      # 蒙皮メッシュつき（骨格の元）。他の FBX はアニメのみ
# T-Pose.fbx だけここで取り込む。ほかの動き（アニメのみの FBX）は ue_mixamo_anims.py が取り込む
ANIMS = [FIRST]

def pipe_for(with_mesh, skeleton=None):
    p = unreal.InterchangeGenericAssetsPipeline()
    p.common_meshes_properties.set_editor_property('force_all_mesh_as_type', unreal.InterchangeForceMeshType.IFMT_SKELETAL_MESH)
    p.mesh_pipeline.set_editor_property('import_skeletal_meshes', bool(with_mesh))
    p.mesh_pipeline.set_editor_property('import_static_meshes', False)
    p.mesh_pipeline.set_editor_property('create_physics_asset', False)
    ap = p.animation_pipeline
    for n, v in (('import_animations', True), ('import_bone_tracks', True)):
        try:
            ap.set_editor_property(n, v)
        except BaseException as e:
            print('anim prop skip', n, type(e).__name__)
    c = p.common_skeletal_meshes_and_animations_properties
    if skeleton is not None:
        c.set_editor_property('skeleton', skeleton)
        c.set_editor_property('import_only_animations', True)
    return p

def run(path, pipe):
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', path)
    t.set_editor_property('destination_path', DEST)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', True)
    t.set_editor_property('options', pipe)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return [str(x) for x in t.get_editor_property('imported_object_paths')]

print('first import:', run(os.path.join(SRC_DIR, FIRST), pipe_for(True)))
reg = unreal.AssetRegistryHelpers.get_asset_registry()
skel = None
for a in reg.get_assets_by_path(DEST, recursive=True):
    if str(a.asset_class_path.asset_name) == 'Skeleton':
        skel = a.get_asset()
        print('skeleton:', a.package_name)
        break
for f in ANIMS:
    if f == FIRST:
        continue
    print('imported', f, '->', run(os.path.join(SRC_DIR, f), pipe_for(False, skel)))
for a in reg.get_assets_by_path(DEST, recursive=True):
    print('ASSET', a.asset_class_path.asset_name, a.package_name)
_fd_finish()
