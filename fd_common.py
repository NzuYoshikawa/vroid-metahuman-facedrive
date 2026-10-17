"""モデルごとの違いを吸収する共通の補助（UE 内 Python 用）。

- bones(): VRM の人型ボーン対応表（VM_*_VrmMeta の humanoid_bone_table）から、スケルトン上の骨の名前を引く。
           VRoid Studio 以外のモデル（骨の名前が違うモデル）でも動かすため。
- model_scale(): モデルの高さ（メッシュのバウンズ）を、検証したモデルとの比で返す。cm で固定していた値の補正に使う。
"""
import unreal

REF_HEIGHT_CM = 140.2         # 最初に検証したモデル（v4u_1130）の頭の骨の高さ（基準姿勢、cm）。補正半径などの基準

# VRoid Studio 標準の名前（対応表に無いときの既定値）
_VROID = {
    'hips': 'J_Bip_C_Hips', 'spine': 'J_Bip_C_Spine', 'chest': 'J_Bip_C_Chest', 'upper_chest': 'J_Bip_C_UpperChest',
    'neck': 'J_Bip_C_Neck', 'head': 'J_Bip_C_Head',
    'l_upper_leg': 'J_Bip_L_UpperLeg', 'l_lower_leg': 'J_Bip_L_LowerLeg', 'l_foot': 'J_Bip_L_Foot', 'l_toes': 'J_Bip_L_ToeBase',
    'r_upper_leg': 'J_Bip_R_UpperLeg', 'r_lower_leg': 'J_Bip_R_LowerLeg', 'r_foot': 'J_Bip_R_Foot', 'r_toes': 'J_Bip_R_ToeBase',
    'l_upper_arm': 'J_Bip_L_UpperArm', 'l_lower_arm': 'J_Bip_L_LowerArm', 'l_hand': 'J_Bip_L_Hand',
    'r_upper_arm': 'J_Bip_R_UpperArm', 'r_lower_arm': 'J_Bip_R_LowerArm', 'r_hand': 'J_Bip_R_Hand',
    'l_eye': 'J_Adj_L_FaceEye', 'r_eye': 'J_Adj_R_FaceEye',
}
# 内部のキー → VRM の humanoid ボーン名
_VRM = {
    'hips': 'hips', 'spine': 'spine', 'chest': 'chest', 'upper_chest': 'upperChest', 'neck': 'neck', 'head': 'head',
    'l_upper_leg': 'leftUpperLeg', 'l_lower_leg': 'leftLowerLeg', 'l_foot': 'leftFoot', 'l_toes': 'leftToes',
    'r_upper_leg': 'rightUpperLeg', 'r_lower_leg': 'rightLowerLeg', 'r_foot': 'rightFoot', 'r_toes': 'rightToes',
    'l_upper_arm': 'leftUpperArm', 'l_lower_arm': 'leftLowerArm', 'l_hand': 'leftHand',
    'r_upper_arm': 'rightUpperArm', 'r_lower_arm': 'rightLowerArm', 'r_hand': 'rightHand',
    'l_eye': 'leftEye', 'r_eye': 'rightEye',
}

_cache = {}


def humanoid_table(meta_path):
    """VRM のボーン名（hips, leftFoot ...）→ スケルトン上の骨の名前。取得できなければ空。"""
    try:
        meta = unreal.load_asset(meta_path)
        t = getattr(meta, 'humanoid_bone_table')
        return {str(k): str(v) for k, v in t.items()}
    except BaseException as e:
        print('FD humanoid table: unavailable (%s)' % type(e).__name__)
        return {}


def bones(meta_path):
    """骨の名前の辞書。対応表を優先し、無いものは VRoid Studio の名前で補う（補ったものは表示する）。"""
    if meta_path in _cache:
        return _cache[meta_path]
    table = humanoid_table(meta_path)
    out, filled = {}, []
    for key, vrm in _VRM.items():
        name = table.get(vrm)
        if not name and key == 'upper_chest':
            name = table.get('chest')            # upperChest は VRM の任意の骨。無ければ chest で代用
        if not name:
            name = _VROID[key]
            filled.append(key)
        out[key] = name
    if table:
        print('FD bones: humanoid table %d entries; defaulted: %s' % (len(table), ','.join(filled) or '-'))
    else:
        print('FD bones: no humanoid table -> VRoid Studio names')
    _cache[meta_path] = out
    return out


def model_height_cm(mesh, pose_anim_path=None, head_bone='J_Bip_C_Head'):
    """頭の骨の高さ（基準姿勢、cm）。メッシュのバウンズは、取り込み方で変わるため使わない。"""
    key = ('h', pose_anim_path, head_bone)
    if key in _cache:
        return _cache[key]
    h = None
    try:
        a = unreal.load_asset(pose_anim_path)
        o = unreal.AnimPoseEvaluationOptions()
        o.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
        p = unreal.AnimPoseExtensions.get_anim_pose_at_time(a, 0.0, o)
        h = float(unreal.AnimPoseExtensions.get_bone_pose(p, head_bone, unreal.AnimPoseSpaces.WORLD).translation.z)
    except BaseException as e:
        print('FD height from pose failed (%s); using mesh bounds' % type(e).__name__)
    if h is None:
        h = 2.0 * float(mesh.get_bounds().box_extent.z) * (REF_HEIGHT_CM / 162.05)
    _cache[key] = h
    return h


def model_scale(mesh, pose_anim_path=None, head_bone='J_Bip_C_Head'):
    """検証したモデルの高さに対する、このモデルの高さの比。"""
    return model_height_cm(mesh, pose_anim_path, head_bone) / REF_HEIGHT_CM


def ensure_ik_rig(mesh_path, meta_path, rig_path, root_bone=None):
    """VRM4U の取り込みダイアログと同じ形（マネキン形式）の IK Rig を、VRM の人型ボーン対応表から作る。
    スクリプトから取り込んだ場合（ダイアログなし）は、VRM4U が IK Rig を作らないため、これで補う。
    チェーン名は、リターゲット元（UE マネキン・Mixamo）と自動で対応づけられる名前（Spine, Neck, Head, LeftArm ...）にする。"""
    if unreal.EditorAssetLibrary.does_asset_exist(rig_path):
        return unreal.load_asset(rig_path)
    table = humanoid_table(meta_path)
    if not table:
        raise RuntimeError('VRM の人型ボーン対応表がありません')
    mesh = unreal.load_asset(mesh_path)
    folder, name = rig_path.rsplit('/', 1)
    rig = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    rc = unreal.IKRigController.get_controller(rig)
    rc.set_skeletal_mesh(mesh)

    def add(chain, a, b=None):
        s, e = table.get(a), table.get(b or a)
        if s and e:
            try:
                rc.add_retarget_chain(chain, s, e, '')
                return True
            except BaseException as ex:
                print('FD ik chain failed', chain, type(ex).__name__)
        return False

    if root_bone:
        rc.add_retarget_chain('Root', root_bone, root_bone, '')
    add('Spine', 'spine', 'upperChest' if 'upperChest' in table else 'chest')
    add('Neck', 'neck'); add('Head', 'head')
    for side, S in (('Right', 'right'), ('Left', 'left')):
        add(side + 'Arm', S + 'UpperArm', S + 'Hand')
        add(side + 'Leg', S + 'UpperLeg', S + 'Foot')
        add(side + 'Toe', S + 'Toes')
        add(side + 'Clavicle', S + 'Shoulder')
        for fname, vrm in (('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Pinky', 'Little')):
            add(side + fname, S + vrm + 'Proximal', S + vrm + 'Distal')
        if not add(side + 'Thumb', S + 'ThumbMetacarpal', S + 'ThumbDistal'):
            add(side + 'Thumb', S + 'ThumbProximal', S + 'ThumbDistal')
    if table.get('hips'):
        rc.set_retarget_root(table['hips'])
    unreal.EditorAssetLibrary.save_asset(rig_path)
    print('FD ik rig created', rig_path, 'chains', len(rc.get_retarget_chains()))
    return rig
