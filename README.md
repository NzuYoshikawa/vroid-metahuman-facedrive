# vroid-metahuman-facedrive

MetaHuman Animator の顔アニメーションを、VRoid（VRM）キャラクターの表情に変換して、Unreal Engine 5.8 で動かすためのスクリプトと設定の一式です。
あわせて、体の動き（UE マネキン／Mixamo）のリターゲット、髪・服の揺れの調整、足の沈み・手の貫通の補正を含みます。

English summary: Python scripts and JSON parameters for UE 5.8 that convert MetaHuman Animator face curves into the standard VRoid
(`Fcl_*`) expressions, bake them as an AnimSequence on a VRM4U-imported VRoid skeleton, add head rotation to the neck/head bones,
retarget Mixamo / UE Mannequin body animation (with the "Run IK Rig" op disabled, which otherwise flips knees and elbows),
and tune hair/skirt spring bones, foot sinking and hand penetration through JSON files. License: CC0.

詳しい使い方は、[日本語マニュアル](docs/MANUAL_ja.md)（手順ごとの画面つき）を見てください。

## 含まれるもの

| 区分 | ファイル | 内容 |
|---|---|---|
| 顔 | `ue_export_face_curves.py`, `apply_mapping.py`（numpy があれば使い、無ければ `fd_mini_np.py`）, `mapping_v2.json`, `face_tuning.json` | Performance → 顔カーブの書き出し → VRoid 標準表情（`Fcl_*`）へ変換、表情ごとの利得 |
| 顔 | `ue_bake_vrm_anim.py`, `ue_head_rotation.py`, `head_params.json` | VRoid 用 AnimSequence へのベイク、頭の回転を首・頭の骨へ |
| 揺れ | `ue_spring_params.py`, `spring_params.json` | 髪・服の揺れやすさ、当たり半径、コライダー（VRM のスプリングボーンの値を倍率で調整） |
| 体 | `ue_body_retarget_mannequin.py`, `ue_mixamo_import.py`, `ue_mixamo_anims.py`, `ue_mixamo_retarget.py` | UE マネキン／Mixamo の動きを VRoid へ |
| 体 | `ue_ground_fix_*.py`, `ue_body_fix.py`, `ground_params.json`, `body_fix_params.json` | 足の沈み（脚 IK）・手の貫通（押し出し）の補正 |
| 確認 | `ue_make_demo_level.py`, `ue_make_sequence.py`, `ue_make_demo_anim.py`, `bl_render_preview.py`, `make_side_by_side.py`, `analyze_limbs.py` | 再生用シーケンス、確認用の描画、手足の崩れの診断 |
| 取り込み・確認 | `ue_import_vrm.py`, `ue_check_model.py`, `fd_common.py` | VRM をダイアログなしで取り込む、モデルが扱える形かの事前チェック、モデルごとの違い（骨の名前・身長）を吸収する共通部分 |
| 実行 | `ue_run_all.py`, `run_all.bat`, `check_model.bat`, `settings.bat` | 全手順を UE のエディタの中で順に実行する（PowerShell 不要。`.bat` をダブルクリック） |
| 実行 | `run_pipeline.ps1`, `apply_params.ps1` | （PowerShell を使う場合）一括実行、パラメーターの反映 |
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

## 使い方（PowerShell を使わない方法）

1. このリポジトリの ZIP をダウンロードして、`C:\FaceDrive\` などの、パスに日本語と空白を含まない場所に展開する（Code ボタン → Download ZIP）。
2. `config.example.json` を `config.json` にコピーして、メモ帳で次を書く。
   - `"vrm"`: 取り込む VRM ファイルのパス
   - `"vroid_dir"`: 取り込み先（例 `"/Game/Model/"`）
   - `"mixamo_dir"`: Mixamo の FBX を置いたフォルダ（任意。`T-Pose.fbx` と動きの FBX）
   - `"performance"`: MetaHuman の Performance アセットのパス（任意。`mh_curves.json` が無いとき、顔カーブを書き出す）
3. `settings.bat` を、メモ帳で開き、UE のフォルダと、プロジェクトの `.uproject` のパスを書く。
4. `run_all.bat` をダブルクリックする。UE のエディタが開き、全手順を順に実行して、閉じる。
5. 各手順の結果は、`run_all_report.json` と `run_all.log` に出る。

エディタを自分で開いて実行する場合は、メニューの **Tools ＞ Execute Python Script...** で `ue_run_all.py` を選ぶ（手順 4 の代わり）。
1つの手順だけを実行する場合は、同じメニューで、その手順のスクリプトを選ぶ。

特定の手順だけを実行するには、`config.json` に `"steps": ["check", "spring"]` のように書く。
手順の名前は、`import`、`check`、`export_face`、`mapping`、`bake`、`head`、`spring`、`mx_import`、`mx_anims`、`mx_retarget`、`mx_ground`、`mx_bodyfix`、`mq_retarget`、`mq_ground`、`mq_bodyfix`、`demo_anim`、`level`、`sequence` です。
条件が合わない手順（Mixamo のフォルダが無い、など）は、自動で飛ばします。

### コマンドで実行する場合

UE のスクリプトは、次の形で実行します（VRM の取り込み `ue_import_vrm.py` だけは、画面部品が要るため、`UnrealEditor.exe <プロジェクト>.uproject -ExecutePythonScript="<スクリプト>"` で実行します）。

```
UnrealEditor-Cmd.exe <プロジェクト>.uproject -run=pythonscript -script="<スクリプト>" -unattended -nosplash -stdout -FullStdOutLogOutput
```

`apply_mapping.py`、`check_mapping.py`、`build_lists.py` は、UE の外でも実行できます（`python -I apply_mapping.py ...`。Python 3 が必要です）。

詳しい手順と、つまずいた点は、記事（yoshikawastudio.com）にまとめています。調整できる値は `PARAMETERS.md` を見てください。

## 検証済みの範囲（モデル）

次の4種類のモデルで、全手順（取り込み、顔、頭、揺れ、Mixamo、UE マネキン、接地・手足の補正、描画の書き出し）を、新規プロジェクトで通しました。

| モデル | 頭の骨の高さ | 揺れ物（房数／関節数） | 結果 |
|---|---|---|---|
| `v4u_1130`（最初に作った基準） | 140 cm | 32／112 | 全手順 完了 |
| `test1130`（同じ VRoid Studio の標準体型） | 142 cm | 22／82 | 全手順 完了 |
| `test251128`（同上） | 143 cm | 21／82 | 全手順 完了 |
| `v4u_1130` を 0.8 倍に取り込み（背が低い） | 112 cm | 32／112 | 全手順 完了 |
| `v4u_1130` を 1.25 倍に取り込み（背が高い） | 175 cm | 32／112 | 全手順 完了 |

- 足の沈みは、どのモデル・どの動きでも、補正後 0.0〜0.3 cm でした（補正前は最大 11.9 cm）。
- 手の貫通は、補正前 最大 10.8 cm が、補正後 最大 2.6 cm になりました（ダンスの一部で残ります）。
- 頭の回転、表情、髪の揺れが、全モデルの書き出し（155フレーム）で見えることを確認しました。

**未検証:** VRoid Studio 以外で作った VRM（骨の名前が違うモデル）、人型でない体型、スカート・髪の無いモデルの揺れの調整。
骨の名前は、VRM の人型ボーン対応表から引く作りにしてありますが、実機では VRoid Studio 製のモデルでしか試していません。
モデルを取り込んだら、まず `check_model.bat`（または `ue_check_model.py`）で、事前チェックを実行してください。

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
