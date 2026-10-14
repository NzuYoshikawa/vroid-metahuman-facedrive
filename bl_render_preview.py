"""v2: 変換カーブでVRoidの顔を動かして連番PNGを書き出す（Blender・確認用）。通常画質=EEVEE。
環境変数: FD_FRAMES='0,150' 対象コマ / FD_OUT 出力先 / FD_MORPHS morphs json / FD_RES 解像度 / FD_ENGINE EEVEE|WORKBENCH"""
import os as _os, json as _json
try:
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _HERE = _os.environ.get('FD_ROOT', '.')
_CFG_PATH = _os.path.join(_HERE, 'config.json')
_CFG = _json.load(open(_CFG_PATH, encoding='utf-8')) if _os.path.exists(_CFG_PATH) else {}
import json, math, os
import numpy as np
import bpy
from mathutils import Vector, Matrix

ROOT = _HERE
OUT = os.environ.get('FD_OUT', os.path.join(ROOT, 'render_bl2'))
os.makedirs(OUT, exist_ok=True)
data = json.load(open(os.environ.get('FD_MORPHS', os.path.join(ROOT, 'vrm_curves.json'))))
mh = json.load(open(os.environ.get('FD_MH_CURVES', os.path.join(ROOT, 'mh_curves.json'))))['curves']
fps, nfr = data['fps'], data['frames']
fr = os.environ.get('FD_FRAMES')
frames = [int(x) for x in fr.split(',')] if fr else list(range(min(nfr, 874)))
RES = int(os.environ.get('FD_RES', '720'))
ENGINE = os.environ.get('FD_ENGINE', 'EEVEE')

face = bpy.data.objects['Face']
keys = face.data.shape_keys.key_blocks
morphs = {k: v for k, v in data['morphs'].items() if k in keys}

def series(name):
    c = mh.get(name)
    t = np.arange(nfr) / fps
    if not c or not c['t']:
        return np.zeros(nfr)
    return np.interp(t, c['t'], c['v'])
nod = series('HeadYaw')     # +で下向き（動画との相関から推定）
turn = series('HeadRoll')   # +で画面右（同上）

arm = bpy.data.objects['Armature']
pb = arm.pose.bones['J_Bip_C_Head']
rest = arm.data.bones['J_Bip_C_Head'].matrix_local.copy()
hpos = rest.translation.copy()
print('head joint (armature space):', hpos)

sc = bpy.context.scene
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.image_settings.file_format = 'PNG'
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
if ENGINE == 'EEVEE':
    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.taa_render_samples = 16
    except Exception:
        pass
else:
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'TEXTURE'
w = sc.world or bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.55, 0.55, 0.55, 1)
    bg.inputs[1].default_value = 1.0

for o in bpy.data.objects:
    if o.type == 'EMPTY':
        o.hide_render = True

bb = [face.matrix_world @ Vector(c) for c in face.bound_box]
ctr = sum(bb, Vector()) / 8
cd = bpy.data.cameras.new('Cam'); cd.lens = 85
cam = bpy.data.objects.new('Cam', cd)
sc.collection.objects.link(cam)
cam.location = ctr + Vector((0, -1.1, 0.02))
cam.rotation_euler = (math.radians(90), 0, 0)
sc.camera = cam

# 正面からの柔らかい光
ld = bpy.data.lights.new('Key', 'SUN'); ld.energy = 3.0
lo = bpy.data.objects.new('Key', ld); sc.collection.objects.link(lo)
lo.rotation_euler = (math.radians(60), 0, math.radians(15))

for f in frames:
    for k in keys:
        if k.name != 'Basis':
            k.value = 0.0
    for name, vals in morphs.items():
        keys[name].value = float(vals[min(f, len(vals) - 1)])
    R = Matrix.Rotation(math.radians(turn[min(f, nfr - 1)]), 4, 'Z') @ Matrix.Rotation(math.radians(nod[min(f, nfr - 1)]), 4, 'X')
    pb.matrix = Matrix.Translation(hpos) @ R @ Matrix.Translation(-hpos) @ rest
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, 'f%04d.png' % f)
    bpy.ops.render.render(write_still=True)
print('rendered', len(frames), 'engine', sc.render.engine)
