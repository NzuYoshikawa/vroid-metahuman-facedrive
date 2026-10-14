# Apply the tuned parameter files to the UE assets.
# NOTE: keep this file ASCII-only (Windows PowerShell 5.1 reads BOM-less UTF-8 as CP932).
# Usage:  .\apply_params.ps1                    (spring + ground)
#         .\apply_params.ps1 -Only spring       sway / hit_radius / colliders   (spring_params.json)
#         .\apply_params.ps1 -Only face         expression gains + bake + head  (face_tuning.json, mapping_v2.json, head_params.json)
#         .\apply_params.ps1 -Only ground       hip-lift grounding              (ground_params.json)
#         .\apply_params.ps1 -Only bodyfix      foot IK + hand push-out         (body_fix_params.json)  [-Set mixamo|mannequin]
#         .\apply_params.ps1 -Sway 2.0 -Groups "hair=1.5,skirt=0.3"   (temporary override of the spring JSON)
param(
  [ValidateSet("both","spring","ground","face","bodyfix")][string]$Only = "both",
  [ValidateSet("mixamo","mannequin")][string]$Set = "mixamo",
  [double]$Sway = 0,
  [string]$Groups = "",
  [string]$UE = "C:\Program Files\Epic Games\UE_5.8",
  [string]$Project = $env:FD_PROJECT
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmd = "$UE\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
function RunUE($script, $log) {
  & $cmd $Project -run=pythonscript -script="$here\$script" -unattended -nosplash -stdout -FullStdOutLogOutput *> "$here\$log"
}
if ($Only -eq "both" -or $Only -eq "spring") {
  if ($Sway -gt 0) { $env:FD_SWAY = "$Sway" }
  if ($Groups -ne "") { $env:FD_GROUPS = $Groups }
  RunUE "ue_spring_params.py" "ue_spring_params.log"
  Get-Content "$here\ue_spring_params.log" | Select-String "SPRING group|overrides used" | ForEach-Object { $_.Line.Substring($_.Line.IndexOf("SPRING") + 0) }
  Remove-Item Env:FD_SWAY, Env:FD_GROUPS -ErrorAction SilentlyContinue
}
if ($Only -eq "both" -or $Only -eq "ground") {
  RunUE "ue_ground_fix_mannequin.py" "ue_ground_fix.log"
  Get-Content "$here\ue_ground_fix.log" | Select-String "GROUND " | ForEach-Object { $_.Line.Substring($_.Line.IndexOf("GROUND")) }
}
if ($Only -eq "bodyfix") {
  $env:FD_SET = $Set
  RunUE "ue_body_fix.py" "ue_body_fix_$Set.log"
  Remove-Item Env:FD_SET -ErrorAction SilentlyContinue
  Get-Content "$here\ue_body_fix_$Set.log" | Select-String "FIX " | ForEach-Object { $_.Line.Substring($_.Line.IndexOf("FIX")) }
}
if ($Only -eq "face") {
  python -I "$here\apply_mapping.py" "$here\mh_curves.json" "$here\mapping_v2.json" "$here\vrm_curves.json" 30
  $env:FD_MORPHS = "$here\vrm_curves.json"; $env:FD_MH_CURVES = "$here\mh_curves.json"; $env:FD_ANIM_NAME = "AS_vrm_face"
  RunUE "ue_bake_vrm_anim.py" "ue_bake_face.log"
  $env:FD_HEAD_ANIM = "/Game/FaceDrive/AS_vrm_face"; $env:FD_HEAD_OUT = "/Game/FaceDrive/AS_vrm_face_Head"; $env:FD_HEAD_T0 = "0"
  RunUE "ue_head_rotation.py" "ue_head_face.log"
  Remove-Item Env:FD_MORPHS, Env:FD_MH_CURVES, Env:FD_ANIM_NAME, Env:FD_HEAD_ANIM, Env:FD_HEAD_OUT, Env:FD_HEAD_T0 -ErrorAction SilentlyContinue
  Get-Content "$here\ue_head_face.log" | Select-String "HEAD saved" | ForEach-Object { $_.Line.Substring($_.Line.IndexOf("HEAD")) }
}
