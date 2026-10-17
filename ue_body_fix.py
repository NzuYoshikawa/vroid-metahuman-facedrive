"""足の沈みと手の貫通の補正（脚・腕の2ボーン IK）。UE 内 Python（numpy 無し）。
入力: リターゲット済み VRM_<名前>（無補正）。出力: VRM_<名前>_Fixed と body_fix_report_<set>.json。
環境変数 FD_SET = mannequin | mixamo。パラメーターは body_fix_params.json。"""
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
import json, math, os
import unreal

ROOT = _HERE
P = json.load(open(os.path.join(ROOT, 'body_fix_params.json'), encoding='utf-8'))
SET = os.environ.get('FD_SET', 'mixamo')

if SET == 'mannequin':
    BODY = '/Game/FaceDrive/Body/'
    M = '/Game/Characters/Mannequins/Anims/Unarmed/'
    NAMES = ['Idle', 'Walk', 'Jog', 'Attack', 'Charged']
    SRC_PATH = {'Idle': M + 'MM_Idle', 'Walk': M + 'Walk/MF_Unarmed_Walk_Fwd', 'Jog': M + 'Jog/MF_Unarmed_Jog_Fwd',
                'Attack': M + 'Attack/MM_Attack_01', 'Charged': M + 'Attack/MM_ChargedAttack'}
    VR_NAME = {'Idle': 'VRM_MM_Idle', 'Walk': 'VRM_MF_Unarmed_Walk_Fwd', 'Jog': 'VRM_MF_Unarmed_Jog_Fwd',
               'Attack': 'VRM_MM_Attack_01', 'Charged': 'VRM_MM_ChargedAttack'}
    SRC_B = dict(foot_l='foot_l', foot_r='foot_r', th='thigh_l', ca='calf_l')
    IDLE = 'Idle'
else:
    BODY = '/Game/FaceDrive/Mixamo/'
    NAMES = [str(a.asset_name) for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game/Mixamo', recursive=False)
             if str(a.asset_class_path.asset_name) == 'AnimSequence' and not str(a.asset_name).lower().startswith('t-pose')]
    NAMES.sort()
    SRC_PATH = {n: '/Game/Mixamo/' + n for n in NAMES}
    VR_NAME = {n: 'VRM_' + n for n in NAMES}
    SRC_B = dict(foot_l='LeftFoot', foot_r='RightFoot', th='LeftUpLeg', ca='LeftLeg')
    IDLE = 'idle'
import sys as _sys
_sys.path.insert(0, _HERE)
import fd_common as _fc
_B = _fc.bones(_CFG['vroid_dir'] + _CFG['meta'])
# 骨の名前は、VRM の人型ボーン対応表から引く（VRoid Studio 以外のモデルにも対応）
HIPS, NECK, HEAD = _B['hips'], _B['neck'], _B['head']
UPCH = _B['upper_chest']
LEG = {'L': (_B['l_upper_leg'], _B['l_lower_leg'], _B['l_foot']), 'R': (_B['r_upper_leg'], _B['r_lower_leg'], _B['r_foot'])}
ARM = {'L': (_B['l_upper_arm'], _B['l_lower_arm'], _B['l_hand']), 'R': (_B['r_upper_arm'], _B['r_lower_arm'], _B['r_hand'])}
SCALE = 1.0      # モデルの高さ / 検証したモデルの高さ。手を避ける半径と余白（cm）に掛ける（下で設定）
NEED = [HIPS, NECK, HEAD, UPCH] + [b for v in list(LEG.values()) + list(ARM.values()) for b in v]

opts = unreal.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)

# ---- 数学 ----
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)
def qconj(a): return (-a[0], -a[1], -a[2], a[3])
def qn(a):
    n = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / n for c in a)
def qrot(q, v):
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qconj(q))
    return (p[0], p[1], p[2])
def arc(u, v):
    u, v = unit(u), unit(v)
    d = dot(u, v)
    if d < -0.999999:
        ax = cross(u, (1.0, 0.0, 0.0))
        if norm(ax) < 1e-6:
            ax = cross(u, (0.0, 1.0, 0.0))
        ax = unit(ax)
        return (ax[0], ax[1], ax[2], 0.0)
    c = cross(u, v)
    return qn((c[0], c[1], c[2], 1.0 + d))
def T3(v): return (v.x, v.y, v.z)
def Q4(q): return (q.x, q.y, q.z, q.w)

def pose_at(anim, t): return unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)
def wtf(pose, b): return unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)

def seg_closest(p, a, b):
    ab = sub(b, a)
    t = max(0.0, min(1.0, dot(sub(p, a), ab) / (dot(ab, ab) or 1.0)))
    return add(a, mul(ab, t))

def two_bone(A, B, C, T):
    a, b = norm(sub(B, A)), norm(sub(C, B))
    to = sub(T, A)
    d = norm(to)
    d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, d))
    u = unit(to)
    along = (a * a - b * b + d * d) / (2 * d)
    h = math.sqrt(max(a * a - along * along, 0.0))
    cur = sub(B, A)
    pole = sub(cur, mul(u, dot(cur, u)))
    pole = unit(pole) if norm(pole) > 1e-6 else (0.0, 1.0, 0.0)
    K = add(add(A, mul(u, along)), mul(pole, h))
    Cn = add(A, mul(u, d))
    return K, Cn

def smooth_vec(vs, n):
    if n <= 1:
        return vs
    h = n // 2
    out = []
    for i in range(len(vs)):
        lo, hi = max(0, i - h), min(len(vs), i + h + 1)
        k = hi - lo
        out.append((sum(v[0] for v in vs[lo:hi]) / k, sum(v[1] for v in vs[lo:hi]) / k, sum(v[2] for v in vs[lo:hi]) / k))
    return out

def dilate_smooth(vs, n):
    """窓内で最も大きい変位を採ってから平均する（短い衝撃フレームの沈みを薄めない）。"""
    h = max(1, n // 2) if n > 1 else 0
    out = []
    for i in range(len(vs)):
        win = vs[max(0, i - h):min(len(vs), i + h + 1)]
        out.append(max(win, key=lambda v: dot(v, v)))
    return smooth_vec(out, n)

def snapshot(anim, ts, dz):
    """全フレームの世界位置・回転（腰を dz だけ下げた状態）。"""
    out = []
    for t in ts:
        p = pose_at(anim, t)
        fr = {}
        for b in NEED:
            tr = wtf(p, b)
            pos = T3(tr.translation)
            fr[b] = (add(pos, (0.0, 0.0, dz)), qn(Q4(tr.rotation)))
        out.append(fr)
    return out

def penetration(fr, side):
    """手首と前腕の中点が、胴・太もも・頭にめり込む深さ（cm, 正＝めり込み）と、押し出す法線。"""
    _, _, hand = ARM[side]
    el, wr = ARM[side][1], ARM[side][2]
    pts = [fr[wr][0], mul(add(fr[el][0], fr[wr][0]), 0.5)]
    worst = (0.0, None, None)
    m = P['hand_margin_cm'] * SCALE
    cols = [(fr[HIPS][0], fr[NECK][0], P['torso_radius_cm'] * SCALE + m)]
    for s in ('L', 'R'):
        cols.append((fr[LEG[s][0]][0], fr[LEG[s][1]][0], P['thigh_radius_cm'] * SCALE + m))
    cols.append((fr[HEAD][0], add(fr[HEAD][0], (0, 0, 8.0 * SCALE)), P['head_radius_cm'] * SCALE + m))
    for k, p in enumerate(pts):
        for (a, b, r) in cols:
            c = seg_closest(p, a, b)
            d = norm(sub(p, c))
            depth = r - d
            if depth > worst[0]:
                n = unit(sub(p, c)) if d > 1e-6 else (1.0 if side == 'L' else -1.0, 0.0, 0.0)
                worst = (depth, n, k)
    return worst

# ---- 基準（立ち姿）----
src_idle = unreal.load_asset(SRC_PATH[IDLE])
dst_idle = unreal.load_asset(BODY + VR_NAME[IDLE])
def foot_z0(anim, b):
    p = pose_at(anim, 0.0)
    return 0.5 * (wtf(p, b['foot_l']).translation.z + wtf(p, b['foot_r']).translation.z)
dstb = dict(foot_l=LEG['L'][2], foot_r=LEG['R'][2])
ank_s = foot_z0(src_idle, SRC_B)
ank_idle_dst = foot_z0(dst_idle, dstb)
def _ref_foot_height():
    """VRoid が基準姿勢で床に立つときの足首の高さ（cm）。トラックの無い AnimSequence は基準姿勢を返す。"""
    path = '/Game/FaceDrive/_RefPose'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        a = unreal.load_asset(path)
    else:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh'])).get_editor_property('skeleton'))
        a = unreal.AssetToolsHelpers.get_asset_tools().create_asset('_RefPose', '/Game/FaceDrive', unreal.AnimSequence, f)
    p = pose_at(a, 0.0)
    return 0.5 * (wtf(p, LEG['L'][2]).translation.z + wtf(p, LEG['R'][2]).translation.z)
ANK_D = float(os.environ['FD_ANKLE_DST']) if os.environ.get('FD_ANKLE_DST') else _ref_foot_height()
DZ0 = (ANK_D - ank_idle_dst) if SET == 'mixamo' else 0.0
def leg_len(anim, names):
    p = pose_at(anim, 0.0)
    a, c, f = (wtf(p, n).translation for n in names)
    d = lambda u, v: math.sqrt((u.x - v.x) ** 2 + (u.y - v.y) ** 2 + (u.z - v.z) ** 2)
    return d(a, c) + d(c, f)
K = leg_len(dst_idle, LEG['L']) / leg_len(src_idle, (SRC_B['th'], SRC_B['ca'], SRC_B['foot_l']))
print('SET', SET, 'ank_s=%.2f ank_dst_idle=%.2f ANK_D=%.2f DZ0=%.2f k=%.3f' % (ank_s, ank_idle_dst, ANK_D, DZ0, K))
parent_hips = str(unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_bone_parent(unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh'])), HIPS))
parent_of = {}
sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
mesh = unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh']))
SCALE = _fc.model_scale(mesh, (_CFG['vroid_dir'] + _CFG['face_pose_anim']), HEAD)
print('FD model head height %.1f cm  scale vs reference model %.3f' % (_fc.model_height_cm(mesh, (_CFG['vroid_dir'] + _CFG['face_pose_anim']), HEAD), SCALE))
for side in ('L', 'R'):
    for b in LEG[side][:1] + ARM[side][:1]:
        parent_of[b] = str(sk.get_bone_parent(mesh, b))
print('parents', parent_of)

report = {'set': SET, 'DZ0': DZ0, 'model_scale': SCALE, 'params': P, 'anims': {}}
P_BASE = dict(P)
for name in NAMES:
    # 動きごとの個別設定（body_fix_params.json の "per_anim": {"gangnam_style": {"strength": 0.8}}）
    P = dict(P_BASE)
    P.update(P_BASE.get('per_anim', {}).get(name, {}))
    src = unreal.load_asset(SRC_PATH[name])
    dst = unreal.load_asset(BODY + VR_NAME[name])
    out_path = BODY + VR_NAME[name] + '_Fixed'
    if unreal.EditorAssetLibrary.does_asset_exist(out_path):
        unreal.EditorAssetLibrary.delete_asset(out_path)
    fixed = unreal.EditorAssetLibrary.duplicate_asset(BODY + VR_NAME[name], out_path)
    n = int(unreal.AnimationLibrary.get_num_frames(fixed))
    length = float(unreal.AnimationLibrary.get_sequence_length(fixed))
    ts = [length * i / n for i in range(n + 1)]
    snap = snapshot(dst, ts, DZ0)

    # 目標足首高さ
    tz = []
    for t in ts:
        ps = pose_at(src, t)
        tz.append({s: ANK_D + K * (wtf(ps, SRC_B['foot_l' if s == 'L' else 'foot_r']).translation.z - ank_s) for s in ('L', 'R')})

    # 必要な変位（足: 上へ持ち上げる量 / 手: 押し出す量）
    foot_off = {s: [] for s in ('L', 'R')}
    hand_off = {s: [] for s in ('L', 'R')}
    sink_before = pen_before = 0.0
    pen_frames_before = 0
    for i, fr in enumerate(snap):
        for s in ('L', 'R'):
            need = tz[i][s] - fr[LEG[s][2]][0][2]
            sink_before = max(sink_before, need)
            foot_off[s].append((0.0, 0.0, need if (P['foot_ik'] and need > P['sink_tolerance_cm']) else 0.0))
            depth, nrm, _ = penetration(fr, s)
            pen_before = max(pen_before, depth)
            if depth > P['penetration_tolerance_cm']:
                pen_frames_before += 1
            hand_off[s].append(mul(nrm, depth) if (P['hand_push'] and depth > P['penetration_tolerance_cm'] and nrm) else (0.0, 0.0, 0.0))
    for s in ('L', 'R'):
        foot_off[s] = dilate_smooth(foot_off[s], int(P['smooth_frames']))
        hand_off[s] = dilate_smooth(hand_off[s], int(P['smooth_frames']))

    # IK を解いてローカル回転を作る
    new_rot = {b: [] for s in ('L', 'R') for b in LEG[s] + ARM[s]}
    for i, fr in enumerate(snap):
        for s in ('L', 'R'):
            for chain, off in ((LEG[s], foot_off[s][i]), (ARM[s], hand_off[s][i])):
                b0, b1, b2 = chain
                A, B, C = fr[b0][0], fr[b1][0], fr[b2][0]
                q0, q1, q2 = fr[b0][1], fr[b1][1], fr[b2][1]
                par_w = None
                if norm(off) > 1e-4:
                    off = mul(off, float(P['strength']))
                    Kn, Cn = two_bone(A, B, C, add(C, off))
                    d1 = arc(sub(B, A), sub(Kn, A))
                    v2 = qrot(d1, sub(C, B))
                    d2 = arc(v2, sub(Cn, Kn))
                    q0n = qn(qmul(d1, q0))
                    q1n = qn(qmul(d2, qmul(d1, q1)))
                    q2n = q2
                else:
                    q0n, q1n, q2n = q0, q1, q2
                pw = qn(Q4(wtf(pose_at(dst, ts[i]), parent_of[b0]).rotation))
                new_rot[b0].append(qn(qmul(qconj(pw), q0n)))
                new_rot[b1].append(qn(qmul(qconj(q0n), q1n)))
                new_rot[b2].append(qn(qmul(qconj(q1n), q2n)))

    def write_track(bone, quats, dz_hips=0.0):
        pos, rot, scl = [], [], []
        for i, t in enumerate(ts):
            tr = unreal.AnimationLibrary.get_bone_pose_for_time(dst, bone, t, False)
            loc = tr.translation
            if bone == HIPS and dz_hips != 0.0:
                pr = qn(Q4(wtf(pose_at(dst, t), parent_hips).rotation))
                v = qrot(qconj(pr), (0.0, 0.0, dz_hips))
                loc = unreal.Vector(loc.x + v[0], loc.y + v[1], loc.z + v[2])
            pos.append(loc)
            q = quats[i] if quats else Q4(tr.rotation)
            rot.append(unreal.Quat(q[0], q[1], q[2], q[3]))
            scl.append(tr.scale3d)
        ctrl = fixed.get_editor_property('controller')
        try:
            ctrl.open_bracket(unreal.Text('body fix'), True)
        except BaseException:
            pass
        ctrl.set_bone_track_keys(bone, pos, rot, scl)
        try:
            ctrl.close_bracket(True)
        except BaseException:
            pass
    for b, qs in new_rot.items():
        write_track(b, qs)
    if DZ0 != 0.0:
        write_track(HIPS, None, DZ0)
    unreal.EditorAssetLibrary.save_asset(out_path)

    # 再評価
    chk = unreal.load_asset(out_path)
    snap2 = []
    for t in ts:
        p = pose_at(chk, t)
        snap2.append({b: (T3(wtf(p, b).translation), qn(Q4(wtf(p, b).rotation))) for b in NEED})
    sink_after = pen_after = 0.0
    pen_frames_after = 0
    for i, fr in enumerate(snap2):
        for s in ('L', 'R'):
            sink_after = max(sink_after, tz[i][s] - fr[LEG[s][2]][0][2])
            depth, _, _ = penetration(fr, s)
            pen_after = max(pen_after, depth)
            if depth > P['penetration_tolerance_cm']:
                pen_frames_after += 1
    report['anims'][name] = {'frames': len(ts), 'sink_before_cm': max(sink_before, 0.0), 'sink_after_cm': max(sink_after, 0.0),
                             'pen_before_cm': max(pen_before, 0.0), 'pen_after_cm': max(pen_after, 0.0),
                             'pen_frames_before': pen_frames_before, 'pen_frames_after': pen_frames_after}
    print('FIX %s sink %.2f -> %.2f cm | hand penetration %.2f -> %.2f cm (frames %d -> %d of %d)' %
          (name, max(sink_before, 0), max(sink_after, 0), max(pen_before, 0), max(pen_after, 0), pen_frames_before, pen_frames_after, len(ts)))
json.dump(report, open(os.path.join(ROOT, 'body_fix_report_%s.json' % SET), 'w'), indent=1)
_fd_finish()
