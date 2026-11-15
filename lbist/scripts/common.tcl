# Vivado Tcl (not XSim Tcl). Always creates a separate Phase 2 project.
set phase2_script_dir [file dirname [file normalize [info script]]]
proc phase2_run {tops} {
    global phase2_script_dir
    set root [file normalize [file join $phase2_script_dir ../..]]
    set results [file join $root Results Phase2]
    file mkdir [file join $results logs] [file join $results reports]
    set project_dir [file join $results work project]
    create_project -force phase2 $project_dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    foreach name {lfsr_16 phase_shifter plpf_optimized plpf_dynamic} {
        add_files -fileset sources_1 [list [file join $root lbist rtl $name.vhd]]
    }
    add_files -fileset sim_1 [list [file join $root lbist tb phase2_tb_pkg.vhd]]
    foreach path [glob [file join $root lbist tb tb_*.vhd]] {add_files -fileset sim_1 [list $path]}
    set_property file_type VHDL [get_files *.vhd]
    set_property xsim.simulate.runtime {0ns} [get_filesets sim_1]
    set rates [open [file join $results reports toggle_rate_summary.csv] w]
    puts $rates "Testbench,Mode,ExpectedRate,MeasuredRate,ErrorPercentagePoints,Patterns,Transitions,Result"
    set weights [open [file join $results reports wtm_summary.csv] w]
    puts $weights "Testbench,Mode,ChainLength,CompletePatterns,NormalizedScanInWTM,ActualChainToggleFraction,WeightedTransitions"
    set status [open [file join $results reports verification_summary.csv] w]
    puts $status "Testbench,Result,CompletionTime"
    set failed 0
    foreach top $tops {
        puts "========================================"
        puts "PHASE 2: $top"
        puts "========================================"
        set_property top $top [get_filesets sim_1]
        update_compile_order -fileset sim_1
        set simlog [file join $project_dir phase2.sim sim_1 behav xsim simulate.log]
        if {[file exists $simlog]} {file delete $simlog}
        set problem [catch {
            launch_simulation -simset sim_1 -mode behavioral
            set finished 0
            for {set step 0} {$step < 2000} {incr step} {
                run 1 us
                set done [string tolower [get_value /$top/test_done]]
                if {$done eq "true" || $done eq "1"} {set finished 1; break}
            }
            if {!$finished} {error "Simulation did not assert test_done within 2 ms"}
        } message]
        catch {close_sim}
        set text ""
        if {[file exists $simlog]} {
            file copy -force $simlog [file join $results logs $top.log]
            set f [open $simlog r]; set text [read $f]; close $f
        }
        foreach buildlog {xvhdl.log elaborate.log} {
            set src [file join [file dirname $simlog] $buildlog]
            if {[file exists $src]} {file copy -force $src [file join $results logs ${top}_${buildlog}]}
        }
        if {$problem} {
            set failurelog [open [file join $results logs ${top}_launch_error.log] w]
            puts $failurelog $message; close $failurelog
        }
        set complete [regexp [format {\[TB_COMPLETE\] %s at ([^\n\r]+)} $top] $text whole duration]
        if {$problem || !$complete || [regexp {\[FAIL\]|Failure:|Fatal:|ERROR:} $text]} {
            set result FAIL; set failed 1; set duration UNKNOWN
            puts "RESULT: FAIL -- $message (completion=$complete)"
        } else {set result PASS; puts "RESULT: PASS -- $duration"}
        puts $status "$top,$result,$duration"
        foreach line [split $text "\n"] {
            if {[regexp {\[PASS\].*} $line category]} {puts $category}
            if {[regexp {\[METRIC\] ([^\r]+)} $line whole metric]} {puts $rates "$metric,$result"}
            if {[regexp {\[WTM\] ([^\r]+)} $line whole metric]} {puts $weights "$top,$metric"}
        }
    }
    close $rates; close $weights; close $status
    close_project
    if {$failed} {error "Phase 2 verification FAILED; inspect Results/Phase2/logs"}
    puts "PHASE 2 RESULT: PASS ([llength $tops] testbenches)"
}
