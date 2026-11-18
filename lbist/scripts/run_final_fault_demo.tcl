# One fresh representative from the unchanged original 16-fault universe.
source [file join [file dirname [file normalize [info script]]] final_common.tcl]
if {[catch {
 phase5_project fault_demo
 phase5_case FaultDemo tb_phase6a_fault_comparison basic_fault_1 {APPROACH=2 BETA=20 CONFIG_ID=2 FAULT_ID=1} 1 1
 close_project
 puts "FINAL REPRESENTATIVE FAULT: PASS"
} reason]} {puts stderr $reason;exit 1}
