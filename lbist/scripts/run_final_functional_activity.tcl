# Separate original/production-scan core activity, under the same lwsw workload.
source [file join [file dirname [file normalize [info script]]] final_common.tcl]
if {[catch {
 phase5_project functional_activity
 add_files -fileset sim_1 [list [file join $final_root lbist tb tb_final_functional_activity.vhd]]
 set body [string map {{tb_core_fault_regression tb_cMIPS} {tb_core_fault_regression tb_final_functional_activity tb_cMIPS}} [info body phase5_case]]
 proc phase5_case {group top tag generics {capture 1} {cpu 0}} $body
 set body [string map {tb_core_fault_regression tb_final_functional_activity} [info body phase5_cpu_run]]
 proc final_cpu_run {top tag out} $body
 proc phase5_capture {out top tag} {
  global final_root
  create_wave_config $tag
  # Reset completion is determined by the actual original memory/cache system.
  for {set k 0} {$k<1000} {incr k} {
   if {[get_value /$top/cpu_reset] eq "1"} {break}
   run 5 ns
  }
  if {[get_value /$top/cpu_reset] ne "1"} {error "No functional reset release"}
  set path [file join $final_root Results Final FPGA_Analysis power activity functional.saif]
  open_saif $path
  log_saif [concat [get_objects -r /$top/U_CORE/*] [get_objects -r /$top/U_SCAN/*]]
  puts "FUNCTIONAL SAIF START [current_time]"
 }
 proc phase5_cpu_run {top tag out} {
  final_cpu_run $top $tag $out
  close_saif
  puts "FUNCTIONAL SAIF END [current_time]"
 }
 # WDB/VCD are not needed for this power-only activity capture.
 proc phase3_wave_finish {args} {return 0}
 phase5_case FunctionalActivity tb_final_functional_activity functional_activity {STALL_TEST=false} 1 1
 close_project
 puts "FINAL FUNCTIONAL ACTIVITY: PASS"
} reason]} {puts stderr $reason;exit 1}
