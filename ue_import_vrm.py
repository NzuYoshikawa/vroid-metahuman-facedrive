"""VRM を、ダイアログなしで UE に取り込み、config.json の名前の欄を自動で書き込む。
VRM4U の ImportVRMFileWithOptions を使う（エディタを開いてドロップする操作の代わり）。

config.json の項目:
  vrm        取り込む VRM ファイルのパス（必須）
  vroid_dir  取り込み先（例 "/Game/Characters/MyModel/"）。末尾は / にする
環境変数（任意）: FD_MODEL_SCALE（取り込み時の拡大率。既定 1.0。身長の違うモデルの検証用）
結果: vroid_dir 内のアセットを探して、mesh / skeleton / meta / retargeter / ik_rig_mannequin / face_pose_anim を書き込む。"""
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

import os, json
import unreal

vrm = _CFG.get('vrm')
dest = _CFG.get('vroid_dir', '/Game/')
if not vrm or not os.path.exists(vrm):
    raise SystemExit('config.json の "vrm" に、取り込む VRM ファイルのパスを書いてください: %r' % vrm)
dest_dir = dest.rstrip('/')
# VRM4U は、渡したパッケージ名の「親フォルダ」にアセットを作る。そのため、取り込み先フォルダの下に、ファイル名を付けて渡す
dest_pkg = dest_dir + '/' + os.path.splitext(os.path.basename(vrm))[0]

# 取り込み直後にメッシュを保存すると、非同期のメッシュのビルドが終わる前に保存されて、表情（モーフ）や大きさの情報が欠けた
# アセットになることがあった。ビルドを同期にして防ぐ
for _c in ('Editor.AsyncSkeletalMeshCompilation 0', 'Editor.AsyncStaticMeshCompilation 0'):
    try:
        unreal.SystemLibrary.execute_console_command(None, _c)
    except BaseException as _e:
        print('FD cvar failed', _c, type(_e).__name__)

opt = unreal.ImportOptionData()
opt.set_editor_property('model_scale', float(os.environ.get('FD_MODEL_SCALE', '1.0')))
# エディタの取り込みダイアログの既定値に合わせる（IK Rig・リターゲッタ・物理アセットを作る）
for _n, _v in (('generate_rig_ik', True), ('skip_physics', False), ('vrm10_remove_local_rotation', False), ('optimize_vertex', False)):
    try:
        opt.set_editor_property(_n, _v)
    except BaseException as _e:
        print('FD option skipped', _n, type(_e).__name__)
_b = os.path.splitext(os.path.basename(vrm))[0]
_need = ['SK_' + _b, 'SKEL_' + _b, 'VM_' + _b + '_VrmMeta', 'A_face_' + _b]      # VRM4U の命名（ファイル名から決まる）


def _import_once():
    print('FD import', vrm, '->', dest_pkg, 'scale', opt.get_editor_property('model_scale'))
    r = unreal.VrmImporterBPFunctionLibrary.import_vrm_file_with_options(vrm, dest_pkg, opt)
    print('FD import result:', r)
    return r


def _complete():
    """必要なアセットが揃い、メッシュに表情（モーフ）が入っているか。"""
    miss = [n for n in _need if not unreal.EditorAssetLibrary.does_asset_exist(dest_dir + '/' + n)]
    if miss:
        return False, 'missing ' + ','.join(miss)
    try:
        n = len(unreal.load_asset(dest_dir + '/' + _need[0]).get_editor_property('morph_targets'))
    except BaseException as e:
        return False, 'mesh load ' + type(e).__name__
    return (n > 0), 'morph_targets=%d' % n


# 取り込みが不完全になることがまれにある（アセットの一部が作られない、表情が欠ける）。揃うまで、最大3回やり直す
for _try in range(3):
    res = _import_once()
    if res is None:
        raise SystemExit('取り込みに失敗しました')
    try:
        unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([dest_dir], True)
    except BaseException:
        pass
    _ok, _why = _complete()
    print('FD import try %d: %s (%s)' % (_try + 1, 'complete' if _ok else 'INCOMPLETE', _why))
    if _ok:
        break
else:
    raise SystemExit('取り込みが3回とも不完全でした（%s）。UE を再起動して、もう一度実行してください' % _why)

# 取り込み先から、各アセットの名前を探す。VRM4U の命名で決まるものを優先し、足りないものだけレジストリから補う
reg = unreal.AssetRegistryHelpers.get_asset_registry()
found = {}
for _k, _n in (('mesh', _need[0]), ('skeleton', _need[1]), ('meta', _need[2]), ('face_pose_anim', _need[3])):
    found[_k] = _n
for _k, _n in (('retargeter', 'RTG_' + _b), ('ik_rig_mannequin', 'IK_' + _b + '_Mannequin')):
    if unreal.EditorAssetLibrary.does_asset_exist(dest_dir + '/' + _n):
        found[_k] = _n
print('FD found assets:', found)

# ダイアログなしの取り込みでは、VRM4U が IK Rig を作らない。マネキン形式の IK Rig を、人型ボーン対応表から作る
import sys
sys.path.insert(0, _HERE)
import fd_common as _fc
if 'ik_rig_mannequin' not in found and 'mesh' in found and 'meta' in found:
    _base = os.path.splitext(os.path.basename(vrm))[0]
    _root = None
    try:
        _fa = unreal.load_asset(dest_dir + '/' + found['face_pose_anim'])
        _o = unreal.AnimPoseEvaluationOptions()
        _o.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
        _root = str(list(unreal.AnimPoseExtensions.get_bone_names(unreal.AnimPoseExtensions.get_anim_pose_at_time(_fa, 0.0, _o)))[0])
    except BaseException as _e:
        print('FD root bone lookup failed', type(_e).__name__)
    _rn = 'IK_' + _base + '_Mannequin'
    _fc.ensure_ik_rig(dest_dir + '/' + found['mesh'], dest_dir + '/' + found['meta'], dest_dir + '/' + _rn, _root)
    found['ik_rig_mannequin'] = _rn

unreal.EditorAssetLibrary.save_directory(dest_dir, only_if_is_dirty=False, recursive=True)

cfg = dict(_CFG)
cfg['vroid_dir'] = dest_dir + '/'
cfg.update(found)
with open(_CFG_PATH, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=1)
print('FD config.json updated:', _CFG_PATH)
_fd_finish()
