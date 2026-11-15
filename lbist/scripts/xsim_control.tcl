# XSim-only control script; supplied TOP is written by the parent runner.
puts "=== Phase 2 bounded simulation: $TOP ==="
set finished 0
for {set step 0} {$step < 2000} {incr step} {
    run 1 us
    set done [string tolower [get_value /$TOP/test_done]]
    if {$done eq "true" || $done eq "1"} {set finished 1; break}
}
if {!$finished} {puts "\[FAIL\] Tcl timeout: test_done was not asserted"}
puts "=== XSim control ended; parent verifies assertions and completion log ==="
quit
