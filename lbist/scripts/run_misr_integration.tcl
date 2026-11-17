source [file join [file dirname [file normalize [info script]]] phase5bc_common.tcl]
if {[catch {
 phase5_project misr_integration
 phase5_case Integration tb_misr_integration fault_free {FAULT_ID=0} 1 1
 close_project
} message]} {puts stderr $message;exit 1}
