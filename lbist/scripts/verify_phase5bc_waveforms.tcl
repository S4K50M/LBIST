set scripts [file dirname [file normalize [info script]]]
source [file join $scripts phase5bc_common.tcl]
if {[catch {
 foreach item {
  {Phase5B MISR misr_unit tb_misr_16}
  {Phase5B Integration fault_free tb_misr_integration}
  {Phase5C Faults fault_1 tb_lbist_fault_injection}
  {Phase5C Faults fault_10 tb_lbist_fault_injection}
 } {
  lassign $item phase group tag top
  set folder [file join $phase5_root Results $phase $group waveforms]
  open_wave_database [file join $folder $tag.wdb]
  open_wave_config [file join $folder $tag.wcfg]
  set prefix /$top
  if {$group ne "MISR"} {append prefix /engine}
  if {[llength [get_objects $prefix/signature]]!=1} {error "Missing real MISR trace"}
  close_sim
  puts "NATIVE MISR WAVEFORM PASS: $tag"
 }
 set python [phase3_python]
 puts [exec $python -E [file join $scripts phase5bc_results.py]]
} message]} {puts stderr $message;exit 1}
