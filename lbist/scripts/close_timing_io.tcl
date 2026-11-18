# Physical identity-buffer ECO for actual failing OOC input hold paths.
# vivado ... -tclargs full_lbist 8 82
set root [file normalize [file join [file dirname [info script]] ../..]]
lassign $argv config m d
set tag m${m}_d${d};set base [file join $root Results Final FPGA_Analysis Timing_Closure]
set out [file join $base closed $tag $config];file mkdir $out
set cache [file join $::env(TEMP) vl405_timing_closed $tag $config];file mkdir $cache
cd [file join $base work]
if {[catch {
 open_checkpoint [file join $::env(TEMP) vl405_timing $tag $config routed.dcp]
 # Remove only disconnected trial cells; no functional sink may be removed.
 foreach cell [get_cells -quiet irq_hold_delay_*] {
  set net [get_nets -of_objects [get_pins $cell/O]]
  if {![llength [get_pins -quiet -leaf -of_objects $net -filter {DIRECTION == IN}]]} {
   set_property DONT_TOUCH false $cell
   remove_cell $cell
   if {[llength [get_nets -quiet $net]]} {remove_net $net}
  }
 }
 # Let Vivado derive MMCM jitter/phase uncertainty. The old blanket0.1ns
 # override produced Timing38-195 warnings on paths to the virtual clock.
 reset_timing
 read_xdc [list [file join $root lbist final final_primary.xdc]]
 set period [expr {10.0*$d/$m}]
 create_clock -name virtual_cpu_io -period $period -waveform [list 0 [expr {$period/2.0}]]
 set inputs [get_ports -filter {DIRECTION == IN && NAME != board_clk && NAME != reset_button}]
 set_input_delay -clock virtual_cpu_io -max 2.000 $inputs
 set_input_delay -clock virtual_cpu_io -min 0.500 $inputs
 set_output_delay -clock virtual_cpu_io -max 2.000 [get_ports -filter {DIRECTION == OUT}]
 set_output_delay -clock virtual_cpu_io -min 0.500 [get_ports -filter {DIRECTION == OUT}]
 set_false_path -from [get_ports reset_button] -to [get_pins -hier -filter {REF_PIN_NAME == CLR || REF_PIN_NAME == PRE || REF_PIN_NAME == RST}]
 set proof [open [file join $out hold_buffer_connectivity.csv] w]
 puts $proof "Iteration,Port,Cell,Function,Sinks,ConnectivityChecked"
 set serial 0
 for {set iteration 0} {$iteration<4} {incr iteration} {
  set paths [get_timing_paths -delay_type min -slack_lesser_than 0 -max_paths 1000 -nworst 1]
  set ports {}
  foreach path $paths {
   set start [get_property STARTPOINT_PIN $path]
   if {[llength [get_ports -quiet [list $start]]]} {lappend ports $start}
  }
  set ports [lsort -unique $ports]
  puts "INPUT HOLD REPAIR ITERATION $iteration: $ports"
  if {![llength $ports]} {break}
  foreach name $ports {
   set port [get_ports [list $name]];set net [get_nets -of_objects $port]
   set loads [get_pins -leaf -of_objects $net -filter {DIRECTION == IN}]
   if {![llength $loads]} {error "No actual loads on $name"}
   # Each leaf pin has its own hierarchy-local segment. Disconnect that
   # segment, then explicitly request a cross-hierarchy connection.
   foreach pin $loads {
    disconnect_net -net [get_nets -of_objects $pin] -objects $pin
    if {[llength [get_nets -quiet -of_objects $pin]]} {error "Failed disconnect $pin"}
   }
   set cell physical_hold_$serial;set delayed physical_hold_net_$serial;incr serial
   create_cell -reference LUT1 $cell;set_property INIT 2'h2 [get_cells $cell]
   set_property DONT_TOUCH true [get_cells $cell]
   create_net $delayed
   connect_net -net $net -objects [get_pins $cell/I0]
   connect_net -net $delayed -objects [get_pins $cell/O]
   connect_net -hierarchical -net $delayed -objects $loads
   set connected [get_pins -leaf -of_objects [get_nets -segments -of_objects [get_pins $cell/O]] -filter {DIRECTION == IN}]
   foreach pin $loads {if {[lsearch -exact $connected $pin]<0} {error "Failed reconnect $pin"}}
   puts $proof "$iteration,$name,$cell,identity_LUT1_INIT_2,[llength $loads],PASS";flush $proof
  }
  place_design
  route_design
 }
 close $proof
 phys_opt_design -aggressive_hold_fix
 route_design
 write_checkpoint -force [file join $cache routed.dcp]
 report_utilization -file [file join $out routed_utilization.rpt]
 report_timing_summary -report_unconstrained -file [file join $out routed_timing.rpt]
 report_timing -delay_type min -max_paths 20 -file [file join $out hold_paths.rpt]
 report_timing -delay_type max -max_paths 20 -file [file join $out setup_paths.rpt]
 report_clock_interaction -file [file join $out clock_interaction.rpt]
 report_clocks -file [file join $out clocks.rpt]
 report_route_status -file [file join $out route_status.rpt]
 report_drc -file [file join $out drc.rpt]
 write_xdc -force [file join $out applied_constraints.xdc]
 puts "FINAL PHYSICAL REPAIR FINISHED: $config $tag; inspect setup AND hold"
 close_design
} reason]} {puts stderr $reason;exit 1}
