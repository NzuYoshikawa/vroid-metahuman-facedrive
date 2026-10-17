"""全手順を、UE のエディタの中で順に実行する（PowerShell もコマンドも不要）。

使い方（どちらか）
  A. エディタのメニュー Tools > Execute Python Script... で、このファイルを選ぶ。
  B. run_all.bat をダブルクリックする（エディタが開いて、実行後に閉じる）。
実行する前に、config.json に次の2つを書いておく。
  "vrm"       取り込む VRM ファイルのパス
  "vroid_dir" 取り込み先（例 "/Game/Model/"）
任意:
  "mixamo_dir"   Mixamo の FBX を置いたフォルダ（T-Pose.fbx と動きの FBX）。無ければ Mixamo の手順は飛ばす
  "performance"  MetaHuman Performance のアセットのパス。mh_curves.json が無いときに、顔カーブを書き出す
  "env"          各スクリプトの環境変数（FD_*）の既定値
特定の手順だけ実行したいときは、config.json の "steps" に、手順名のリストを書く（例 ["check", "spring"]）。
結果は run_all_report.json にも書く。"""
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

import json, os, runpy, sys, time, traceback
import unreal

os.environ['FD_NO_QUIT'] = '1'          # 各スクリプトの終了処理（エディタを閉じる）を止める
for _k, _v in (_CFG.get('env') or {}).items():
    os.environ.setdefault(str(_k), str(_v))

DEFAULT_ENV = {
    'FD_HEAD_ANIM': '/Game/FaceDrive/AS_vrm_face', 'FD_HEAD_OUT': '/Game/FaceDrive/AS_vrm_face_Head', 'FD_HEAD_T0': '0',
    'FD_DEMO': '/Game/FaceDrive/AS_Mixamo_Talking_Face', 'FD_T0': '0',
    'FD_SEQ_NAME': 'LS_Demo', 'FD_ANIM': '/Game/FaceDrive/AS_Mixamo_Talking_Face', 'FD_REPEAT': '1',
}
for _k, _v in DEFAULT_ENV.items():
    os.environ.setdefault(_k, _v)


def asset(path):
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def list_assets(folder):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        reg.scan_paths_synchronous([folder], True)
    except BaseException:
        pass
    return [str(a.asset_name) for a in reg.get_assets_by_path(folder, recursive=False)]


def run_script(name, argv=None):
    path = os.path.join(_HERE, name)
    old_argv = list(sys.argv)
    sys.argv = [path] + (argv or [])
    try:
        runpy.run_path(path, run_name='__main__')
    finally:
        sys.argv = old_argv


def reload_cfg():
    global _CFG
    _CFG = json.load(open(_CFG_PATH, encoding='utf-8-sig'))
    return _CFG


def have_model():
    c = reload_cfg()
    return bool(c.get('mesh')) and asset(c['vroid_dir'] + c['mesh'])


STEPS = []


def step(name, fn, when=None, why=''):
    STEPS.append((name, fn, when, why))


def script(fname, argv=None, env=None, pre=None):
    def f():
        for k, v in (env or {}).items():
            os.environ[k] = v
        if pre:
            pre()
        run_script(fname, argv)
    return f


def pick_body():
    names = [n for n in list_assets('/Game/FaceDrive/Mixamo') if n.endswith('_Fixed')]
    if not names:
        return
    pick = next((n for n in names if 'alk' in n), names[0])
    os.environ.setdefault('FD_BODY', '/Game/FaceDrive/Mixamo/' + pick)
    print('FD demo body:', os.environ['FD_BODY'])


step('import', script('ue_import_vrm.py'), when=lambda: bool(_CFG.get('vrm')) and not have_model(),
     why='config.json の vrm が未指定、または取り込み済み')
step('check', script('ue_check_model.py'), when=have_model, why='モデルが未取り込み')
step('export_face', script('ue_export_face_curves.py'),
     when=lambda: bool(_CFG.get('performance')) and not os.path.exists(os.path.join(_HERE, 'mh_curves.json')),
     why='performance 未指定、または mh_curves.json が既にある')
step('mapping', script('apply_mapping.py'), when=lambda: os.path.exists(os.path.join(_HERE, 'mh_curves.json')),
     why='mh_curves.json が無い')
step('bake', script('ue_bake_vrm_anim.py'), when=lambda: have_model() and os.path.exists(os.path.join(_HERE, 'vrm_curves.json')),
     why='モデル、または vrm_curves.json が無い')
step('head', script('ue_head_rotation.py'), when=lambda: asset(os.environ['FD_HEAD_ANIM']), why='顔のアニメ（ベイク結果）が無い')
step('spring', script('ue_spring_params.py'), when=have_model, why='モデルが無い')
_mx = lambda: bool(_CFG.get('mixamo_dir')) and os.path.isdir(_CFG['mixamo_dir'])
step('mx_import', script('ue_mixamo_import.py'), when=_mx, why='mixamo_dir が未指定')
step('mx_anims', script('ue_mixamo_anims.py', pre=lambda: unreal.SystemLibrary.execute_console_command(
    None, 'Interchange.FeatureFlags.Import.FBX 0')), when=lambda: _mx() and asset('/Game/Mixamo/T-Pose_Skeleton'),
     why='T-Pose が取り込まれていない')
step('mx_retarget', script('ue_mixamo_retarget.py'), when=lambda: have_model() and asset('/Game/Mixamo/T-Pose'), why='Mixamo 未取り込み')
step('mx_ground', script('ue_ground_fix_mixamo.py'), when=lambda: have_model() and asset('/Game/Mixamo/idle'), why='Mixamo の idle が無い')
step('mx_bodyfix', script('ue_body_fix.py', env={'FD_SET': 'mixamo'}), when=lambda: have_model() and asset('/Game/Mixamo/idle'),
     why='Mixamo の idle が無い')
_mq = lambda: have_model() and asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle')
step('mq_retarget', script('ue_body_retarget_mannequin.py'), when=_mq, why='UE マネキンのアニメがプロジェクトに無い')
step('mq_ground', script('ue_ground_fix_mannequin.py'), when=lambda: _mq() and asset('/Game/FaceDrive/Body/VRM_MM_Idle'), why='マネキンの変換結果が無い')
step('mq_bodyfix', script('ue_body_fix.py', env={'FD_SET': 'mannequin'}), when=lambda: _mq() and asset('/Game/FaceDrive/Body/VRM_MM_Idle'),
     why='マネキンの変換結果が無い')
step('demo_anim', script('ue_make_demo_anim.py', pre=pick_body),
     when=lambda: have_model() and any(n.endswith('_Fixed') for n in list_assets('/Game/FaceDrive/Mixamo')),
     why='体の動き（Mixamo の補正結果）が無い')
step('level', script('ue_make_demo_level.py'), when=have_model, why='モデルが無い')
step('sequence', script('ue_make_sequence.py'), when=lambda: asset(os.environ['FD_ANIM']) and asset('/Game/FaceDrive/Demo_VRoid'),
     why='デモ用のアニメ、またはレベルが無い')

only = _CFG.get('steps')
report = {'steps': {}, 'started': time.strftime('%Y-%m-%d %H:%M:%S')}
for name, fn, when, why in STEPS:
    if only and name not in only:
        continue
    try:
        reload_cfg()
        if when is not None and not when():
            report['steps'][name] = {'status': 'skipped', 'why': why}
            print('FD STEP %-12s skipped (%s)' % (name, why))
            continue
    except BaseException as e:
        report['steps'][name] = {'status': 'skipped', 'why': 'check failed: %s' % type(e).__name__}
        print('FD STEP %-12s skipped (check failed: %s)' % (name, type(e).__name__))
        continue
    t0 = time.time()
    try:
        fn()
        report['steps'][name] = {'status': 'ok', 'sec': round(time.time() - t0)}
        print('FD STEP %-12s OK (%.0fs)' % (name, time.time() - t0))
    except SystemExit as e:
        report['steps'][name] = {'status': 'ng', 'error': 'SystemExit: %s' % (e,)}
        print('FD STEP %-12s NG  %s' % (name, e))
    except BaseException as e:
        report['steps'][name] = {'status': 'ng', 'error': '%s: %s' % (type(e).__name__, str(e)[:200])}
        print('FD STEP %-12s NG  %s' % (name, type(e).__name__))
        traceback.print_exc()
    json.dump(report, open(os.path.join(_HERE, 'run_all_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 最後まで到達した印（run_all.bat が、エディタが途中で落ちたかを判断するのに使う）
open(os.path.join(_HERE, 'run_all_done.txt'), 'w', encoding='utf-8').write(time.strftime('%Y-%m-%d %H:%M:%S'))
ok = [k for k, v in report['steps'].items() if v['status'] == 'ok']
ng = [k for k, v in report['steps'].items() if v['status'] == 'ng']
print('FD SUMMARY ok=%d ng=%d skipped=%d  ng_steps=%s' % (len(ok), len(ng), len(report['steps']) - len(ok) - len(ng), ng))
del os.environ['FD_NO_QUIT']
try:
    _cl = str(unreal.SystemLibrary.get_command_line()).lower()
    if '-executepythonscript' in _cl or '-run=pythonscript' in _cl:
        unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
except BaseException:
    pass
