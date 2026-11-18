# First run prepare_timing_verification.py M D. No earlier reports are written.
set root [file normalize [file join [file dirname [info script]] ../..]]
if {[llength $argv]!=2} {error "Arguments: VCO_MULT CPU_DIVIDE"}
lassign $argv m d
set timing_base [file join $root Results Final FPGA_Analysis Timing_Closure]
set generated [file join $timing_base generated m${m}_d${d}]
source [file join $generated clock.tcl]
source [file join $root lbist scripts phase6a_common.tcl]
cd [file join $timing_base work]
set ::env(PHASE6A_NATIVE_ROOT) [file join $::env(TEMP) vl405_timing_sim $timing_tag]
set body [string map [list Phase6A Final/FPGA_Analysis/Timing_Closure/verification/$timing_tag {tb_core_fault_regression tb_cMIPS} {tb_core_fault_regression tb_final_functional_activity tb_cMIPS}] [info body phase5_case]]
set body [string map [list {{Time: ([0-9]+) ns[^\n]*RF_STOP_SIMULATION} $text m ns} {{Time: ([0-9]+) (ps|ns)[^\n]*RF_STOP_SIMULATION} $text m raw unit} {[expr {$ns*1000}]} {[expr {$raw*($unit eq "ns" ? 1000 : 1)}]}] $body]
proc phase5_case {group top tag generics {capture 1} {cpu 0}} $body
set body [string map [list tb_phase6a_fault_comparison {tb_phase6a_fault_comparison tb_final_activity} {current_bit future1 future2 } {} { active_mode } { }] [info body phase5_capture]]
proc timing_base_capture {out top tag} $body
rename phase3_wave_finish timing_native_wave_finish
proc phase3_wave_finish {folder top tag simdir} {
 global timing_scale
 set bytes [timing_native_wave_finish $folder $top $tag $simdir]
 set path [file join $folder $tag.wcfg]
 set f [open $path r];set text [read $f];close $f
 regsub {<ZoomStartTime time="[^"]+"} $text [format {<ZoomStartTime time="%.3f ns"} [expr {1800*$timing_scale}]] text
 regsub {<ZoomEndTime time="[^"]+"} $text [format {<ZoomEndTime time="%.3f ns"} [expr {2150*$timing_scale}]] text
 set f [open $path w];puts $f $text;close $f
 return $bytes
}
set body [string map [list tb_core_fault_regression tb_final_functional_activity {run 5 ns} "run [expr {5*$timing_scale}] ns" {run 10 ns} "run [expr {10*$timing_scale}] ns" {$step*5000} "\$step*[expr {5000*$timing_scale}]"] [info body phase5_cpu_run]]
proc timing_cpu_run {top tag out} $body
proc phase5_cpu_run {top tag out} {
 global timing_functional_saif
 timing_cpu_run $top $tag $out
 if {$timing_functional_saif} {close_saif;puts "FUNCTIONAL SAIF END [current_time]"}
}
set timing_functional_saif 0
proc phase5_capture {out top tag} {
 global timing_base timing_tag timing_scale timing_functional_saif
 if {$top eq "tb_final_functional_activity"} {
  create_wave_config $tag
  while {[get_value /$top/cpu_reset] ne "1"} {run [expr {5*$timing_scale}] ns}
  open_saif [file join $timing_base activity $timing_tag functional.saif]
  log_saif [concat [get_objects -r /$top/U_CORE/*] [get_objects -r /$top/U_SCAN/*]]
  set timing_functional_saif 1
  puts "FUNCTIONAL SAIF START [current_time]"
 } else {
  timing_base_capture $out $top $tag
  if {$top eq "tb_final_activity"} {
   run [expr {610*$timing_scale}] ns
   if {[get_value -radix unsigned /$top/engine/test_phase] ne "2"} {error "Unexpected SHIFT window start"}
   open_saif [file join $timing_base activity $timing_tag $tag.saif]
   log_saif [get_objects -r /$top/engine/system_copy/*]
   puts "TIMING SAIF START $tag [current_time]"
   run [expr {660540*$timing_scale}] ns
   run $timing_scale ps
   if {[get_value /$top/engine/done] ne "1" || [get_value /$top/engine/prod_valid] ne "1"} {error "Incomplete production window"}
   close_saif
   puts "TIMING SAIF END $tag [current_time]"
  }
 }
}
if {[catch {
 phase5_project timing_$timing_tag
 # Replace simulation time constants/fixtures only; CPU RTL remains identical.
 remove_files [get_files [list [file join $root cMIPS vhdl packageWires.vhd]]]
 remove_files [get_files [list [file join $root cMIPS vhdl altera.vhd]]]
 add_files -fileset sources_1 [list [file join $generated packageWires.vhd] [file join $root lbist final final_processor_system.vhd] [file join $root lbist final final_clock_tree.vhd]]
 add_files -fileset sources_1 [list [file join $generated altera.vhd]]
 remove_files [get_files [list [file join $root lbist tb phase6a_processor_check.vhd]]]
 add_files -fileset sim_1 [list [file join $generated phase6a_processor_check.vhd] [file join $generated final_activity_check.vhd] [file join $generated tb_final_functional_activity.vhd] [file join $root lbist tb tb_final_activity.vhd] [file join $root lbist tb tb_timing_clock_tree.vhd]]
 set_property file_type {VHDL 2008} [get_files [list [file join $root lbist tb tb_timing_clock_tree.vhd]]]
 file mkdir [file join $timing_base activity $timing_tag]
 phase5_case Clock tb_timing_clock_tree actual_mmcm [list M=$m D=$d] 0 0
 # Functional capture helper intentionally needs no WDB export.
 rename phase3_wave_finish timing_finish
 proc phase3_wave_finish {args} {return 0}
 phase5_case Functional tb_final_functional_activity functional_lwsw {STALL_TEST=false} 1 1
 set timing_functional_saif 0
 phase5_case Functional tb_final_functional_activity functional_stalls {STALL_TEST=true} 0 1
 rename phase3_wave_finish {};rename timing_finish phase3_wave_finish
 foreach a {0 1 2 3 4} {
  phase5_case Activity tb_final_activity approach_$a [list APPROACH=$a BETA=[expr {$a==3?16:20}] CONFIG_ID=$a] 1 1
 }
 phase5_case Fault tb_phase6a_fault_comparison basic_fault_1 {APPROACH=2 BETA=20 CONFIG_ID=2 FAULT_ID=1} 1 1
 close_project
 puts "TIMING FUNCTIONAL VERIFICATION: PASS ($timing_tag, new activity captured)"
} reason]} {puts stderr $reason;exit 1}
