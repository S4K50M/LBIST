source [file join [file dirname [file normalize [info script]]] final_common.tcl]
if {[catch {
 phase5_project essentials
 foreach n {phase3_tb_pkg phase3_controller_check tb_basic_controller tb_swap_controller tb_moving_controller tb_reg_IF_RF_scan phase5a_processor_check tb_core_scan_isolation tb_phase6a_router tb_lfsr_16 tb_phase_shifter tb_plpf_dynamic} {
  set file [file join $final_root lbist tb $n.vhd]
  if {[file exists $file]} {add_files -fileset sim_1 [list $file]}
 }
 foreach top {tb_lfsr_16 tb_phase_shifter tb_plpf_dynamic tb_basic_controller tb_swap_controller tb_moving_controller tb_reg_IF_RF_scan tb_core_scan_isolation tb_misr_16 tb_phase6a_misr_safety tb_phase6a_router} {
  phase5_case Essential $top $top {} 0 1
 }
 phase5_case Essential tb_core_fault_regression functional_lwsw {STALL_TEST=false} 0 1
 phase5_case Essential tb_core_fault_regression functional_stalls {STALL_TEST=true} 0 1
 close_project
 puts "FINAL ESSENTIAL VERIFICATION: PASS"
} message]} {puts stderr $message;exit 1}
