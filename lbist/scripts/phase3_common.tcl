# Common project-mode engine; all reports are under new Phase 3 folders.
set phase3_script_dir [file dirname [file normalize [info script]]]
source [file join $phase3_script_dir waveforms_common.tcl]
# Vivado prepends its bundled Python to PATH; choose an installation that can
# generate the requested plots, or honor an explicit executable override.
proc phase3_python {} {
    if {[info exists ::phase3_selected_python]} {return $::phase3_selected_python}
    set candidates {}
    if {[info exists ::env(PHASE3_PYTHON)]} {
        lappend candidates $::env(PHASE3_PYTHON)
    } else {
        if {[info exists ::env(LOCALAPPDATA)]} {
            set installs [glob -nocomplain -directory [file join $::env(LOCALAPPDATA) Programs Python] Python*/python.exe]
            set candidates [lsort -decreasing $installs]
        }
        lappend candidates python3 python
    }
    foreach candidate $candidates {
        if {![catch {exec $candidate -E -c {import sys; assert sys.version_info >= (3,9); import matplotlib,numpy}}]} {
            set ::phase3_selected_python $candidate
            puts "PHASE 3 PYTHON: $candidate"
            return $candidate
        }
    }
    error "No Python 3.9+ with matplotlib/numpy found; install those packages and set PHASE3_PYTHON to its executable."
}
proc phase3_run {selection} {
    global phase3_script_dir
    set root [file normalize [file join $phase3_script_dir ../..]]
    set python [phase3_python]
    puts [exec $python -E [file join $phase3_script_dir make_phase3_plan.py]]
    source [file join $root Results Phase3 Comparison work experiment_plan.tcl]
    set project_dir [file join $root Results Phase3 Comparison work project_$selection]
    create_project -force phase3 $project_dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    foreach file [glob [file join $root lbist rtl *.vhd]] {add_files -fileset sources_1 [list $file]}
    foreach name {phase2_tb_pkg phase3_tb_pkg phase3_controller_check phase3_integration_check tb_swap_controller tb_moving_controller tb_swap_integration tb_moving_integration tb_phase3_comparison tb_lfsr_16 tb_phase_shifter tb_plpf_optimized tb_plpf_dynamic tb_phase2_integration tb_basic_controller tb_basic_integration} {
        set file [file join $root lbist tb $name.vhd]
        if {[file exists $file]} {add_files -fileset sim_1 [list $file]}
    }
    set_property file_type VHDL [get_files *.vhd]
    set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
    set failed 0; set executed 0
    foreach case $phase3_cases {
        lassign $case group top tag generics negative capture regression
        set selected [expr {$selection eq "all" || ($selection eq "regression" && $regression) || ($selection eq "waveforms" && $capture) || ($selection eq $top && !$regression)}]
        if {!$selected} {continue}
        incr executed
        set out [file join $root Results Phase3 $group]
        file mkdir [file join $out logs] [file join $out reports cases]
        set_property top $top [get_filesets sim_1]
        set_property generic $generics [get_filesets sim_1]
        update_compile_order -fileset sim_1
        set simdir [file join $project_dir phase3.sim sim_1 behav xsim]
        set simlog [file join $simdir simulate.log]
        if {[file exists $simlog]} {file delete $simlog}
        puts "=== PHASE 3: $tag ==="
        set size 0
        set problem [catch {
            launch_simulation -simset sim_1 -mode behavioral
            if {!$negative} {
                if {$capture} {phase3_wave_begin [file join $out waveforms] $top $tag}
                set finished 0
                for {set step 0} {$step<20000} {incr step} {
                    if {[string tolower [get_value /$top/test_done]] in {true 1}} {set finished 1; break}
                    run 1 us
                }
                if {!$finished} {error "Simulation timeout without test_done"}
                if {$capture} {save_wave_config [file join $out waveforms $tag.wcfg]}
            }
        } message]
        catch {close_vcd}
        catch {close_sim}
        set text ""
        if {[file exists $simlog]} {
            file copy -force $simlog [file join $out logs $tag.log]
            if {$capture} {file copy -force $simlog [file join $out waveforms $tag.log]}
            set f [open $simlog r]; set text [read $f]; close $f
        }
        foreach filename {xvhdl.log elaborate.log} {
            set src [file join $simdir $filename]
            if {[file exists $src]} {file copy -force $src [file join $out logs [format "%s_%s" $tag $filename]]}
        }
        set complete [regexp [format {[[]TB_COMPLETE[]] %s at ([^[:cntrl:]]+)} $top] $text whole duration]
        set result FAIL
        if {$negative} {
            set duration {0 ns}
            if {[regexp {[[]CONFIG_ERROR[]]} $text] && !$complete && ![regexp {[[]FAIL[]]} $text]} {set result PASS}
        } elseif {!$problem && $complete && ![regexp {[[]FAIL[]]|Failure:|Fatal:|ERROR:} $text]} {
            set result PASS
            if {$capture} {
                if {[catch {set size [phase3_wave_finish [file join $out waveforms] $top $tag $simdir]} why]} {
                    set result FAIL; set message $why
                }
            }
        }
        if {$result eq "FAIL"} {
            incr failed; set duration UNKNOWN
            set f [open [file join $out logs [format "%s_runner_error.log" $tag]] w]
            puts $f $message; close $f
            puts stderr "[format {FAIL: %s -- %s} $tag $message]"
        }
        set f [open [file join $out reports cases $tag.csv] w]
        puts $f "Case,Testbench,ExpectedNegative,Regression,Capture,Result,CompletionTime,WDBBytes"
        puts $f "$tag,$top,$negative,$regression,$capture,$result,$duration,$size"
        close $f
        puts "RESULT: $result -- $tag -- $duration"
    }
    close_project
    if {$failed} {error "$failed of $executed Phase 3 cases failed"}
    puts "PHASE 3 RESULT: PASS ($executed cases)"
}

# Report generation and real-data waveform verification are shared by full and
# staged execution. They never invoke the old Phase 2/Basic report writers.
proc phase3_finalize {} {
    global phase3_script_dir
    set python [phase3_python]
    puts [exec $python -E [file join $phase3_script_dir collect_phase3_results.py] --require-all]
    puts [exec $python -E [file join $phase3_script_dir render_waveform_previews.py] --phase3]
    set ::WAVEFORM_VERIFY_SCOPE phase3
    source [file join $phase3_script_dir verify_waveforms.tcl]
    puts "PHASE 3 FINAL REPORTS AND WAVEFORM VERIFICATION: PASS"
}
