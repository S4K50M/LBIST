source [file join [file dirname [file normalize [info script]]] phase3_common.tcl]
if {[catch {phase3_run regression} message]} {puts stderr $message; exit 1}
