"""頭の回転（うなずき・左右の向き）を、VRoid の首・頭の骨トラックに入れる。
入力アニメ（体）を複製して <名前>_Head を作る。体の動きの上に、世界座標系の回転を足す:
    local_new = conj(P) * Rw * P * local        (P = 親の世界回転、Rw = うなずき×向き)
パラメーターは head_params.json。UE 内の Python（numpy 無し）。
環境変数: FD_HEAD_ANIM 入力アニメ / FD_HEAD_OUT 出力名 / FD_HEAD_T0 MetaHumanカーブの開始秒 / FD_MH_CURVES"""
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
import json, math, os
import unreal

ROOT = _HERE
P = json.load(open(os.path.join(ROOT, 'head_params.json'), encoding='utf-8-sig'))
SRC = os.environ.get('FD_HEAD_ANIM', '/Game/FaceDrive/AS_VRoid_Demo_Idle_Face')
OUT = os.environ.get('FD_HEAD_OUT', SRC + '_Head')
T0 = float(os.environ.get('FD_HEAD_T0', '8.0'))
MH = json.load(open(os.environ.get('FD_MH_CURVES', os.path.join(ROOT, 'mh_curves.json'))))['curves']
import sys as _sys
_sys.path.insert(0, _HERE)
import fd_common as _fc
_B = _fc.bones(_CFG['vroid_dir'] + _CFG['meta'])
HEAD, NECK = _B['head'], _B['neck']

opts = unreal.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)

# ---- 小さな数学（クォータニオンは (x,y,z,w)、ハミルトン積） ----
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)
def qconj(a): return (-a[0], -a[1], -a[2], a[3])
def qnorm(a):
    n = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / n for c in a)
def qaxis(axis, rad):
    n = math.sqrt(sum(c * c for c in axis)) or 1.0
    s = math.sin(rad / 2) / n
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(rad / 2))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def unit(a):
    n = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def qrot(q, v):
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qconj(q))
    return (p[0], p[1], p[2])
def Q(u): return (u.x, u.y, u.z, u.w)

def pose(anim, t): return unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)
def wt(p, b): return unreal.AnimPoseExtensions.get_bone_pose(p, b, unreal.AnimPoseSpaces.WORLD)

def curve(name, t):
    c = MH.get(name)
    if not c or not c['t']:
        return 0.0
    ts, vs = c['t'], c['v']
    if t <= ts[0]: return vs[0]
    if t >= ts[-1]: return vs[-1]
    lo, hi = 0, len(ts) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if ts[m] <= t: lo = m
        else: hi = m
    a = (t - ts[lo]) / (ts[hi] - ts[lo])
    return vs[lo] * (1 - a) + vs[hi] * a

mesh = unreal.load_asset((_CFG['vroid_dir'] + _CFG['mesh']))
sub_sys = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
neck_parent = str(sub_sys.get_bone_parent(mesh, NECK))
head_parent = str(sub_sys.get_bone_parent(mesh, HEAD))
print('neck parent:', neck_parent, ' head parent:', head_parent)

if unreal.EditorAssetLibrary.does_asset_exist(OUT):
    unreal.EditorAssetLibrary.delete_asset(OUT)
anim = unreal.EditorAssetLibrary.duplicate_asset(SRC, OUT)
n = int(unreal.AnimationLibrary.get_num_frames(anim))
length = float(unreal.AnimationLibrary.get_sequence_length(anim))
ts = [length * i / n for i in range(n + 1)]

# キャラの前方・左方向（0フレーム目の姿勢から）
p0 = pose(anim, 0.0)
tp = lambda b: (lambda v: (v.x, v.y, v.z))(wt(p0, b).translation)
f = sub(tp(_B['l_toes']), tp(_B['l_foot'])); f = unit((f[0], f[1], 0.0))
l = sub(tp(_B['l_upper_arm']), tp(_B['r_upper_arm'])); l = (l[0], l[1], 0.0)
l = unit(sub(l, tuple(c * dot(l, f) for c in f)))
up = (0.0, 0.0, 1.0)
axis_turn = unit(cross(f, l))                       # fをlへ回す軸（左向き）
axis_nod = unit(cross(f, (0.0, 0.0, -1.0)))         # fを下へ回す軸（うなずき）
print('forward', f, ' left', l)

def Rw(nod_deg, turn_deg, frac):
    rn = qaxis(axis_nod, math.radians(nod_deg * frac))
    rt = qaxis(axis_turn, math.radians(turn_deg * frac))
    return qnorm(qmul(rt, rn))

share = float(P['neck_share'])
mx = float(P['max_deg'])
head_tr, neck_tr = [], []
eye_before, eye_after = [], []
log_n = []
eye_bone = None
_names = [str(b) for b in unreal.AnimPoseExtensions.get_bone_names(p0)]
if _B['l_eye'] in _names:
    eye_bone = _B['l_eye']
for i, t in enumerate(ts):
    nod = max(-mx, min(mx, P['nod_sign'] * P['nod_gain'] * curve(P['mh_nod_curve'], T0 + t)))
    turn = max(-mx, min(mx, P['turn_sign'] * P['turn_gain'] * curve(P['mh_turn_curve'], T0 + t)))
    if not P['enable']:
        nod = turn = 0.0
    pz = pose(anim, t)
    qn_world = qnorm(Q(wt(pz, NECK).rotation))
    qnp = qnorm(Q(wt(pz, neck_parent).rotation))
    qh_local = Q(unreal.AnimationLibrary.get_bone_pose_for_time(anim, HEAD, t, False).rotation)
    qn_local = Q(unreal.AnimationLibrary.get_bone_pose_for_time(anim, NECK, t, False).rotation)
    # 首: 割合 share を、世界座標系の回転として足す
    Rn = Rw(nod, turn, share)
    dn = qmul(qmul(qconj(qnp), Rn), qnp)
    qn_local_new = qnorm(qmul(dn, qn_local))
    qn_world_new = qnorm(qmul(Rn, qn_world))
    # 頭: 残りの割合
    Rh = Rw(nod, turn, 1.0 - share)
    dh = qmul(qmul(qconj(qn_world_new), Rh), qn_world_new)
    qh_local_new = qnorm(qmul(dh, qh_local))
    head_tr.append(qh_local_new)
    neck_tr.append(qn_local_new)
    if eye_bone and i % max(1, n // 12) == 0:
        e0 = wt(pz, eye_bone).translation
        hd = wt(pz, HEAD).translation
        eye_before.append((e0.x - hd.x, e0.y - hd.y, e0.z - hd.z, nod, turn, t))

def set_track(bone, quats):
    pos, rot, scl = [], [], []
    for i, t in enumerate(ts):
        tr = unreal.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
        pos.append(tr.translation)
        q = quats[i]
        rot.append(unreal.Quat(q[0], q[1], q[2], q[3]))
        scl.append(tr.scale3d)
    ctrl = anim.get_editor_property('controller')
    try:
        ctrl.open_bracket(unreal.Text('head rotation'), True)
    except BaseException:
        pass
    # 顔だけのアニメ（骨のトラックが無い）では、先にトラックを作らないと set_bone_track_keys が何もしない
    for fn in ('add_bone_curve', 'add_bone_track'):
        if hasattr(ctrl, fn):
            try:
                getattr(ctrl, fn)(bone)
                break
            except BaseException:
                pass
    ctrl.set_bone_track_keys(bone, pos, rot, scl)
    try:
        ctrl.close_bracket(True)
    except BaseException:
        pass

set_track(NECK, neck_tr)
set_track(HEAD, head_tr)
unreal.EditorAssetLibrary.save_asset(OUT)
print('HEAD saved', OUT, 'frames', n + 1, 'length %.2f' % length)

# ---- 検証: 目の位置が、指令どおりの向きに動いたか ----
if eye_bone:
    chk = unreal.load_asset(OUT)
    print('verify with eye bone:', eye_bone)
    for (ex, ey, ez, nod, turn, t) in eye_before:
        pz = pose(chk, t)
        e1 = wt(pz, eye_bone).translation
        hd = wt(pz, HEAD).translation
        d = (e1.x - hd.x - ex, e1.y - hd.y - ey, e1.z - hd.z - ez)
        print('VERIFY t=%.2f nod=%+.1f turn=%+.1f | eye move: left=%+.2f cm down=%+.2f cm' % (t, nod, turn, dot(d, l), -dot(d, up)))
_fd_finish()
