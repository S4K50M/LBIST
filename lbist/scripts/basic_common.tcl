# Separate Vivado project-mode runner. Phase 2 scripts/results are read-only.
set basic_script_dir [file dirname [file normalize [info script]]]
proc basic_run {selection} {
    global basic_script_dir
    set root [file normalize [file join $basic_script_dir ../..]]
    set results [file join $root Results Phase3 Basic]
    file mkdir [file join $results logs] [file join $results reports]
    set project_dir [file join $results work project]
    if {$selection eq "negative"} {set project_dir [file join $results work negative_project]}
    create_project -force basic $project_dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    foreach name {lfsr_16 phase_shifter plpf_dynamic basic_controller} {
        add_files -fileset sources_1 [list [file join $root lbist rtl $name.vhd]]
    }
    foreach name {phase2_tb_pkg tb_basic_controller tb_basic_integration} {
        add_files -fileset sim_1 [list [file join $root lbist tb $name.vhd]]
    }
    set_property file_type VHDL [get_files *.vhd]
    set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
    set cases {}
    if {$selection ne "integration"} {
        if {$selection ne "negative"} {
            foreach beta {0 8 16 20 28 36} {lappend cases [list tb_basic_controller 64 $beta paper-compliant]}
            lappend cases {tb_basic_controller 28 0 paper-compliant} {tb_basic_controller 65 21 paper-compliant}
        }
        foreach pair {{64 1} {64 65} {1 0} {64 38}} {
            lappend cases [list tb_basic_controller {*}$pair expected-rejection]
        }
    }
    if {$selection eq "all" || $selection eq "integration"} {
        foreach beta {0 8 16 20 28 36} {lappend cases [list tb_basic_integration 64 $beta paper-compliant]}
    }
    set status [open [file join $results reports basic_verification_summary.csv] w]
    puts $status "Case,Testbench,ChainLength,Beta,Classification,Result,CompletionTime"
    set units [open [file join $results reports basic_controller_summary.csv] w]
    puts $units "Case,ChainLength,Alpha,Beta,Gamma,Patterns,Shifts,SimTime,Result"
    set metrics [open [file join $results reports basic_wtm_summary.csv] w]
    puts $metrics "ChainLength,Alpha,Beta,Gamma,TargetWTM,EstimatedWTM,MeasuredWTM,ErrorPP,SerialToggleRate,ActualChainToggleFraction,Patterns,Shifts,SimTime,Result"
    set failures 0
    foreach case $cases {
        lassign $case top length beta classification
        set tag ${top}_L${length}_B${beta}
        puts "========================================"
        puts "BASIC CONTROL: $tag ($classification)"
        puts "========================================"
        set_property top $top [get_filesets sim_1]
        set_property generic [list CHAIN_LENGTH=$length BETA=$beta] [get_filesets sim_1]
        update_compile_order -fileset sim_1
        set simlog [file join $project_dir basic.sim sim_1 behav xsim simulate.log]
        if {[file exists $simlog]} {file delete $simlog}
        set problem [catch {
            launch_simulation -simset sim_1 -mode behavioral
            set finished 0
            # A negative configuration has already asserted at time zero during
            # launch's run 0ns. Never resume a rejected simulation.
            if {$classification ne "expected-rejection"} {
            for {set step 0} {$step < 5000} {incr step} {
                run 1 us
                set done [string tolower [get_value /$top/test_done]]
                if {$done eq "true" || $done eq "1"} {set finished 1; break}
            }
            }
            if {!$finished && $classification ne "expected-rejection"} {error "watchdog or Tcl runtime timeout"}
        } message]
        catch {close_sim}
        set text ""
        if {[file exists $simlog]} {
            file copy -force $simlog [file join $results logs $tag.log]
            set f [open $simlog r]; set text [read $f]; close $f
        }
        foreach filename {xvhdl.log elaborate.log} {
            set src [file join [file dirname $simlog] $filename]
            if {[file exists $src]} {file copy -force $src [file join $results logs ${tag}_${filename}]}
        }
        set complete [regexp [format {\[TB_COMPLETE\] %s at ([^\n\r]+)} $top] $text whole duration]
        set result FAIL
        if {$classification eq "expected-rejection"} {
            set duration {0 ns}
            if {[regexp {\[CONFIG_ERROR\]} $text] && !$complete && ![regexp {\[FAIL\]} $text]} {
                set result PASS
                puts "\[PASS\] BC11 expected generic rejection (intentional negative test)"
            }
        } elseif {!$problem && $complete && ![regexp {\[FAIL\]|Failure:|Fatal:|ERROR:} $text]} {set result PASS}
        if {$result eq "FAIL"} {
            incr failures; set duration UNKNOWN
            set f [open [file join $results logs ${tag}_runner_error.log] w]
            puts $f "$message; completion=$complete"; close $f
        }
        puts "RESULT: $result -- $duration"
        puts $status "$tag,$top,$length,$beta,$classification,$result,$duration"
        foreach line [split $text "\n"] {
            if {[regexp {\[PASS\].*} $line category]} {puts $category}
            if {[regexp {\[CONTROLLER\] ([^\r]+)} $line whole data]} {puts $units "$tag,$data,$duration,$result"}
            if {[regexp {\[METRIC\] ([^\r]+)} $line whole data]} {puts $metrics "$data,$result"}
        }
        flush $status; flush $units; flush $metrics
    }
    close $status; close $units; close $metrics; close_project
    if {$failures} {error "$failures Basic verification cases FAILED"}
    puts "BASIC RESULT: PASS ([llength $cases] cases; expected rejections separately classified)"
}
