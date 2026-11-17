source [file join [file dirname [file normalize [info script]]] phase5bc_common.tcl]
if {[catch {
 phase5_project misr_unit
 phase5_case MISR tb_misr_16 misr_unit {} 1 0
 close_project
} message]} {puts stderr $message;exit 1}
