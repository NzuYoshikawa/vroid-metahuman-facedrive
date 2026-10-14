"""Mixamo → VRoid のリターゲッタを作り、取り込んだ Mixamo アニメを VRoid に変換する。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, os
import unreal

DEST = '/Game/Mixamo'
OUT_DIR = '/Game/FaceDrive/Mixamo'
tools = unreal.AssetToolsHelpers.get_asset_tools()
src_mesh = unreal.load_asset(DEST + '/T-Pose')
dst_mesh = unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh']))

def names(o, key):
    return [n for n in dir(o) if key in n.lower() and not n.startswith('_')]

# ---- 1) Mixamo の IK Rig（自動でチェーンを作る）----
p = DEST + '/IK_Mixamo'
if unreal.EditorAssetLibrary.does_asset_exist(p):
    rig = unreal.load_asset(p)            # 既存を使う（削除→再作成は同一セッションで失敗する）
else:
    rig = tools.create_asset('IK_Mixamo', DEST, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
rc = unreal.IKRigController.get_controller(rig)
print('IKRigController fns (auto/chain/root):', names(rc, 'auto') + names(rc, 'chain') + names(rc, 'root'))
rc.set_skeletal_mesh(src_mesh)
ok = None
for fn in ('apply_auto_generated_retarget_definition', 'apply_auto_retarget_definition', 'auto_generate_retarget_definition'):
    if hasattr(rc, fn):
        try:
            ok = getattr(rc, fn)()
            print('auto retarget def via', fn, '->', ok)
            break
        except BaseException as e:
            print(fn, 'failed', type(e).__name__, str(e)[:100])
print('retarget root:', rc.get_retarget_root())
chs = rc.get_retarget_chains()
print('mixamo chains:', [(str(c.get_editor_property('chain_name')),) for c in chs])
unreal.EditorAssetLibrary.save_asset(p)

# ---- 2) リターゲッタ ----
rp = DEST + '/RTG_Mixamo_to_VRoid'
if unreal.EditorAssetLibrary.does_asset_exist(rp):
    rtg = unreal.load_asset(rp)
else:
    rtg = tools.create_asset('RTG_Mixamo_to_VRoid', DEST, unreal.IKRetargeter, unreal.IKRetargetFactory())
tc = unreal.IKRetargeterController.get_controller(rtg)
try:
    tc.remove_all_ops()
except BaseException as e:
    print('remove_all_ops failed', type(e).__name__)
print('IKRetargeterController fns (map/align/chain):', names(tc, 'map') + names(tc, 'align') + names(tc, 'pose'))
tc.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, rig)
# 検証済み: VRM4U が作る Mannequin 形式の IK Rig を使う（VrmHumanoid 形式はチェーン名が合わず誤差 25〜45%、こちらは 9%）
tgt_rig = unreal.load_asset((_CFG['vroid_dir'] + _CFG['ik_rig_mannequin']))
tc.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, tgt_rig)
try:
    tc.add_default_ops()
    print('default ops added; num ops =', tc.get_num_retarget_ops())
    # 「Run IK Rig」は VRM4U の IK Rig（目標側）を実行し、膝・肘の向きが反転して手足が崩れる
    # （Gangnam で関節角の差 15〜23°→0.4〜9°、反転 10→0、手足の速度の外れ値 45倍→4倍）。無効にする。
    for i in range(tc.get_num_retarget_ops()):
        nm = str(tc.get_op_name(i))
        if 'ik rig' in nm.lower():
            tc.set_retarget_op_enabled(i, False)
            print('disabled op', i, nm)
except BaseException as e:
    print('add_default_ops failed', type(e).__name__, str(e)[:120])
try:
    tc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    tgt_chains = [str(c.get_editor_property('chain_name')) for c in unreal.IKRigController.get_controller(tgt_rig).get_retarget_chains()]
    mapping = []
    for tcname in tgt_chains:
        try:
            mapping.append((tcname, str(tc.get_source_chain(tcname, 0))))
        except BaseException as e2:
            mapping.append((tcname, 'ERR ' + type(e2).__name__))
    print('CHAINMAP', mapping)
except BaseException as e:
    print('auto_map_chains failed', type(e).__name__, str(e)[:120])
    for n in dir(unreal):
        if 'AutoMap' in n:
            print('  enum', n)
try:
    tc.auto_align_all_bones(unreal.RetargetSourceOrTarget.SOURCE)
    print('auto aligned source')
except BaseException as e:
    print('auto_align failed', type(e).__name__, str(e)[:120])
unreal.EditorAssetLibrary.save_asset(rp)

# ---- 3) 変換 ----
src_names = sorted(str(a.asset_name) for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(DEST, recursive=False)
                   if str(a.asset_class_path.asset_name) == 'AnimSequence' and not str(a.asset_name).lower().startswith('t-pose'))
datas = [unreal.EditorAssetLibrary.find_asset_data(DEST + '/' + n) for n in src_names]
res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(datas, src_mesh, dst_mesh, rtg, '', '', 'VRM_', '', OUT_DIR, False, False, True)
print('retarget results:', [str(r.asset_name) for r in res])
print('saved:', unreal.EditorAssetLibrary.save_directory(OUT_DIR, only_if_is_dirty=False, recursive=True))
unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
