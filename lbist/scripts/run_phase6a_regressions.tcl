source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 phase5_project regressions
 foreach n {phase3_tb_pkg phase3_controller_check tb_basic_controller tb_swap_controller tb_moving_controller tb_reg_IF_RF_scan phase5a_processor_check tb_core_scan_isolation} {
  add_files -fileset sim_1 [list [file join $phase5_root lbist tb $n.vhd]]
 }
 foreach top {tb_basic_controller tb_swap_controller tb_moving_controller tb_reg_IF_RF_scan tb_core_scan_isolation tb_misr_16} {
  phase5_case Regression $top $top {} 0 1
 }
 phase5_case Regression tb_core_fault_regression functional_lwsw {STALL_TEST=false} 0 1
 phase5_case Regression tb_core_fault_regression functional_stalls {STALL_TEST=true} 0 1
 close_project
} message]} {puts stderr $message;exit 1}
