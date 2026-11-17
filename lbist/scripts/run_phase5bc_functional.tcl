source [file join [file dirname [file normalize [info script]]] phase5bc_common.tcl]
if {[catch {
 phase5_project bc_functional
 phase5_case Integration tb_core_fault_regression functional_lwsw {STALL_TEST=false} 0 1
 phase5_case Integration tb_core_fault_regression functional_stalls {STALL_TEST=true} 0 1
 close_project
} message]} {puts stderr $message;exit 1}
