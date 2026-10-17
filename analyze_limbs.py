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
import json, sys
import numpy as np
R = _os.path.join(_HERE, 'body_retarget')
name = sys.argv[1] if len(sys.argv) > 1 else 'gangnam_style'
tag = sys.argv[2] if len(sys.argv) > 2 else ''
mq = tag == 'mq'          # UE マネキン由来（body_retarget\<名前>_{src,vrm}.json）
if mq:
    pre = name
else:
    pre = ('mx_%s_%s' % (tag, name)) if tag else ('mx_%s' % name)
S = json.load(open(R + '\\%s_src.json' % pre)); V = json.load(open(R + '\\%s_vrm.json' % pre))
si = {b: i for i, b in enumerate(S['bones'])}; vi = {b: i for i, b in enumerate(V['bones'])}
FS, FV = np.array(S['frames']), np.array(V['frames'])
n = min(len(FS), len(FV)); fps = S['fps']
if mq:
    chains = {
     'L arm': (('upperarm_l', 'lowerarm_l', 'hand_l'), ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand')),
     'R arm': (('upperarm_r', 'lowerarm_r', 'hand_r'), ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand')),
     'L leg': (('thigh_l', 'calf_l', 'foot_l'), ('J_Bip_L_UpperLeg', 'J_Bip_L_LowerLeg', 'J_Bip_L_Foot')),
     'R leg': (('thigh_r', 'calf_r', 'foot_r'), ('J_Bip_R_UpperLeg', 'J_Bip_R_LowerLeg', 'J_Bip_R_Foot')),
    }
else:
    chains = {  # (上, 中, 末) 元 / VRoid
     'L arm': (('LeftArm', 'LeftForeArm', 'LeftHand'), ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand')),
     'R arm': (('RightArm', 'RightForeArm', 'RightHand'), ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand')),
     'L leg': (('LeftUpLeg', 'LeftLeg', 'LeftFoot'), ('J_Bip_L_UpperLeg', 'J_Bip_L_LowerLeg', 'J_Bip_L_Foot')),
     'R leg': (('RightUpLeg', 'RightLeg', 'RightFoot'), ('J_Bip_R_UpperLeg', 'J_Bip_R_LowerLeg', 'J_Bip_R_Foot')),
    }
def P(F, idx, names): return [F[:n, idx[b], :] for b in names]
def angle(a, b, c):
    u, v = a - b, c - b
    cs = np.sum(u * v, axis=1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cs, -1, 1)))
def normal(a, b, c):
    nrm = np.cross(a - b, c - b)
    return nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
print('anim', name, 'frames', n, 'fps', fps)
bad_frames = set()
for k, (sn, vn) in chains.items():
    a, b, c = P(FS, si, sn); A, B, C = P(FV, vi, vn)
    ang_s, ang_v = angle(a, b, c), angle(A, B, C)
    d = ang_v - ang_s
    nv = normal(A, B, C); ns = normal(a, b, c)
    flip_v = np.sum(nv[1:] * nv[:-1], axis=1)            # 屈曲面の向きが急に反転したら負
    # 骨の長さ（VRoid）の変動
    l1, l2 = np.linalg.norm(A - B, axis=1), np.linalg.norm(B - C, axis=1)
    var1, var2 = (l1.max() - l1.min()) / l1.mean() * 100, (l2.max() - l2.min()) / l2.mean() * 100
    # 関節角の1フレーム変化量
    jump = np.abs(np.diff(ang_v))
    bad = np.where((np.abs(d) > 35) | (np.concatenate([[1], flip_v]) < 0.0))[0]
    bad_frames |= set(bad.tolist())
    print('%-6s elbow/knee angle diff: mean %.1f max %.1f deg | bone-length var %.2f%% %.2f%% | max 1-step angle jump %.0f deg | plane flips %d | frames |diff|>35 or flip: %d'
          % (k, np.mean(np.abs(d)), np.max(np.abs(d)), var1, var2, jump.max(), int(np.sum(flip_v < 0)), len(bad)))
bf = sorted(bad_frames)
print('bad frames (15fps index):', bf[:40], '...' if len(bf) > 40 else '', 'total', len(bf), 'of', n)
# 手足の速度の外れ値（元と比べた比）
for k, (sn, vn) in chains.items():
    a, b, c = P(FS, si, sn); A, B, C = P(FV, vi, vn)
    vs = np.linalg.norm(np.diff(c, axis=0), axis=1) * fps
    vv = np.linalg.norm(np.diff(C, axis=0), axis=1) * fps
    r = vv / (vs + 5.0)
    print('%-6s end-effector speed ratio vrm/src: p50 %.2f p95 %.2f max %.2f (at frame %d)' % (k, np.median(r), np.percentile(r, 95), r.max(), int(np.argmax(r))))
