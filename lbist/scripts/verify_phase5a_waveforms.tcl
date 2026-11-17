# Native availability and independent VCD/SVG behavior are separate checks.
source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
set checked 0
foreach item {
    {Controller controller_L64 tb_lbist_test_controller}
    {Isolation core_isolation tb_core_scan_isolation}
    {ShiftCapture core_shift_capture_P256 tb_core_scan_shift_capture}
    {ShiftCapture core_shift_capture_P16 tb_core_scan_shift_capture}
} {
    lassign $item group tag top
    set folder [file join $phase5_root Results Phase5A $group waveforms]
    set db [file join $folder $tag.wdb];set cfg [file join $folder $tag.wcfg]
    if {![file exists $db] || [file size $db]==0} {error "Missing native database for $tag"}
    set f [open $cfg r];set text [read $f];close $f
    if {![regexp [format {<db_ref path="%s.wdb"} $tag] $text]} {error "Wrong native database reference for $tag"}
    open_wave_database $db;open_wave_config $cfg
    set prefix /$top
    set signals {clk rst state se ce}
    if {$group ne "Controller"} {
        set prefix /$top/engine
        set signals {clk rst test_phase isolation_ack protected_state scan_state scan_enable capture_enable scan_out scan_feedback wr register_write_actual}
    }
    foreach name $signals {
        if {[llength [get_objects $prefix/$name]]!=1} {error "Missing native signal $prefix/$name"}
    }
    close_sim;incr checked
    puts "PHASE 5A NATIVE WAVEFORM: PASS -- $tag"
}
set python [phase3_python]
puts [exec $python -E [file join $phase5_scripts phase5a_analysis.py] --waves]
puts "PHASE 5A WAVEFORM AUDIT: PASS ($checked native captures)"
