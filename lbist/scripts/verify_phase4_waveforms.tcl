# Extends the established native+portable audit through separate Phase 4 entries.
source [file join [file dirname [file normalize [info script]]] phase4_common.tcl]
set checked 0
foreach item {
    {IF_RF scan_unit_seed12345 tb_reg_IF_RF_scan}
    {PLPF_Integration real_plpf_B20_P1024 tb_if_rf_plpf_integration}
    {Core_Integration core_scan_lwsw tb_core_scan_regression}
} {
    lassign $item group tag top
    set folder [file join $phase4_root Results Phase4 $group waveforms]
    set db [file join $folder $tag.wdb];set cfg [file join $folder $tag.wcfg]
    if {![file exists $db] || [file size $db]==0} {error "Missing native trace: $tag"}
    set f [open $cfg r];set layout [read $f];close $f
    if {![regexp [format {<db_ref path="%s.wdb"} $tag] $layout]} {error "Wrong waveform database reference"}
    open_wave_database $db;open_wave_config $cfg
    set signals {clk scan_enable scan_in scan_out scan_feedback}
    if {$top ne "tb_core_scan_regression"} {lappend signals q rst ld}
    foreach signal $signals {
        if {[llength [get_objects /$top/$signal]]!=1} {error "Missing captured signal: $signal"}
    }
    close_sim;incr checked;puts "PHASE 4 NATIVE TRACE: PASS -- $tag"
}
set python [phase3_python]
puts [exec $python -E [file join $phase4_scripts phase4_analysis.py] --waves]
puts "PHASE 4 WAVEFORM VALIDATION: PASS ($checked native captures)"
