# vroid-metahuman-facedrive

MetaHuman Animator の顔アニメーションを、VRoid（VRM）キャラクターの表情に変換して、Unreal Engine 5.8 で動かすためのスクリプトと設定の一式です。
あわせて、体の動き（UE マネキン／Mixamo）のリターゲット、髪・服の揺れの調整、足の沈み・手の貫通の補正を含みます。

English summary: Python scripts and JSON parameters for UE 5.8 that convert MetaHuman Animator face curves into the standard VRoid
(`Fcl_*`) expressions, bake them as an AnimSequence on a VRM4U-imported VRoid skeleton, add head rotation to the neck/head bones,
retarget Mixamo / UE Mannequin body animation (with the "Run IK Rig" op disabled, which otherwise flips knees and elbows),
and tune hair/skirt spring bones, foot sinking and hand penetration through JSON files. License: CC0.

## 含まれるもの

| 区分 | ファイル | 内容 |
|---|---|---|
| 顔 | `ue_export_face_curves.py`, `apply_mapping.py`, `mapping_v2.json`, `face_tuning.json` | Performance → 顔カーブの書き出し → VRoid 標準表情（`Fcl_*`）へ変換、表情ごとの利得 |
| 顔 | `ue_bake_vrm_anim.py`, `ue_head_rotation.py`, `head_params.json` | VRoid 用 AnimSequence へのベイク、頭の回転を首・頭の骨へ |
| 揺れ | `ue_spring_params.py`, `spring_params.json` | 髪・服の揺れやすさ、当たり半径、コライダー（VRM のスプリングボーンの値を倍率で調整） |
| 体 | `ue_body_retarget_mannequin.py`, `ue_mixamo_import.py`, `ue_mixamo_anims.py`, `ue_mixamo_retarget.py` | UE マネキン／Mixamo の動きを VRoid へ |
| 体 | `ue_ground_fix_*.py`, `ue_body_fix.py`, `ground_params.json`, `body_fix_params.json` | 足の沈み（脚 IK）・手の貫通（押し出し）の補正 |
| 確認 | `ue_make_demo_level.py`, `ue_make_sequence.py`, `ue_make_demo_anim.py`, `bl_render_preview.py`, `make_side_by_side.py`, `analyze_limbs.py` | 再生用シーケンス、確認用の描画、手足の崩れの診断 |
| 実行 | `run_pipeline.ps1`, `apply_params.ps1` | 一括実行、パラメーターの反映 |
| 文書 | `PARAMETERS.md` | 調整できる値の一覧 |

## 含まれないもの

- MetaHuman のアセット（Identity、Performance、キャラクター）。ご自身の撮影と解析で作ってください。
- Mixamo の FBX（再配布できません）。ご自身で Mixamo から入手してください。
- VRoid モデル（VRM）。モデルごとの利用条件に従ってください。
- VRM4U（MIT ライセンス）。ご自身で導入してください: https://github.com/ruyo/VRM4U

## 動作確認の環境

- Unreal Engine 5.8、VRM4U（5.8 用ビルド）、Windows 11、Blender 5.2（確認用の描画のみ）。
- UE 5.7 は、スクリプトを書くときに互換を意識していますが、実機では未確認です。
- VRoid Studio 標準の `Fcl_*` 表情を持つモデルで確認しています（ARKit 名の表情を持つモデルは、VRM4U 自身の機能で足ります）。

## 使い方（概要）

1. `config.example.json` を `config.json` にコピーし、プロジェクトの名前を書く（VRM4U が取り込み時に付ける名前、Performance のパス）。
2. UE で VRM を取り込む（Content Browser へドロップ。コマンドラインの自動実行では、ダイアログが出て中断します）。
3. MetaHuman Animator で Identity と Performance を作り、Process まで実行する。
4. 顔: `ue_export_face_curves.py` → `apply_mapping.py` → `ue_bake_vrm_anim.py` → `ue_head_rotation.py`
5. 揺れ・体: `ue_spring_params.py`、`ue_mixamo_*.py`、`ue_ground_fix_*.py`、`ue_body_fix.py`

UE のスクリプトは、次の形で実行します。

```
UnrealEditor-Cmd.exe <プロジェクト>.uproject -run=pythonscript -script="<スクリプト>" -unattended -nosplash -stdout -FullStdOutLogOutput
```

詳しい手順と、つまずいた点は、記事（yoshikawastudio.com）にまとめています。調整できる値は `PARAMETERS.md` を見てください。

## 再現確認について

新規プロジェクトで、このリポジトリを clone して、次の手順を実際に実行して確認しています（記事に画面を載せています）。
VRM の取り込み → `build_lists.py` → 顔カーブの書き出し → 変換 → ベイク → 頭の回転 → 揺れ → Mixamo の取り込み・リターゲット → 接地補正 → 手足の補正 → デモ用レベル・シーケンス → UE での書き出し。
UE マネキンの動き（`ue_body_retarget_mannequin.py`、`ue_ground_fix_mannequin.py`、`FD_SET=mannequin` の `ue_body_fix.py`）も、同じ方法で確認しています。

## 既知の限界

- 手のずれが、元の動きに対して 12〜20%（腕の比率の違い）。肘のめり込みと、服（上着の裾など）との干渉は補正していません。
- 脚を大きく上げる姿勢で、スカートの帯の間に隙間が出ることがあります（当たり半径で軽減）。
- MetaHuman の `HeadYaw/Pitch/Roll` は、名前と実際の動きが一致しません。映像の動きとの相関から、`HeadYaw`＝うなずき、`HeadRoll`＝左右の向きと割り当てています（`HeadPitch` は未使用）。
- 目線は未対応（VRoid の目に視線用の形状がないため）。

## ライセンス

CC0 1.0（パブリックドメイン相当）。`LICENSE` を参照してください。
依存するソフトウェア（Unreal Engine、MetaHuman、VRM4U、Mixamo、VRoid Studio）は、それぞれの利用条件に従ってください。
