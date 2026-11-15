# Run with vivado -mode batch -source this_file.tcl (or source in fresh GUI session).
source [file join [file dirname [file normalize [info script]]] common.tcl]
if {[catch {phase2_run {tb_plpf_dynamic}} message]} {
    puts stderr "\[FAIL\] $message"
    if {[info exists ::env(PHASE2_GUI)]} {error $message} else {exit 1}
}
