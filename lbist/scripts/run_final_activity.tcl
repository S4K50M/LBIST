source [file join [file dirname [file normalize [info script]]] final_common.tcl]
if {[catch {
 phase5_project production_activity
 set saif_dir [file join $final_root Results Final FPGA_Analysis power activity]
 file mkdir $saif_dir
 # Wrap actual native capture: start at accepted SHIFT state, stop at DONE.
 rename phase5_capture final_base_capture
 proc phase5_capture {out top tag} {
  global saif_dir
  final_base_capture $out $top $tag
  run 610 ns
  if {[get_value -radix unsigned /$top/engine/test_phase] ne "2"} {error "Unexpected activity-window start"}
  open_saif [file join $saif_dir $tag.saif]
  log_saif [get_objects -r /$top/engine/system_copy/*]
  puts "FINAL SAIF WINDOW START: $tag at [current_time]"
  run 660540 ns
  run 1 ps
  if {[get_value /$top/engine/done] ne "1" || [get_value /$top/engine/prod_valid] ne "1"} {error "Incomplete production activity window"}
  close_saif
  puts "FINAL SAIF WINDOW END: $tag at [current_time]"
 }
 # Exact common window: SHIFT state at 610ns through completed UNLOAD,
 # plus 1ps to include settled zero-delay RTL updates. Reset/restart excluded.
 set approaches {0 1 2 3 4};set betas {20 20 20 16 20}
 foreach a $approaches {
  set tag approach_$a
  # Capture helper opens at 610ns. Schedule close before the 1us stepping loop
  # can include reset/restart. XSim scheduled event is tied to actual DONE.
  set ::final_saif_open 0
  phase5_case Activity tb_final_activity $tag [list APPROACH=$a BETA=[lindex $betas $a] CONFIG_ID=$a] 1 1
 }
 close_project
 puts "FINAL PRODUCTION ACTIVITY: PASS"
} message]} {puts stderr $message;exit 1}
