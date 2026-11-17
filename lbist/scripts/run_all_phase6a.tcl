set phase6_scripts [file dirname [file normalize [info script]]]
source [file join $phase6_scripts phase6a_common.tcl]
set py [phase3_python]
if {[catch {
 puts [exec $py -E [file join $phase6_scripts build_phase6a.py]]
 source [file join $phase6_scripts run_phase6a_router.tcl]
 set ::configs {0 1 2 3 4 5 6 7 8 9 10 11}
 set ::fault_last 0
 source [file join $phase6_scripts run_phase6a_faults.tcl]
 unset ::fault_last
 set ::batch_configs $::configs
 source [file join $phase6_scripts run_phase6a_batch.tcl]
 source [file join $phase6_scripts run_phase6a_regressions.tcl]
 puts [exec $py -E [file join $phase6_scripts phase6a_results.py]]
 puts [exec $py -E [file join $phase6_scripts phase6a_layouts.py]]
 source [file join $phase6_scripts verify_phase6a_waveforms.tcl]
 puts [exec $py -E [file join $phase6_scripts phase6a_report.py]]
 puts [exec $py -E [file join $phase6_scripts phase6a_manifest.py]]
} message]} {puts stderr $message;exit 1}
