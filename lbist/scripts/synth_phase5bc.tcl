set here [file dirname [file normalize [info script]]]
set root [file normalize [file join $here ../..]]
cd [file join $root Results Phase5B work]
if {[catch {
 create_project -in_memory -part xc7a35tcpg236-1
 foreach n {misr_16 misr_signature_checker lbist_misr_top lbist_test_controller lbist_controlled_misr} {
  add_files [list [file join $root lbist rtl $n.vhd]]
 }
 file mkdir [file join $root Results Phase5B reports]
 set f [open [file join $root Results Phase5B reports synthesis.csv] w]
 puts $f "Top,FF,LUT,Latches"
 foreach top {misr_16 lbist_misr_top lbist_controlled_misr} {
  synth_design -mode out_of_context -top $top -part xc7a35tcpg236-1
  set ff 0;set lut 0;set latch 0
  foreach c [get_cells -hier] {
   set r [get_property REF_NAME $c]
   if {[string match FD* $r]} {incr ff}
   if {[string match LUT* $r]} {incr lut}
   if {[string match LD* $r]} {incr latch}
  }
  puts $f "$top,$ff,$lut,$latch"
  report_utilization -file [file join $root Results Phase5B reports $top.utilization.rpt]
  if {$latch!=0} {error "Unexpected latch"}
  close_design
 }
 close $f
} message]} {puts stderr $message;exit 1}
