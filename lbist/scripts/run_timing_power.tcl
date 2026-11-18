set root [file normalize [file join [file dirname [info script]] ../..]]
if {[llength $argv]!=2} {error "Arguments: VCO_MULT CPU_DIVIDE"}
lassign $argv m d
set tag m${m}_d${d};set period [expr {10.0*$d/$m}]
set base [file join $root Results Final FPGA_Analysis Timing_Closure]
set out [file join $base power $tag];file mkdir $out
cd [file join $base work]
set status [open [file join $out status.csv] w];puts $status "Configuration,Approach,Result,Detail";flush $status
set failed 0
foreach config {baseline scan_enabled full_lbist} {
 foreach a [expr {$config eq "full_lbist" ? {0 1 2 3 4} : {functional}}] {
  set name [expr {$a eq "functional" ? $config : "approach_$a"}]
  set folder [file join $out $name];file mkdir $folder
  if {[catch {
   open_checkpoint [file join $::env(TEMP) vl405_timing_closed $tag $config routed.dcp]
   if {abs([get_property PERIOD [get_clocks c0]]-$period)>0.002} {error "Wrong checkpoint clock"}
   if {[llength [get_cells -quiet irq_hold_delay_*]]} {error "Orphan trial cells remain in production checkpoint"}
   set buffers [get_cells -quiet physical_hold_*]
   foreach cell $buffers {
    if {[get_property REF_NAME $cell] ne "LUT1" || ![string equal -nocase [get_property INIT $cell] "2'h2"]} {error "Non-identity physical repair: $cell"}
    set loads [get_pins -leaf -of_objects [get_nets -segments -of_objects [get_pins $cell/O]] -filter {DIRECTION == IN}]
    if {![llength $loads]} {error "Unconnected repair cell: $cell"}
   }
   puts "ROUTED IDENTITY ECO CHECK PASS: $config, [llength $buffers] connected LUT1 identity delays"
   set_operating_conditions -ambient_temp 25 -process typical
   read_saif -strip_path final_fpga_top -out_file [file join $folder unmatched_nets.rpt] [file join $base activity $tag mapped_$name.saif]
   report_power -hier all -hierarchical_depth 5 -l 30 -file [file join $folder power.rpt]
   report_switching_activity -file [file join $folder switching.rpt] [get_nets -hier]
   set ffs [get_cells -hier -filter {REF_NAME =~ FD*}]
   set qs [get_pins -of_objects $ffs -filter {REF_PIN_NAME == Q}]
   report_switching_activity -file [file join $folder register_switching.rpt] [get_nets -of_objects $qs]
   puts $status "$config,$a,PASS,fresh own RTL SAIF; inspect coverage and confidence";flush $status
   close_design
  } reason]} {
   set failed 1;puts $status "$config,$a,FAIL,[string map {, ; \n { }} $reason]";flush $status
   puts stderr $reason;catch {close_design}
  }
 }
}
close $status
if {$failed} {exit 1}
puts "UPDATED TIMING-CONSISTENT POWER EXPORTS: PASS"
