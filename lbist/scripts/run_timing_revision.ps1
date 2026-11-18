param(
 [string]$Vivado = 'E:/2025.1.1/Vivado/bin/vivado.bat',
 [int]$Mult = 8,
 [int]$Divide = 82
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot '../..')
$revision = Join-Path (Get-Location) 'Results/Final/FPGA_Analysis/Timing_Closure'
New-Item -ItemType Directory -Force -Path $revision | Out-Null
$tag = "m${Mult}_d${Divide}"
function Invoke-NativeStage([string]$Script, [string]$LogName, [string[]]$StageArgs) {
 & $Vivado -mode batch -nolog -nojournal -source "lbist/scripts/$Script" -tclargs @StageArgs *> (Join-Path $revision $LogName)
 if ($LASTEXITCODE -ne 0) { throw "Vivado failed: $Script. See $LogName" }
}
function Invoke-PythonStage([string]$Script) {
 & python "lbist/scripts/$Script" $Mult $Divide
 if ($LASTEXITCODE -ne 0) { throw "Python failed: $Script" }
}
foreach ($config in 'baseline','scan_enabled','full_lbist') {
 Invoke-NativeStage 'run_timing_closure.tcl' "${config}_${tag}_console.log" @($config,$Mult,$Divide)
 Invoke-NativeStage 'close_timing_io.tcl' "close_${config}_${tag}.log" @($config,$Mult,$Divide)
}
Invoke-PythonStage 'prepare_timing_verification.py'
Invoke-NativeStage 'run_timing_verification.tcl' "verification_${tag}.log" @($Mult,$Divide)
Invoke-PythonStage 'audit_timing_verification.py'
Invoke-NativeStage 'verify_timing_waveforms.tcl' 'waveform_audit.log' @($Mult,$Divide)
Invoke-PythonStage 'prepare_timing_power.py'
Invoke-NativeStage 'run_timing_power.tcl' "power_${tag}.log" @($Mult,$Divide)
Invoke-PythonStage 'build_timing_report.py'
& python lbist/scripts/build_final_pdf.py
if ($LASTEXITCODE -ne 0) { throw 'PDF build failed' }
Write-Host 'Revision exported. Inspect TimingClean and annotation coverage; process completion alone is not timing closure.'
