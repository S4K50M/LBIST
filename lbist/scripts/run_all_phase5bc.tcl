set bc_scripts [file dirname [file normalize [info script]]]
source [file join $bc_scripts phase5bc_common.tcl]
set python [phase3_python]
if {[catch {
 puts [exec $python -E [file join $bc_scripts build_phase5bc.py]]
 puts [exec $python -E [file join $bc_scripts misr_golden.py] --unit]
 foreach runner {run_misr_unit.tcl run_misr_integration.tcl run_fault_campaign.tcl run_phase5bc_functional.tcl} {
  source [file join $bc_scripts $runner]
 }
 puts [exec $python -E [file join $bc_scripts phase5bc_results.py]]
 source [file join $bc_scripts verify_phase5bc_waveforms.tcl]
 puts "PHASE 5B/C ALL TESTS: PASS"
} message]} {puts stderr $message;exit 1}
