"""左＝元の演技（撮影した元の動画）、右＝VRoid。音声つき。通常画質（EEVEE）。"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import subprocess, cv2, numpy as np, os
import imageio_ffmpeg

import sys
# 使い方: python -I make_side_by_side.py [MOV WAV RENDER_DIR OUT_MP4 FRAMES]
ROOT = _HERE
A = sys.argv[1:]
MOV = A[0]
WAV = A[1]
RENDER = A[2] if len(A) > 2 else os.path.join(ROOT, 'render_bl2')
out = A[3] if len(A) > 3 else os.path.join(ROOT, 'preview_side_by_side.mp4')
N = int(A[4]) if len(A) > 4 else 874
H = 720
tmp = os.path.join(ROOT, '_tmp_sbs2.mp4')

cap = cv2.VideoCapture(MOV)
vw = None
for i in range(N):
    ok, a = cap.read()
    if not ok:
        break
    a = cv2.resize(a, (int(a.shape[1] * H / a.shape[0]), H))
    b = cv2.imread(os.path.join(RENDER, 'f%04d.png' % i))
    b = cv2.resize(b, (H, H))
    cv2.putText(a, 'original', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(b, 'VRoid v2  f%04d' % i, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 40, 40), 2)
    fr = np.hstack([a, b])
    if vw is None:
        vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), 30.0, (fr.shape[1], fr.shape[0]))
    vw.write(fr)
vw.release()
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, '-y', '-i', tmp, '-i', WAV, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-crf', '18', '-c:a', 'aac', '-shortest', out], check=True, capture_output=True)
print('done', out, round(os.path.getsize(out) / 1e6, 1), 'MB')
