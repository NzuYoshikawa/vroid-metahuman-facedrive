# VRoid x MetaHuman face drive: run one take end to end.
# NOTE: keep this file ASCII-only (Windows PowerShell 5.1 reads BOM-less UTF-8 as CP932).
# Usage:
#   .\run_pipeline.ps1 -Tag take5 -Perf /Game/MetaHumans/<name>/MHA/<PerformanceAsset> `
#       -Mov <capture folder>\<file>.mov -Wav <wav of the same take> -Frames 874
# IMPORTANT: -Mov must be the footage the Performance actually used (footage_capture_data in UE).
param(
  [Parameter(Mandatory)][string]$Tag,
  [Parameter(Mandatory)][string]$Perf,
  [Parameter(Mandatory)][string]$Mov,
  [Parameter(Mandatory)][string]$Wav,
  [int]$Frames = 874,
  [string]$Mapping = "mapping_v2.json",
  [string]$Blend = $env:FD_BLEND,
  [string]$Vrm = $env:FD_VRM,
  [string]$Project = $env:FD_PROJECT,
  [string]$UE = "C:\Program Files\Epic Games\UE_5.8",
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$mhJson = Join-Path $here "mh_${Tag}_curves.json"
$morphs = Join-Path $here "vrm_${Tag}_morphs.json"
$ueCmd = "$UE\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

Write-Host "1/6 UE: export face curves from the Performance"
$env:FD_PERF = $Perf; $env:FD_MH_JSON = $mhJson; $env:FD_MH_ANIM_NAME = "AS_${Tag}_face"
& $ueCmd $Project -run=pythonscript -script="$here\ue_export_face_curves.py" -unattended -nosplash -stdout -FullStdOutLogOutput *> "$here\ue_export_${Tag}.log"
if (-not (Test-Path $mhJson)) { throw "export failed: see ue_export_${Tag}.log" }

Write-Host "2/6 refresh name lists and check the mapping"
python -I build_lists.py $UE $Vrm
python -I check_mapping.py $Mapping

Write-Host "3/6 apply the mapping (to VRoid expression curves)"
python -I apply_mapping.py $mhJson $Mapping $morphs

Write-Host "4/6 UE: bake an AnimSequence for the VRoid skeleton"
$env:FD_MORPHS = $morphs; $env:FD_MH_CURVES = $mhJson; $env:FD_ANIM_NAME = "AS_vrm_${Tag}"
& $ueCmd $Project -run=pythonscript -script="$here\ue_bake_vrm_anim.py" -unattended -nosplash -stdout -FullStdOutLogOutput *> "$here\ue_bake_${Tag}.log"

Write-Host "4b/6 UE: add head rotation to the neck/head bones (adopted setting)"
$env:FD_HEAD_ANIM = "/Game/FaceDrive/AS_vrm_${Tag}"; $env:FD_HEAD_OUT = "/Game/FaceDrive/AS_vrm_${Tag}_Head"; $env:FD_HEAD_T0 = "0"; $env:FD_MH_CURVES = $mhJson
& $ueCmd $Project -run=pythonscript -script="$here\ue_head_rotation.py" -unattended -nosplash -stdout -FullStdOutLogOutput *> "$here\ue_head_${Tag}.log"
Remove-Item Env:FD_HEAD_ANIM, Env:FD_HEAD_OUT, Env:FD_HEAD_T0 -ErrorAction SilentlyContinue

Write-Host "5/6 Blender: preview frames (normal quality)"
$out = Join-Path $here "render_${Tag}"
$env:FD_MORPHS = $morphs; $env:FD_OUT = $out; $env:FD_MH_CURVES = $mhJson
& $Blender -b $Blend --python "$here\bl_render_preview.py" *> "$here\bl_render_${Tag}.log"

Write-Host "6/6 side-by-side video (left = footage, right = VRoid)"
python -I make_side_by_side.py $Mov $Wav $out (Join-Path $here "preview_${Tag}.mp4") $Frames
Write-Host "done: preview_${Tag}.mp4"
