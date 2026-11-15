# Source in a fresh Vivado GUI Tcl console. Override WAVEFORM_CASE if desired.
if {![info exists ::WAVEFORM_CASE]} {set ::WAVEFORM_CASE tb_basic_integration_L64_B20}
set wave_root [file normalize [file join [file dirname [info script]] ../..]]
set wave_folder ""
foreach relative {Results/Phase2/waveforms Results/Phase3/Basic/waveforms} {
    set candidate [file join $wave_root $relative]
    if {[file exists [file join $candidate $::WAVEFORM_CASE.wdb]]} {set wave_folder $candidate; break}
}
if {$wave_folder eq ""} {error "Waveform database is missing; run generate_waveforms.tcl first."}
open_wave_database [file join $wave_folder $::WAVEFORM_CASE.wdb]
open_wave_config [file join $wave_folder $::WAVEFORM_CASE.wcfg]
puts "Opened $::WAVEFORM_CASE; full trace in WDB, initial 300 ns shown by the saved layout."
