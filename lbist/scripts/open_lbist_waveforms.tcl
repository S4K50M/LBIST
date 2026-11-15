# Source in a fresh Vivado GUI Tcl console. Override WAVEFORM_CASE if desired.
if {![info exists ::WAVEFORM_CASE]} {set ::WAVEFORM_CASE tb_basic_integration_L64_B20}
set wave_root [file normalize [file join [file dirname [info script]] ../..]]
set wave_folder ""
foreach relative {Results/Phase2/waveforms Results/Phase3/Basic/waveforms Results/Phase3/Swap/waveforms Results/Phase3/Moving/waveforms Results/Phase3/Comparison/waveforms} {
    set candidate [file join $wave_root $relative]
    foreach tag [list $::WAVEFORM_CASE [format "%s_N4" $::WAVEFORM_CASE]] {
        if {[file exists [file join $candidate $tag.wdb]]} {
            set wave_folder $candidate; set ::WAVEFORM_CASE $tag; break
        }
    }
    if {$wave_folder ne ""} {break}
}
if {$wave_folder eq ""} {error "Waveform database is missing; run generate_phase3_waveforms.tcl for Phase 3 or generate_waveforms.tcl for legacy captures."}
open_wave_database [file join $wave_folder $::WAVEFORM_CASE.wdb]
open_wave_config [file join $wave_folder $::WAVEFORM_CASE.wcfg]
puts "Opened $::WAVEFORM_CASE; full trace in WDB; the saved layout sets the initial zoom."
