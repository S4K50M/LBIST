source [file join [file dirname [file normalize [info script]]] phase3_common.tcl]
if {[catch {phase3_run tb_swap_controller} message]} {
    puts stderr [format {[FAIL] %s} $message]
    if {[info exists ::env(PHASE3_GUI)]} {error $message} else {exit 1}
}
