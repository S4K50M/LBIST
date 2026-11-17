set scripts [file dirname [file normalize [info script]]]
if {[catch {
    source [file join $scripts phase5a_common.tcl]
    set python [phase3_python]
    puts [exec $python -E [file join $scripts audit_phase5a.py] --snapshot]
    puts [exec $python -E [file join $scripts generate_phase5a_variants.py]]
    foreach runner {run_test_controller.tcl run_core_scan_isolation.tcl run_core_shift_capture.tcl run_phase5a_functional.tcl} {
        source [file join $scripts $runner]
    }
    set python [phase3_python]
    puts [exec $python -E [file join $scripts phase5a_analysis.py] --require-all --waves]
    source [file join $scripts verify_phase5a_waveforms.tcl]
    set test_output [exec $python -E [file join $scripts test_phase5a_analysis.py] 2>@1]
    puts $test_output
    set f [open [file join $phase5_root Results Phase5A Controller logs python_capture_tests.log] w]
    puts $f $test_output;close $f
    puts [exec $python -E [file join $scripts audit_phase5a.py]]
    puts [exec $python -E [file join $scripts phase5a_manifest.py]]
    puts "PHASE 5A ALL TESTS: PASS"
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
