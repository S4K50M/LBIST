source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 phase5_project synthesis
 add_files -fileset sources_1 [list [file join $phase5_root lbist rtl phase6a_controlled_misr.vhd]]
 set out [file join $phase5_root Results Phase6A reports];file mkdir $out
 set f [open [file join $out synthesis.csv] w];puts $f "Top,FF,LUT,Latches"
 foreach top {phase6a_safe_misr lbist_pattern_router phase6a_controlled_misr} {
  synth_design -mode out_of_context -top $top -part xc7a35tcpg236-1
  set ff 0;set lut 0;set latch 0
  foreach c [get_cells -hier] {
   set ref [get_property REF_NAME $c]
   if {[string match FD* $ref]} {incr ff}
   if {[string match LUT* $ref]} {incr lut}
   if {[string match LD* $ref]} {incr latch}
  }
  puts $f "$top,$ff,$lut,$latch"
  if {$latch} {error "Unexpected latch"}
  report_utilization -file [file join $out $top.utilization.rpt]
  close_design
 }
 close $f;close_project
} message]} {puts stderr $message;exit 1}
