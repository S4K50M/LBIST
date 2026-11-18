# Uses the already routed, constrained checkpoints. No synthesis/route rerun.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $root Results Final FPGA_Analysis]
file mkdir [file join $root Results Final work]
cd [file join $root Results Final work]
set status [open [file join $out power status.csv] w]
puts $status "Configuration,Approach,Stage,Status,Detail";flush $status
set failed 0
foreach config {baseline scan_enabled full_lbist} {
 set cases [expr {$config eq "full_lbist" ? {0 1 2 3 4} : {functional}}]
 foreach a $cases {
  set tag [expr {$a eq "functional" ? $config : "approach_$a"}]
  set folder [file join $out power $tag];file mkdir $folder
  if {[catch {
   open_checkpoint [file join $::env(TEMP) vl405_final_fpga $config routed.dcp]
   if {[get_property PART [current_design]] ne "xc7a35tcpg236-1"} {error "Incorrect part"}
   set_operating_conditions -ambient_temp 25 -process typical
   set saif [file join $out power activity mapped_$tag.saif]
   if {![file exists $saif]} {error "Missing own activity: $saif"}
   read_saif -strip_path final_fpga_top -out_file [file join $folder unmatched_nets.rpt] $saif
   report_power -file [file join $folder power.rpt]
   report_switching_activity -file [file join $folder switching.rpt] [get_nets -hier]
   report_utilization -file [file join $out $config routed_utilization.rpt]
   report_timing_summary -report_unconstrained -file [file join $out $config routed_timing.rpt]
   set f [open [file join $folder activity_properties.txt] w]
   puts $f [list_property [lindex [get_nets -hier] 0]]
   close $f
   puts $status "$config,$a,SAIF_power,PASS,real own RTL SAIF on routed checkpoint; inspect annotation coverage"
   flush $status
   close_design
  } reason]} {
   set failed 1
   puts $status "$config,$a,SAIF_power,FAIL,[string map {, ; \n { }} $reason]";flush $status
   puts stderr "FINAL POWER $config/$a: $reason"
   catch {close_design}
  }
 }
}
close $status
if {$failed} {exit 1}
puts "FINAL FPGA SAIF POWER: PASS (coverage/confidence limitations retained)"
