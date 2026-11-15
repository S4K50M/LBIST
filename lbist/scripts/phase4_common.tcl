# Phase 4 extensions reuse the existing Python/waveform tools without changing them.
set phase4_scripts [file dirname [file normalize [info script]]]
source [file join $phase4_scripts phase3_common.tcl]
set phase4_root [file normalize [file join $phase4_scripts ../..]]
file mkdir [file join $phase4_root Results Phase4 work]
# Vivado writes runtime profiles in its working directory: keep them isolated.
cd [file join $phase4_root Results Phase4 work]
proc phase4_run {selection} {
    global phase4_root
    set project_dir [file join $phase4_root Results Phase4 work project_$selection]
    create_project -force phase4 $project_dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    set cpu {packageWires pipestages}
    if {$selection in {core regression}} {
        set cpu {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core cache instrcache rom ram io uart disk SDcard fpu sdram tb_cMIPS}
    }
    foreach name $cpu {add_files -fileset sources_1 [list [file join $phase4_root cMIPS vhdl $name.vhd]]}
    foreach name {reg_IF_RF_scan lfsr_16 phase_shifter plpf_optimized plpf_dynamic basic_controller swap_controller moving_controller multi_chain_phase_shifter} {
        add_files -fileset sources_1 [list [file join $phase4_root lbist rtl $name.vhd]]
    }
    set benches {phase2_tb_pkg tb_reg_IF_RF_scan tb_if_rf_plpf_integration}
    if {$selection eq "core"} {
        add_files -fileset sources_1 [list [file join $phase4_root lbist core_scan core_scan.vhd]]
        lappend benches tb_core_scan_regression
    }
    if {$selection eq "regression"} {
        lappend benches phase3_tb_pkg phase3_controller_check phase3_integration_check tb_lfsr_16 tb_phase_shifter tb_plpf_optimized tb_plpf_dynamic tb_phase2_integration tb_basic_controller tb_basic_integration tb_swap_controller tb_moving_controller tb_swap_integration tb_moving_integration
    }
    foreach name $benches {add_files -fileset sim_1 [list [file join $phase4_root lbist tb $name.vhd]]}
    set_property file_type VHDL [get_files *.vhd]
    set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
    set cases {}
    if {$selection eq "unit"} {
        set cases {
            {IF_RF tb_reg_IF_RF_scan scan_unit_seed12345 {PATTERNS=256 SEED=12345} 0 1}
            {IF_RF tb_reg_IF_RF_scan scan_unit_seed67890 {PATTERNS=256 SEED=67890} 0 0}
            {IF_RF tb_reg_IF_RF_scan scan_unit_invalid_patterns {PATTERNS=1} 1 0}
        }
    } elseif {$selection eq "plpf"} {
        set cases {
            {PLPF_Integration tb_if_rf_plpf_integration real_plpf_B20_P1024 {BETA=20 PATTERNS=1024} 0 1}
            {PLPF_Integration tb_if_rf_plpf_integration real_plpf_B0_P256 {BETA=0 PATTERNS=256} 0 0}
            {PLPF_Integration tb_if_rf_plpf_integration real_plpf_B16_P256 {BETA=16 PATTERNS=256} 0 0}
            {PLPF_Integration tb_if_rf_plpf_integration real_plpf_B36_P256 {BETA=36 PATTERNS=256} 0 0}
            {PLPF_Integration tb_if_rf_plpf_integration real_plpf_invalid_beta {BETA=1 PATTERNS=256} 1 0}
        }
    } elseif {$selection eq "core"} {
        set cases {
            {Core_Integration tb_core_scan_regression core_scan_lwsw {STALL_TEST=false} 0 1}
            {Core_Integration tb_core_scan_regression core_scan_stalls {STALL_TEST=true} 0 0}
        }
    } elseif {$selection eq "regression"} {
        foreach top {tb_lfsr_16 tb_phase_shifter tb_plpf_optimized tb_plpf_dynamic tb_phase2_integration tb_basic_controller tb_basic_integration tb_swap_controller tb_moving_controller tb_swap_integration tb_moving_integration} {
            lappend cases [list Core_Integration $top regression_$top {} 0 0]
        }
        lappend cases {Core_Integration tb_cMIPS baseline_lwsw {} 0 0}
    } else {error "Unknown Phase 4 selection"}
    set failures 0
    foreach item $cases {
        lassign $item group top tag generics negative capture
        set out [file join $phase4_root Results Phase4 $group]
        file mkdir [file join $out logs] [file join $out reports] [file join $out waveforms]
        set_property top $top [get_filesets sim_1]
        set_property generic $generics [get_filesets sim_1]
        update_compile_order -fileset sim_1
        set simdir [file join $project_dir phase4.sim sim_1 behav xsim]
        file mkdir $simdir
        if {$selection in {core regression}} {
            foreach image {prog.bin data.bin input.data serial.inp} {
                set src [file join $phase4_root cMIPS $image]
                if {![file exists $src]} {error "Missing original image: $image"}
                file copy -force $src [file join $simdir $image]
            }
        }
        set simlog [file join $simdir simulate.log]
        if {[file exists $simlog]} {file delete $simlog}
        puts "PHASE 4 CASE: $tag"
        set problem [catch {
            launch_simulation -mode behavioral
            if {!$negative} {
                if {$capture} {phase4_capture_begin $out $top $tag}
                if {$top in {tb_core_scan_regression tb_cMIPS}} {
                    phase4_core_run $top $tag $out
                } else {
                    set done 0
                    for {set step 0} {$step<20000} {incr step} {
                        if {[string tolower [get_value /$top/test_done]] in {true 1}} {set done 1;break}
                        run 1 us
                    }
                    if {!$done} {error "Timeout without test_done"}
                }
                if {$capture} {save_wave_config [file join $out waveforms $tag.wcfg]}
            }
        } message]
        catch {close_vcd}
        catch {close_sim}
        set text ""
        if {[file exists $simlog]} {
            set f [open $simlog r];set text [read $f];close $f
            file copy -force $simlog [file join $out logs $tag.log]
            if {$capture} {file copy -force $simlog [file join $out waveforms $tag.log]}
        }
        foreach name {xvhdl.log elaborate.log} {
            set src [file join $simdir $name]
            if {[file exists $src]} {file copy -force $src [file join $out logs [format "%s_%s" $tag $name]]}
        }
        set duration UNKNOWN;set result FAIL;set bytes 0
        if {$negative} {
            if {[regexp {[[]CONFIG_ERROR[]]} $text] && ![regexp {[[]TB_COMPLETE[]]|[[]FAIL[]]} $text]} {set result PASS;set duration {0 ps}}
        } elseif {$top in {tb_core_scan_regression tb_cMIPS}} {
            if {!$problem && [regexp {cMIPS BREAKPOINT at PC=00000038} $text] && [regexp {Time: ([0-9]+) ns[^\n]*RF_STOP_SIMULATION} $text whole ns] && ![regexp {[[]FAIL[]]|SIMULATION ABORTED|Fatal:|ERROR:} $text]} {
                set result PASS;set duration "[expr {$ns*1000}] ps"
            }
        } elseif {!$problem && [regexp [format {[[]TB_COMPLETE[]] %s at ([0-9]+ ps)} $top] $text whole duration] && ![regexp {[[]FAIL[]]|Failure:|Fatal:|ERROR:} $text]} {set result PASS}
        if {$result eq "PASS" && $capture} {
            if {[catch {set bytes [phase3_wave_finish [file join $out waveforms] $top $tag $simdir]} why]} {set result FAIL;set message $why}
        }
        if {$result eq "FAIL"} {
            incr failures
            set f [open [file join $out logs [format "%s_error.log" $tag]] w];puts $f $message;close $f
            puts stderr "FAILED: $tag -- $message"
        }
        set f [open [file join $out reports $tag.csv] w]
        puts $f "Case,Testbench,Group,ExpectedNegative,Result,CompletionTime,Capture,WDBBytes"
        puts $f "$tag,$top,$group,$negative,$result,$duration,$capture,$bytes"
        close $f
        puts "RESULT: $result -- $tag -- $duration"
        if {$result eq "FAIL"} {break}
    }
    close_project
    if {$failures} {error "Phase 4 tests failed"}
}
proc phase4_capture_begin {out top tag} {
    create_wave_config $tag
    set paths {}
    foreach name {clk rst ld scan_enable scan_in scan_out scan_feedback pc_d instr pc_q rf_instr q reference_q event_id generator_rst shift_count_v state c f1 f2 mode_select active_mode mode_valid pattern_done cpu_reset cpu_i_wait cpu_d_wait i_addr d_addr wr cpu_i_aVal cpu_d_aVal cpu_instr cpu_data cpu_data_inp cpu_xfer busFree scan_pc scan_instr scan_wr scan_i_addr scan_d_addr scan_i_aval scan_d_aval scan_data scan_xfer scan_busfree scan_feedback scan_out equivalent} {
        set p /$top/$name
        if {[llength [get_objects $p]]} {lappend paths $p}
    }
    if {$top eq "tb_core_scan_regression"} {
        foreach instance {U_CORE U_SCAN} {
            foreach name {RF_PCincd RF_instruction IF_RF_ld EX_A EX_B MM_result WB_C WB_wreg MM_wrmem PC} {
                set p /$top/$instance/$name
                if {[llength [get_objects $p]]} {lappend paths $p}
            }
        }
    }
    foreach p $paths {
        set radix hex
        if {[string match *mode* $p]} {set radix bin}
        if {[string match *count_v $p]} {set radix unsigned}
        add_wave -radix $radix $p;log_wave $p
    }
    open_vcd [file join $out waveforms $tag.vcd]
    foreach p $paths {log_vcd $p}
}

# Recognize both wait decoders before the original intentional stop.
proc phase4_core_run {top tag out} {
    set samples [open [file join $out reports [format "%s_samples.csv" $tag]] w]
    puts $samples "TimePS,PC,RF_PCincd,RF_instruction,IF_RF_ld,WB_wreg,MM_wrmem,Result"
    set checked 0;set stalled 0;set exit_seen 0
    for {set step 1} {$step<=1000} {incr step} {
        run 5 ns
        if {[get_value /$top/cpu_reset] ne "1"} {continue}
        if {$top eq "tb_core_scan_regression"} {
            set values {}
            foreach name {PC RF_PCincd RF_instruction IF_RF_ld WB_wreg MM_wrmem EX_A EX_B WB_C} {
                set a [get_value -radix hex /$top/U_CORE/$name]
                set b [get_value -radix hex /$top/U_SCAN/$name]
                if {$a ne $b} {close $samples;error "Core pipeline mismatch $name at step $step"}
                lappend values $a
            }
            if {[get_value /$top/U_CORE/IF_RF_ld] eq "1"} {incr stalled}
            puts $samples "[expr {$step*5000}],[join [lrange $values 0 5] ,],PASS"
            incr checked
        }
        set exception [string tolower [get_value /$top/U_CORE/exception]]
        set syscall [string tolower [get_value -radix hex /$top/U_CORE/syscall_n]]
        if {$exception eq "exwait" && $syscall eq "80000"} {
            set exit_seen 1
            if {$top eq "tb_core_scan_regression"} {
                foreach name {RF_PC exception syscall_n} {
                    if {[get_value /$top/U_CORE/$name] ne [get_value /$top/U_SCAN/$name]} {close $samples;error "Exit decoder mismatch"}
                }
                if {$checked<100 || ($tag eq "core_scan_stalls" && $stalled<1)} {close $samples;error "Insufficient execution/stall comparisons"}
                puts "CORE DIFFERENTIAL: PASS ($checked samples, $stalled stalls; both wait decoders equal)"
            }
            break
        }
    }
    close $samples
    if {!$exit_seen} {error "No expected wait decoder within 5 us"}
    # phi2 triggers the original assertion within the next half CPU cycle.
    run 10 ns
}
