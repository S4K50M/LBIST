param(
    [string]$Case = 'tb_basic_integration_L64_B20',
    [string]$XSim = 'E:/2025.1.1/Vivado/bin/xsim.bat'
)
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$waveFolder = $null
foreach ($relative in @('Results/Phase2/waveforms', 'Results/Phase3/Basic/waveforms')) {
    $candidate = Join-Path $repoRoot $relative
    if (Test-Path -LiteralPath (Join-Path $candidate ($Case + '.wdb'))) { $waveFolder = $candidate; break }
}
if ($null -eq $waveFolder) { throw 'Wave database missing; run generate_waveforms.tcl first.' }
$database = Join-Path $waveFolder ($Case + '.wdb')
$layout = Join-Path $waveFolder ($Case + '.wcfg')
if (-not (Test-Path -LiteralPath $layout)) { throw 'Saved waveform layout is missing.' }
# Static database viewer: no simulation rebuild and no verification report writes.
Push-Location -LiteralPath $waveFolder
try { & $XSim $database -gui -view $layout } finally { Pop-Location }
