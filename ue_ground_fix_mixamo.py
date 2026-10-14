"""接地補正。リターゲット後の VRoid アニメの腰を上下させ、足が床に沈まないようにする。
パラメーターは ground_params.json。結果は /Game/FaceDrive/Body/VRM_<名前>_Grounded と ground_report.json。
（UE 内の Python には numpy が無いので標準ライブラリのみ）"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, os
import unreal

ROOT = _HERE
P = json.load(open(os.path.join(ROOT, 'ground_params.json'), encoding='utf-8'))
BODY = '/Game/FaceDrive/Mixamo/'
M = '/Game/Mixamo/'
def _anim_names(path):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    out = []
    for a in reg.get_assets_by_path(path, recursive=False):
        if str(a.asset_class_path.asset_name) == 'AnimSequence':
            if not str(a.asset_name).lower().startswith('t-pose'):
                out.append(str(a.asset_name))
    return sorted(out)
NAMES = _anim_names('/Game/Mixamo')   # 取り込んだ動き全部
if 'idle' not in NAMES:
    raise SystemExit('/Game/Mixamo に idle が必要です（基準姿勢に使います）')
SRC_PATH = {n: M + n for n in NAMES}
VR_NAME = {n: 'VRM_' + n for n in NAMES}
SRC_B = dict(hips='Hips', foot_l='LeftFoot', foot_r='RightFoot', th='LeftUpLeg', ca='LeftLeg')
DST_B = dict(hips='J_Bip_C_Hips', foot_l='J_Bip_L_Foot', foot_r='J_Bip_R_Foot', th='J_Bip_L_UpperLeg', ca='J_Bip_L_LowerLeg')

opts = unreal.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)

def pose_at(anim, t):
    return unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)

def wtf(pose, bone):
    return unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)

def foot_z(anim, ts, b):
    out = []
    for t in ts:
        p = pose_at(anim, t)
        out.append((wtf(p, b['foot_l']).translation.z, wtf(p, b['foot_r']).translation.z))
    return out

def dist(u, v):
    return ((u.x - v.x) ** 2 + (u.y - v.y) ** 2 + (u.z - v.z) ** 2) ** 0.5

def leg_len(anim, b):
    p = pose_at(anim, 0.0)
    a, c, f = (wtf(p, b[n]).translation for n in ('th', 'ca', 'foot_l'))
    return dist(a, c) + dist(c, f)

def rot_T_apply(q, v):
    """回転行列の転置（＝逆回転）をベクトル v に適用。q は (x,y,z,w) のクォータニオン。"""
    x, y, z, w = q.x, q.y, q.z, q.w
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [R[0][0] * v[0] + R[1][0] * v[1] + R[2][0] * v[2],
            R[0][1] * v[0] + R[1][1] * v[1] + R[2][1] * v[2],
            R[0][2] * v[0] + R[1][2] * v[1] + R[2][2] * v[2]]

mesh = unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh']))
parent = None
try:
    parent = str(unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_bone_parent(mesh, DST_B['hips']))
except BaseException as e:
    print('get_bone_parent failed:', type(e).__name__, str(e)[:120])
print('hips parent:', parent)

s_idle = unreal.load_asset(SRC_PATH['idle'])
d_idle = unreal.load_asset(BODY + VR_NAME['idle'])
fs, fd = foot_z(s_idle, [0.0], SRC_B)[0], foot_z(d_idle, [0.0], DST_B)[0]
ank_s, ank_d = 0.5 * (fs[0] + fs[1]), 0.5 * (fd[0] + fd[1])
# Mixamo→VRoid は腰の高さの縮尺が合わず、立ち姿でも VRoid が浮く（足首 21.9cm）。
# VRoid が床に立つときの足首高さ（マネキン経由の Idle で実測 10.25cm）を絶対基準にし、浮きも沈みも直す。
ank_d_idle_retarget = ank_d
def _ref_foot_height():
    path = '/Game/FaceDrive/_RefPose'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        a = unreal.load_asset(path)
    else:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', mesh.get_editor_property('skeleton'))
        a = unreal.AssetToolsHelpers.get_asset_tools().create_asset('_RefPose', '/Game/FaceDrive', unreal.AnimSequence, f)
    p = pose_at(a, 0.0)
    return 0.5 * (wtf(p, DST_B['foot_l']).translation.z + wtf(p, DST_B['foot_r']).translation.z)
ank_d = float(os.environ['FD_ANKLE_DST']) if os.environ.get('FD_ANKLE_DST') else _ref_foot_height()
print('standing ankle height from reference pose = %.2f cm' % ank_d)
DZ0 = ank_d - ank_d_idle_retarget          # 全フレーム共通の高さ補正（浮き）。立ち姿の足首が絶対基準に合う量
print('constant height offset DZ0 = %.2f cm' % DZ0)
k = leg_len(d_idle, DST_B) / leg_len(s_idle, SRC_B)
print('ankle height src=%.2f dst=%.2f  leg ratio k=%.3f' % (ank_s, ank_d, k))

def smooth(a, n):
    if n <= 1:
        return a
    h = n // 2
    out = []
    for i in range(len(a)):
        lo, hi = max(0, i - h), min(len(a), i + h + 1)
        out.append(sum(a[lo:hi]) / (hi - lo))
    return out

report = {'ankle_src': ank_s, 'ankle_dst': ank_d, 'k': k, 'params': P, 'anims': {}}
for name in NAMES:
    src = unreal.load_asset(SRC_PATH[name])
    dst = unreal.load_asset(BODY + VR_NAME[name])
    out_path = BODY + VR_NAME[name] + '_Grounded'
    if unreal.EditorAssetLibrary.does_asset_exist(out_path):
        unreal.EditorAssetLibrary.delete_asset(out_path)
    fixed = unreal.EditorAssetLibrary.duplicate_asset(BODY + VR_NAME[name], out_path)
    n = int(unreal.AnimationLibrary.get_num_frames(fixed))
    length = float(unreal.AnimationLibrary.get_sequence_length(fixed))
    ts = [length * i / n for i in range(n + 1)]
    zs, zd = foot_z(src, ts, SRC_B), foot_z(dst, ts, DST_B)
    # 共通の高さ補正 DZ0 を当てたうえで、なお沈む分だけを持ち上げる（足の接地の入れ替わりで腰が跳ねないよう、沈み補正のみ）
    need = [[ank_d + k * (zs[i][j] - ank_s) - (zd[i][j] + DZ0) for j in (0, 1)] for i in range(len(ts))]   # 正＝沈んでいる
    sink = [max(max(a, b), 0.0) if max(a, b) > P['sink_tolerance_cm'] else 0.0 for a, b in need]
    sm_n = int(P.get('smooth_frames_by_anim', {}).get(name, P['smooth_frames']))
    dz = [DZ0 + float(P['strength']) * s for s in smooth(sink, sm_n)]

    pos, rot, scl = [], [], []
    for i, t in enumerate(ts):
        tr = unreal.AnimationLibrary.get_bone_pose_for_time(dst, DST_B['hips'], t, False)   # 元（無補正）から読む
        v = [0.0, 0.0, dz[i]]
        if parent and parent != 'None':
            v = rot_T_apply(wtf(pose_at(dst, t), parent).rotation, v)
        loc = tr.translation
        pos.append(unreal.Vector(loc.x + v[0], loc.y + v[1], loc.z + v[2]))
        rot.append(tr.rotation)
        scl.append(tr.scale3d)
    ctrl = fixed.get_editor_property('controller')
    try:
        ctrl.open_bracket(unreal.Text('ground fix'), True)
    except BaseException:
        pass
    ctrl.set_bone_track_keys(DST_B['hips'], pos, rot, scl)
    try:
        ctrl.close_bracket(True)
    except BaseException:
        pass
    unreal.EditorAssetLibrary.save_asset(out_path)

    zd2 = foot_z(unreal.load_asset(out_path), ts, DST_B)
    need2 = [[ank_d + k * (zs[i][j] - ank_s) - zd2[i][j] for j in (0, 1)] for i in range(len(ts))]
    need_orig = [[ank_d + k * (zs[i][j] - ank_s) - zd[i][j] for j in (0, 1)] for i in range(len(ts))]
    sink_before = max(max(max(a, b), 0.0) for a, b in need_orig)
    sink_after = max(max(max(a, b), 0.0) for a, b in need2)
    report['anims'][name] = {'frames': len(ts), 'max_sink_cm_before': sink_before, 'max_sink_cm_after': sink_after,
                             'max_lift_cm': max(dz), 'mean_lift_cm': sum(dz) / len(dz)}
    print('GROUND', name, 'sink before=%.2f after=%.2f  lift max=%.2f mean=%.2f cm' % (sink_before, sink_after, max(dz), sum(dz) / len(dz)))
json.dump(report, open(os.path.join(ROOT, 'ground_report_mixamo.json'), 'w'), indent=1)
unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
