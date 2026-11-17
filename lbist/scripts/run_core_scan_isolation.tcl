source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
if {[catch {
    phase5_project isolation
    phase5_case Isolation tb_core_scan_isolation core_isolation {} 1 1
    close_project
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
