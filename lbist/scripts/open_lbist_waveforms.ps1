param(
    [string]$Case = 'tb_basic_integration_L64_B20',
    [string]$XSim = 'E:/2025.1.1/Vivado/bin/xsim.bat'
)
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$waveFolder = $null
foreach ($relative in @('Results/Phase2/waveforms', 'Results/Phase3/Basic/waveforms', 'Results/Phase3/Swap/waveforms', 'Results/Phase3/Moving/waveforms', 'Results/Phase3/Comparison/waveforms')) {
    $candidate = Join-Path $repoRoot $relative
    foreach ($tag in @($Case, ($Case + '_N4'))) {
        if (Test-Path -LiteralPath (Join-Path $candidate ($tag + '.wdb'))) { $waveFolder = $candidate; $Case = $tag; break }
    }
    if ($null -ne $waveFolder) { break }
}
if ($null -eq $waveFolder) { throw 'Wave database missing; run generate_phase3_waveforms.tcl for Phase 3 or generate_waveforms.tcl for legacy captures.' }
$database = Join-Path $waveFolder ($Case + '.wdb')
$layout = Join-Path $waveFolder ($Case + '.wcfg')
if (-not (Test-Path -LiteralPath $layout)) { throw 'Saved waveform layout is missing.' }
# Static database viewer: no simulation rebuild and no verification report writes.
Push-Location -LiteralPath $waveFolder
try { & $XSim $database -gui -view $layout } finally { Pop-Location }
