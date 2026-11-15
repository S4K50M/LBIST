source [file join [file dirname [file normalize [info script]]] phase4_common.tcl]
if {[catch {phase4_run unit} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
