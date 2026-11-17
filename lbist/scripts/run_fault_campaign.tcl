source [file join [file dirname [file normalize [info script]]] phase5bc_common.tcl]
if {[catch {
 set first 1;set last 16
 if {[info exists ::fault_first]} {set first $::fault_first}
 if {[info exists ::fault_last]} {set last $::fault_last}
 phase5_project faults_$first
 for {set id $first} {$id<=$last} {incr id} {
  set capture [expr {$id in {1 10}}]
  phase5_case Faults tb_lbist_fault_injection fault_$id [list FAULT_ID=$id] $capture 1
 }
 close_project
} message]} {puts stderr $message;exit 1}
