"""体の動きのリターゲット検証（UE5.8 / コマンドレット）。
UEマネキンのアニメ → RTG_v4u_1130 → VRoid。結果の関節位置をJSONに出す。揺れモノの設定も点検する。"""
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
import json, os
import unreal

OUT = _os.path.join(_HERE, 'body_retarget')
os.makedirs(OUT, exist_ok=True)
D = _CFG['vroid_dir']
M = '/Game/Characters/Mannequins/'

def safe(o, n):
    try:
        return getattr(o, n)
    except BaseException as e:
        return 'ERR ' + type(e).__name__

# ---- 揺れモノの点検 ----
meta = unreal.load_asset(D + _CFG['meta'])
print('SPRING meta class:', meta.get_class().get_name())
for n in dir(meta):
    if n.startswith('_'):
        continue
    v = safe(meta, n)
    if callable(v):
        continue
    if 'spring' in n.lower() or 'collider' in n.lower():
        try:
            ln = len(v)
        except BaseException:
            ln = '-'
        print('SPRING', n, 'len=', ln)
        try:
            for i, e in enumerate(list(v)[:12]):
                print('   [%d]' % i, str(e)[:200])
        except BaseException:
            pass

sb = safe(meta, 'vrm1_spring_bone_meta')
print('SPRING1 type:', type(sb).__name__)
for n in dir(sb):
    if n.startswith('_'):
        continue
    v = safe(sb, n)
    if callable(v):
        continue
    try:
        ln = len(v)
    except BaseException:
        ln = '-'
    print('SPRING1', n, 'len=', ln, str(v)[:240] if ln == '-' else '')
    if ln not in ('-', 0):
        for i, e in enumerate(list(v)[:40]):
            if hasattr(e, 'get_editor_property') or True:
                s = str(e)
                print('   [%d]' % i, s[:260])

# ---- リターゲット ----
src_mesh = unreal.load_asset(M + 'Meshes/SKM_Manny_Simple')
dst_mesh = unreal.load_asset(D + _CFG['mesh'])
# VRM4U 付属の RTG_v4u_1130 は「Run IK Rig」が有効で、膝・肘が反転して手足が崩れる。
# 複製して Run IK Rig を無効にしたリターゲッタを使う。
RTG_NOIK = '/Game/FaceDrive/RTG_Mannequin_to_VRoid'
if not unreal.EditorAssetLibrary.does_asset_exist(RTG_NOIK):
    if _CFG.get('retargeter') and unreal.EditorAssetLibrary.does_asset_exist(D + _CFG['retargeter']):
        unreal.EditorAssetLibrary.duplicate_asset(D + _CFG['retargeter'], RTG_NOIK)
    else:
        # VRM4U が RTG を作っていない取り込みでは、マネキンの IK Rig とリターゲッタを自前で作る
        _tools = unreal.AssetToolsHelpers.get_asset_tools()
        _rigp = '/Game/FaceDrive/IK_Mannequin_Auto'
        if unreal.EditorAssetLibrary.does_asset_exist(_rigp):
            _rig = unreal.load_asset(_rigp)
        else:
            _rig = _tools.create_asset('IK_Mannequin_Auto', '/Game/FaceDrive', unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
        _rc = unreal.IKRigController.get_controller(_rig)
        _rc.set_skeletal_mesh(src_mesh)
        for _fn in ('apply_auto_generated_retarget_definition', 'apply_auto_retarget_definition', 'auto_generate_retarget_definition'):
            if hasattr(_rc, _fn):
                try:
                    getattr(_rc, _fn)()
                    break
                except BaseException as _e:
                    print(_fn, 'failed', type(_e).__name__)
        unreal.EditorAssetLibrary.save_asset(_rigp)
        _r = _tools.create_asset('RTG_Mannequin_to_VRoid', '/Game/FaceDrive', unreal.IKRetargeter, unreal.IKRetargetFactory())
        _c = unreal.IKRetargeterController.get_controller(_r)
        try:
            _c.remove_all_ops()
        except BaseException:
            pass
        _c.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, _rig)
        _c.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, unreal.load_asset(D + _CFG['ik_rig_mannequin']))
        _c.add_default_ops()
        _c.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
        try:
            _c.auto_align_all_bones(unreal.RetargetSourceOrTarget.SOURCE)
        except BaseException as _e:
            print('auto_align failed', type(_e).__name__)
        unreal.EditorAssetLibrary.save_asset(RTG_NOIK)
        print('created retargeter', RTG_NOIK)
rtg = unreal.load_asset(RTG_NOIK)
_tc = unreal.IKRetargeterController.get_controller(rtg)
for _i in range(_tc.get_num_retarget_ops()):
    if 'ik rig' in str(_tc.get_op_name(_i)).lower():
        _tc.set_retarget_op_enabled(_i, False)
        print('disabled op', _i, str(_tc.get_op_name(_i)))
unreal.EditorAssetLibrary.save_asset(RTG_NOIK)
print('src_mesh', src_mesh, 'dst_mesh', dst_mesh, 'rtg', rtg)

srcs = [
    ('Idle', M + 'Anims/Unarmed/MM_Idle'),
    ('Walk', M + 'Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd'),
    ('Jog', M + 'Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd'),
    ('Attack', M + 'Anims/Unarmed/Attack/MM_Attack_01'),
    ('Charged', M + 'Anims/Unarmed/Attack/MM_ChargedAttack'),
]
objs = [unreal.EditorAssetLibrary.find_asset_data(p) for _, p in srcs]
print('loaded anims:', [str(o.asset_name) for o in objs])
if os.environ.get('FD_FORCE') != '1' and all(unreal.EditorAssetLibrary.does_asset_exist('/Game/FaceDrive/Body/VRM_' + p.split('/')[-1]) for _, p in srcs):
    print('retarget: 既に生成済み（再実行しない。作り直すには FD_FORCE=1）')
else:
    res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        objs, src_mesh, dst_mesh, rtg, '', '', 'VRM_', '', '/Game/FaceDrive/Body', False, False, True)
    print('retarget results:', len(res))
    print('saved:', unreal.EditorAssetLibrary.save_directory('/Game/FaceDrive/Body', only_if_is_dirty=False, recursive=True))

# ---- 関節位置のダンプ ----
def dump(anim, fps=15.0):
    length = anim.get_editor_property('sequence_length') if hasattr(anim, 'get_editor_property') else unreal.AnimationLibrary.get_sequence_length(anim)
    length = float(unreal.AnimationLibrary.get_sequence_length(anim))
    opts = unreal.AnimPoseEvaluationOptions()
    opts.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    n = int(length * fps) + 1
    frames = []
    names = None
    for i in range(n):
        t = min(i / fps, length)
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)
        if names is None:
            names = [str(x) for x in unreal.AnimPoseExtensions.get_bone_names(pose)]
        fr = []
        for b in names:
            tr = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
            p = tr.translation
            fr.append([round(p.x, 2), round(p.y, 2), round(p.z, 2)])
        frames.append(fr)
    return {'fps': fps, 'length': length, 'bones': names, 'frames': frames}

for label, p in srcs:
    a_src = unreal.load_asset(p)
    base = p.split('/')[-1]
    a_dst = unreal.load_asset('/Game/FaceDrive/Body/VRM_' + base)
    for tag, a in (('src', a_src), ('vrm', a_dst)):
        if a is None:
            print('MISSING', label, tag)
            continue
        try:
            d = dump(a)
            json.dump(d, open(os.path.join(OUT, '%s_%s.json' % (label, tag)), 'w'))
            print('DUMP', label, tag, 'bones=%d frames=%d len=%.2f' % (len(d['bones']), len(d['frames']), d['length']))
        except BaseException as e:
            print('DUMP FAIL', label, tag, type(e).__name__, str(e)[:200])
_fd_finish()
