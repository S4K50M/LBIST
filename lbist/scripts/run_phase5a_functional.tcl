source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
if {[catch {
    phase5_project functional
    phase5_case Isolation tb_core_scan_test_regression functional_lwsw {STALL_TEST=false} 0 1
    phase5_case Isolation tb_core_scan_test_regression functional_stalls {STALL_TEST=true} 0 1
    close_project
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
