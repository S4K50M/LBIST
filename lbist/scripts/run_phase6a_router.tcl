source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 phase5_project safety
 add_files -fileset sim_1 [list [file join $phase5_root lbist tb tb_phase6a_router.vhd]]
 phase5_case Router tb_phase6a_misr_safety safety {} 1 0
 phase5_case Router tb_phase6a_router router {} 1 0
 close_project
} message]} {puts stderr $message;exit 1}
