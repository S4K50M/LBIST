source [file join [file dirname [file normalize [info script]]] phase4_common.tcl]
if {[catch {
    set python [phase3_python]
    puts [exec $python -E [file join $phase4_scripts audit_phase4.py] --snapshot]
    # Core integration deliberately follows successful register/PLPF suites.
    foreach selection {unit plpf core regression} {phase4_run $selection}
    set python [phase3_python]
    puts [exec $python -E [file join $phase4_scripts phase4_analysis.py] --require-all]
    source [file join $phase4_scripts verify_phase4_waveforms.tcl]
    set test_output [exec $python -E [file join $phase4_scripts test_phase4_analysis.py] 2>@1]
    puts $test_output
    set f [open [file join $phase4_root Results Phase4 IF_RF logs python_capture_tests.log] w]
    puts $f $test_output;close $f
    source [file join $phase4_scripts synth_if_rf_scan.tcl]
    puts [exec $python -E [file join $phase4_scripts audit_phase4.py]]
    puts "PHASE 4 ALL TESTS: PASS"
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
