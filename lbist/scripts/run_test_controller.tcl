source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
if {[catch {
    phase5_project controller
    foreach length {1 2 64} {
        phase5_case Controller tb_lbist_test_controller controller_L$length [list LENGTH=$length PATTERNS=256] [expr {$length==64}]
    }
    close_project
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
