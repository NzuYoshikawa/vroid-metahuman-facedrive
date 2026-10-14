# 調整パラメーター一覧（個別に微調整できる値の場所）

2026-10-14。値を直したら、右の「反映」のコマンドを実行する。すべてこのフォルダで、PowerShell から実行。
`.ps1` は ASCII のみ（Windows PowerShell 5.1 は BOM なし UTF-8 を CP932 として読む）。

## 1. 顔（表情）

| ファイル | 何を決めるか | 主な項目 | 反映 |
|---|---|---|---|
| `mapping_v2.json` | MetaHuman の顔コントロール → VRoid の表情への割り当て | `targets`（重みの和・gate）、`visemes`（開口量×5母音の配分）、`auto_norm`（まばたきの下駄） | `.\apply_params.ps1 -Only face` |
| `face_tuning.json` | 表情ごとの最終調整 | `expression_gain`（全体）、`smooth_frames`、`morphs.<Fcl_*>.gain / offset / min / max` | 同上 |
| `head_params.json` | 頭の回転 | `nod_gain`・`turn_gain`（利得）、`nod_sign`・`turn_sign`（向きの反転）、`neck_share`（首に配る割合）、`max_deg` | `.\apply_params.ps1 -Only face` |

- 口が小さい → `Fcl_MTH_A` などの `gain` を上げる。口が動きすぎる → 下げる。
- 目の閉じ方 → `Fcl_EYE_Close_L/R` の `gain`／`mapping_v2.json` の `auto_norm`。
- ちらつき → `face_tuning.json` の `smooth_frames` を 3 に。

## 2. 髪・服の揺れ

| ファイル | 何を決めるか | 主な項目 | 反映 |
|---|---|---|---|
| `spring_params.json` | 揺れやすさ・当たりの大きさ | `sway`（全体）、`groups.hair/skirt/other`（`sway`・`stiffness_scale`・`drag_scale`・`gravity_scale`・`hit_radius_scale`）、`overrides[]`（骨名の部分一致で個別）、`colliders[]`（体の当たり球の半径） | `.\apply_params.ps1 -Only spring` |

- 現在値: 全体 3.0／髪 1.5／裾 0.3＋`hit_radius_scale` 2.0／その他 1.0。
- 個別の揺れ物の例: `"overrides": [{"match": "CoatSkirtBack_01", "sway": 0.2, "hit_radius_scale": 2.5}]`
- 元の値は `spring_params_original.json`（常にこれに対する倍率で、何度実行しても累積しない）。

## 3. 体の動き

| ファイル | 何を決めるか | 主な項目 | 反映 |
|---|---|---|---|
| `ground_params.json` | 腰の持ち上げによる接地補正（マネキン系の旧方式） | `strength`、`smooth_frames`（`smooth_frames_by_anim`）、`prevent_sink_only`、`float_blend` | `.\apply_params.ps1 -Only ground` |
| `body_fix_params.json` | 足の沈み（脚 IK）と手の貫通（押し出し） | `foot_ik`、`hand_push`、`torso_radius_cm`・`thigh_radius_cm`・`head_radius_cm`、`hand_margin_cm`、`strength`、`per_anim`（動きごとに上書き） | `.\apply_params.ps1 -Only bodyfix -Set mixamo`（または `mannequin`） |

- `per_anim` の例: `"per_anim": {"gangnam_style": {"strength": 0.8, "hand_margin_cm": 2.0}}`

## 4. リターゲット（コードに埋め込み・必要時のみ）

- 「Run IK Rig」は無効（`ue_mixamo_retarget.py`、`ue_body_retarget_mannequin.py`）。有効にすると膝・肘が反転して手足が崩れる。
- 目標の IK Rig は `IK_v4u_1130_Mannequin`（マネキン形式）。

## 5. 値を試す流れ

1. JSON を直す → 2. `apply_params.ps1` で反映 → 3. UE で `LS_*`（Level Sequence）を再生して確認。
   確認用の書き出し（コマンドライン）は `README.md` の 5e・5h 節。
