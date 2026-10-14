# MetaHuman のリグで VRoid モデルを動かす 使い方マニュアル（日本語）

このマニュアルは、このリポジトリのスクリプトを使って、MetaHuman Animator で作った顔のアニメーションと、Mixamo／UE マネキンの体の動きを、VRoid（VRM）モデルに当てる手順をまとめたものです。
画面は、このリポジトリを clone した新規の UE 5.8 プロジェクトで、実際にコマンドを実行して撮影しました。

- 流れを1枚で知りたい方は「2. 全体の流れ」を読んでください。
- 値を変えたい方は「5. 調整できる値」を読んでください。
- うまくいかないときは「6. よくある失敗」を読んでください。

---

## 1. 先に知っておく用語

| 用語 | 意味 |
|---|---|
| VRM | VRoid Studio が書き出す、人型キャラクターのファイル形式 |
| VRM4U | VRM を UE に取り込むための、無料のプラグイン（MIT ライセンス） |
| `Fcl_*` | VRoid 標準の表情（モーフ）の名前。口は `Fcl_MTH_A`（あ）など、約56個あります |
| MetaHuman Animator | 動画から MetaHuman の顔のアニメーションを作る、UE の機能 |
| Performance | MetaHuman Animator が解析した結果のアセット。顔のコントロールの時間変化が入っています |
| カーブ | 時間ごとの値の列。表情の強さ（0〜1）を表します |
| AnimSequence | UE のアニメーションのアセット。骨の動きと、カーブが入ります |
| リターゲット | ある骨格の動きを、別の骨格に当てること |
| IK | 手や足の位置から、腕や脚の曲がりを計算する方法 |
| スプリングボーン | 髪や服を、ばね仕掛けで揺らす VRM の仕組み |
| Level Sequence | UE のシーケンス。カメラとアニメを決めて、再生や書き出しに使います |
| `config.json` | プロジェクト固有の名前を書く設定ファイル。スクリプトはこれを読みます |

---

## 2. 全体の流れ

| 順 | やること | 使うもの | 結果 |
|---|---|---|---|
| 1 | VRM を UE に取り込む | UE のエディタ（VRM4U） | `SK_*`、`VM_*_VrmMeta` など |
| 2 | 設定ファイルを書く | `config.json` | 名前の対応 |
| 3 | 顔カーブを書き出す | `ue_export_face_curves.py` | `mh_curves.json` |
| 4 | VRoid の表情に変換する | `apply_mapping.py` | `vrm_curves.json` |
| 5 | AnimSequence にする | `ue_bake_vrm_anim.py` | `AS_vrm_face` |
| 6 | 頭の回転を入れる | `ue_head_rotation.py` | `AS_vrm_face_Head` |
| 7 | 揺れを調整する | `ue_spring_params.py` | VRM メタの値 |
| 8 | 体の動きを当てる | `ue_mixamo_*.py`／`ue_body_retarget_mannequin.py` | `VRM_*` |
| 9 | 足と手を補正する | `ue_ground_fix_*.py`、`ue_body_fix.py` | `VRM_*_Fixed` |
| 10 | 確認する | `ue_make_*.py` | `LS_Demo`、PNG の連番 |

顔（順 3〜6）と体（順 8〜9）は、別々に作って、最後に1つのアニメにまとめます。

---

## 3. 準備

- Unreal Engine 5.8（MetaHuman プラグインを有効にする）
- VRM4U（5.8 用のビルド）を、プロジェクトの `Plugins` に置く
- VRoid Studio で作った VRM（標準の `Fcl_*` 表情を持つもの）
- MetaHuman Animator で、Process まで終えた Performance
- Mixamo の FBX（`T-Pose.fbx` と、動かしたい動き）。Mixamo の規約に従って、ご自身で入手してください
- Python 3 と Git

UE 5.7 は未確認です。

### 3-1. リポジトリを取得する

![step01_git_clone.png](img/step01_git_clone.png)

```
git clone https://github.com/NzuYoshikawa/vroid-metahuman-facedrive
```

### 3-2. VRM を取り込む

エディタを通常起動して、Content Browser の **Import** から VRM を選びます。

> コマンドラインの自動実行（`-unattended`）では、ダイアログが出て取り込みが中断します。

![**VRM Import Options** は既定のまま **Import**](img/step06_vrm_options.png)

![33個のアセットができます](img/step07_content_browser.png)

### 3-3. `config.json` を書く

`config.example.json` を `config.json` にコピーして、書き換えます。

![step08_config_json.png](img/step08_config_json.png)

| 項目 | 意味 | 例 |
|---|---|---|
| `vroid_dir` | VRM を取り込んだ場所 | `/Game/` |
| `mesh` | スケルタルメッシュの名前 | `SK_v4u_1130` |
| `skeleton` | スケルトンの名前 | `SKEL_v4u_1130` |
| `meta` | VRM メタの名前（揺れの値が入っています） | `VM_v4u_1130_VrmMeta` |
| `retargeter` | VRM4U が作るリターゲッタの名前（無ければ自動で作ります） | `RTG_v4u_1130` |
| `ik_rig_mannequin` | VRM4U が作るマネキン形式の IK Rig | `IK_v4u_1130_Mannequin` |
| `face_pose_anim` | 表情のポーズのアニメ | `A_face_v4u_1130` |
| `mh_face_skeleton` | MetaHuman の顔のスケルトン | `/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton` |
| `performance` | Performance アセットのパス | `/Game/MetaHumans/<名前>/MHA/<アセット>` |
| `mixamo_dir` | Mixamo の FBX を置いたフォルダ | `C:\Mixamo` |

---

## 4. 手順

UE のスクリプトは、すべて次の形で実行します（`<スクリプト>` を差し替えます）。PowerShell で、リポジトリのフォルダから実行してください。

```
& "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" <プロジェクト>.uproject -run=pythonscript -script="$PWD\<スクリプト>" -unattended -nosplash -stdout -FullStdOutLogOutput
```

### 4-1. 名前の一覧を作る（初回のみ）

```
python -I build_lists.py "C:\Program Files\Epic Games\UE_5.8" <モデル>.vrm
```

MetaHuman のコントロール 251個と、VRM のモーフ 57個の一覧ができます。

### 4-2. 顔カーブを書き出す

スクリプト: `ue_export_face_curves.py`

![278本、29.1秒、873フレーム](img/step10_export_curves.png)

### 4-3. VRoid の表情に変換する

```
python -I apply_mapping.py mh_curves.json mapping_v2.json vrm_curves.json 30
python -I check_mapping.py mapping_v2.json
```

![対象 20表情、エラー 0](img/step11_apply_mapping.png)

### 4-4. AnimSequence にする

スクリプト: `ue_bake_vrm_anim.py`

![`AS_vrm_face`、22本のカーブ](img/step12_bake.png)

### 4-5. 頭の回転を入れる

```
$env:FD_HEAD_ANIM = "/Game/FaceDrive/AS_vrm_face"
$env:FD_HEAD_OUT  = "/Game/FaceDrive/AS_vrm_face_Head"
$env:FD_HEAD_T0   = "0"
```

スクリプト: `ue_head_rotation.py`

![`VERIFY` の行で、目の骨が指令どおりに動いたことを確認できます](img/step13_head_rotation.png)

![左：撮影した映像、中：顔のみ、右：顔と頭の回転](img/preview_head_compare.gif)

### 4-6. 揺れを調整する

`spring_params.json` の値を書いて、`ue_spring_params.py` を実行します。

![髪 12本、スカート 18本、その他 2本](img/step14_spring.png)

![左：元の揺れ、右：揺れ 3倍](img/preview_sway_compare.gif)

### 4-7. Mixamo の動きを取り込む

1. `mixamo_dir` に、`T-Pose.fbx` と動きの FBX を置く
2. `ue_mixamo_import.py` を実行する（T-Pose とスケルトンができます）

   ![step15_mixamo_import.png](img/step15_mixamo_import.png)

3. 動きの FBX を取り込む。このときだけ、`-ExecCmds` を付けます

```
& "<UnrealEditor-Cmd.exe>" <プロジェクト>.uproject -ExecCmds="Interchange.FeatureFlags.Import.FBX 0" -run=pythonscript -script="$PWD\ue_mixamo_anims.py" -unattended -nosplash -stdout -FullStdOutLogOutput
```

![フォルダ内の動きが、全部取り込まれます](img/step16_mixamo_anims.png)

### 4-8. VRoid にリターゲットする

スクリプト: `ue_mixamo_retarget.py`

![`VRM_` で始まるアニメができます](img/step17_mixamo_retarget.png)

UE マネキンの動きを使う場合は、`ue_body_retarget_mannequin.py` を実行します。

![step25_mannequin_retarget.png](img/step25_mannequin_retarget.png)

### 4-9. 足の沈みと手の貫通を補正する

| 動きの種類 | 接地補正 | 手足の補正 |
|---|---|---|
| Mixamo | `ue_ground_fix_mixamo.py` | `FD_SET=mixamo` で `ue_body_fix.py` |
| UE マネキン | `ue_ground_fix_mannequin.py` | `FD_SET=mannequin` で `ue_body_fix.py` |

![Mixamo の接地補正](img/step18_ground_fix.png)

![Mixamo の手足の補正](img/step19_body_fix.png)

![左：補正前、右：補正後](img/preview_bodyfix_compare.gif)

![step26_mannequin_ground.png](img/step26_mannequin_ground.png)

![UE マネキン](img/step27_mannequin_bodyfix.png)

### 4-10. 確認する

1. 体と顔を、1つのアニメにまとめる（`ue_make_demo_anim.py`。`FD_BODY`、`FD_DEMO`、`FD_T0` で指定）

   ![step20_demo_anim.png](img/step20_demo_anim.png)

2. `ue_make_demo_level.py` で、確認用のレベル `Demo_VRoid` を作る
3. `ue_make_sequence.py` で、Level Sequence を作る（`FD_SEQ_NAME`、`FD_ANIM`、`FD_REPEAT`）
4. エディタで `Demo_VRoid` を開く

   ![step24_editor_demo_level.png](img/step24_editor_demo_level.png)

5. 画像として書き出す

```
UnrealEditor.exe <プロジェクト>.uproject /Game/FaceDrive/Demo_VRoid -game -windowed -ResX=720 -ResY=720 -ForceRes -NoLoadingScreen -NoTextureStreaming -MovieSceneCaptureType=/Script/MovieSceneCapture.AutomatedLevelSequenceCapture -LevelSequence=/Game/FaceDrive/LS_Demo.LS_Demo -MovieFolder=<出力先> -MovieName=vroid -MovieFormat=PNG -MovieFrameRate=30 -NoSplash -unattended
```

> `-NoTextureStreaming` を付けないと、書き出しが始まらず、フレームが1枚も出ません。
> Movie Render Queue は、PIE がすぐ終わるため使えませんでした。

---

## 5. 調整できる値

値を直したら、`apply_params.ps1` で反映します（`-Only face`／`spring`／`ground`／`bodyfix`）。反映したあと、UE で Level Sequence を再生して確認します。
`FD_PROJECT` に、`.uproject` のパスを入れておいてください。

### 5-1. 顔の表情（`face_tuning.json`）

| 項目 | 何が変わるか | 上げると／1以外にすると | 既定値 |
|---|---|---|---|
| `expression_gain` | 全表情の強さ | 全体が大きく動く | 1.0 |
| `smooth_frames` | ちらつきの抑え方 | 大きくすると、動きがなめらかになるが、鈍くなる（3 で 3フレーム平均） | 1 |
| `morphs.<名前>.gain` | その表情だけの強さ | 上げると大きく動く | 1.0 |
| `morphs.<名前>.offset` | その表情の下駄 | 上げると、常にその分だけかかる | 0.0 |
| `morphs.<名前>.min`／`max` | その表情の下限・上限 | `max` を下げると、それ以上は動かない | 0.0／1.0 |

- 口が小さい → `Fcl_MTH_A` などの `gain` を上げる。動きすぎる → 下げる。
- 目の閉じ方 → `Fcl_EYE_Close_L／R` の `gain`、または `mapping_v2.json` の `auto_norm`。
- 変換の対応そのものを変える場合は、`mapping_v2.json` の `targets`（重みの和）、`visemes`（口の開き×あ・い・う・え・お の配分）を編集します。

### 5-2. 頭の回転（`head_params.json`）

| 項目 | 何が変わるか | 既定値 |
|---|---|---|
| `enable` | 頭の回転を入れるか | true |
| `nod_gain` | うなずきの大きさ | 1.0 |
| `turn_gain` | 左右の向きの大きさ | 1.0 |
| `nod_sign`／`turn_sign` | 向きの反転（1 か −1） | 1 |
| `neck_share` | 回転のうち、首に配る割合（0 なら頭だけ） | 0.3 |
| `max_deg` | 回転の上限（度） | 25.0 |

### 5-3. 髪・服の揺れ（`spring_params.json`）

値は、VRM の元の値に対する倍率です（1.0 が元のまま）。元の値は `spring_params_original.json` に保存されるので、何度実行しても累積しません。

| 項目 | 何が変わるか | 上げると | 下げると | 既定値 |
|---|---|---|---|---|
| `sway` | 揺れやすさ（全体） | 大きく揺れる | 揺れが小さい | 3.0 |
| `groups.<名前>.sway` | グループごとの揺れやすさ | 大きく揺れる | 揺れが小さい | 髪 1.5／スカート 0.3／その他 1.0 |
| `stiffness_scale` | 戻る力 | 元の形に戻りやすい | 戻りにくい | 1.0 |
| `drag_scale` | 空気抵抗 | 動きが早く止まる | 長く揺れる | 1.0 |
| `gravity_scale` | 重力 | 下に垂れる | 垂れにくい | 1.0 |
| `hit_radius_scale` | 当たりの半径 | 体に近づきにくい（めり込みと隙間が減る） | 体に近づく | スカート 2.0、他 1.0 |

- グループは、骨名の部分一致で分けます（髪：`Hair`、スカート：`Skirt`／`Coat`／`Cloth`、その他：残り）。
- 個別の揺れ物は、`overrides` に書きます。例: `{"match": "CoatSkirtBack_01", "sway": 0.2, "hit_radius_scale": 2.5}`
- 体のコライダー（球）の半径は、`colliders` に書きます。例: `{"match": "UpperLeg", "radius_scale": 1.2}`

一時的に試すだけなら、次のように指定できます。

```
.\apply_params.ps1 -Only spring -Sway 2.0 -Groups "hair=1.5,skirt=0.3"
```

### 5-4. 接地補正（`ground_params.json`、UE マネキン用）

| 項目 | 何が変わるか | 既定値 |
|---|---|---|
| `strength` | 腰を持ち上げる強さ（0 で補正なし） | 1.0 |
| `smooth_frames` | 補正量の平滑化。大きいと、短い接地が薄まる | 3（Jog は 1） |
| `prevent_sink_only` | true なら、沈みだけを直す | true |
| `sink_tolerance_cm` | この深さまでの沈みは直さない | 0.5 |
| `float_blend` | 浮いた分を、どれだけ直すか（0〜1） | 0.0 |

### 5-5. 足の沈みと手の貫通（`body_fix_params.json`）

| 項目 | 何が変わるか | 既定値 |
|---|---|---|
| `foot_ik` | 足の沈みを、脚の IK で直すか | true |
| `hand_push` | 手の貫通を、押し出しで直すか | true |
| `sink_tolerance_cm` | この深さまでの沈みは直さない | 0.3 |
| `torso_radius_cm`／`thigh_radius_cm`／`head_radius_cm` | 胴・太もも・頭の、手を避ける半径 | 11／8／10 |
| `hand_margin_cm` | 手と体の間に残す余白 | 3.0 |
| `penetration_tolerance_cm` | この深さまでの貫通は直さない | 0.3 |
| `smooth_frames` | 補正量の平滑化 | 3 |
| `strength` | 補正の強さ（0〜1） | 1.0 |
| `per_anim` | 動きごとの上書き | 空 |

例: `"per_anim": {"gangnam_style": {"strength": 0.8, "hand_margin_cm": 2.0}}`

---

## 6. よくある失敗

| 症状 | 原因 | 直し方 |
|---|---|---|
| VRM の取り込みが途中で止まる | `-unattended` では、ダイアログが出る | エディタを通常起動して、Import から取り込む |
| アニメだけの FBX が「nothing to import」になる | UE 5.8 の FBX は、既定で Interchange になる | `-ExecCmds="Interchange.FeatureFlags.Import.FBX 0"` を付けて、`ue_mixamo_anims.py` を実行する |
| 膝や肘が反転して、手足が崩れる | リターゲッタの操作「Run IK Rig」 | スクリプトが自動で無効にします。自分でリターゲッタを作った場合は、無効にする |
| リターゲッタが何も動かさない | 操作の一覧が空 | `add_default_ops()` が必要です（スクリプトは実行済み） |
| 誤差が 25〜45% になる | 目標の IK Rig が、VRM 人型形式になっている | VRM4U が作る、マネキン形式の IK Rig（`ik_rig_mannequin`）を使う |
| 顔だけのアニメで、頭が回らない | 骨のトラックが無い | 現在のスクリプトは、先にトラックを作ります。古い版を使っていないか確認する |
| 画像の書き出しで、フレームが1枚も出ない | テクスチャのストリーミング待ち | `-NoTextureStreaming` を付ける |
| 口の位置が、あごに下がる | `Fcl_MTH_Up`／`Fcl_MTH_Down` を使っている | 使わない（`mapping_v2.json` では、使っていません） |
| 映像と表情がずれて見える | 別のテイクの映像と比べている | Performance が使った映像を、`footage_capture_data` で確認する |
| `.ps1` が構文エラーになる | Windows PowerShell 5.1 は、BOM なしの UTF-8 を CP932 として読む | `.ps1` は ASCII のみで書く |
| スカートの帯の間に隙間が出る | 揺れを強くしたため | `hit_radius_scale` を 2 倍にする |

---

## 7. 限界

- 手のずれが、元の動きに対して 12〜20% あります（VRoid の腕の比率の違い）。
- 肘のめり込みと、服（上着の裾など）との干渉は、補正していません。
- 脚を大きく上げる姿勢で、スカートの隙間が残ることがあります。
- 目線は未対応です（VRoid の目に、視線用の形状がありません）。
- UE 5.8 と、VRM4U の 5.8 用ビルドで確認しています。5.7 は未確認です。

## 8. 配布に含まれないもの

MetaHuman のアセット、Mixamo の FBX、VRoid モデル、VRM4U。それぞれ、ご自身で入手し、各ライセンスに従ってください。
このリポジトリのスクリプトと設定は、CC0 です。
