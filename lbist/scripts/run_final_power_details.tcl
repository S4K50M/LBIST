# Report a consistent existing LBIST hierarchy as the limited power boundary.
# This does not synthesize substitute hardware or change the full-processor area study.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $root Results Final FPGA_Analysis power]
cd [file join $root Results Final work]
if {[catch {
 open_checkpoint [file join $::env(TEMP) vl405_final_fpga full_lbist routed.dcp]
 puts [help reset_switching_activity]
 set expected_router [get_cells -hier -filter {REF_NAME =~ *lbist_pattern_router* || ORIG_REF_NAME =~ *lbist_pattern_router*}]
 if {[llength $expected_router]!=1} {error "Expected actual retained production router"}
 puts "RETAINED PRODUCTION ROUTER: $expected_router"
 foreach a {0 1 2 3 4} {
  if {[catch {reset_switching_activity -all} reason]} {
   # A fresh checkpoint is the safe fallback if reset is unsupported.
   puts "Activity reset fallback: $reason"
   close_design
   open_checkpoint [file join $::env(TEMP) vl405_final_fpga full_lbist routed.dcp]
  }
  set_operating_conditions -ambient_temp 25 -process typical
  read_saif -strip_path final_fpga_top -out_file [file join $out approach_$a unmatched_details.rpt] [file join $out activity mapped_approach_$a.saif]
  report_power -hier all -hierarchical_depth 5 -l 100 -file [file join $out approach_$a power_details.rpt]
  report_power -hier all -hierarchical_depth 5 -l 100 -format xml -file [file join $out approach_$a power_details.xml]
  puts "FINAL DETAILED POWER: approach_$a PASS"
 }
 close_design
} reason]} {puts stderr $reason;exit 1}
