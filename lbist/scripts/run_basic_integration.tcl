source [file join [file dirname [file normalize [info script]]] basic_common.tcl]
if {[catch {basic_run integration} message]} {
    puts stderr "\[FAIL\] $message"
    if {[info exists ::env(BASIC_GUI)]} {error $message} else {exit 1}
}
