set phase5_scripts [file dirname [file normalize [info script]]]
source [file join $phase5_scripts phase3_common.tcl]
set phase5_root [file normalize [file join $phase5_scripts ../..]]
file mkdir [file join $phase5_root Results Phase6A work]
cd [file join $phase5_root Results Phase6A work]
proc phase5_project {selection} {
    global phase5_root phase5_scripts
    set python [phase3_python]
    puts [exec $python -E [file join $phase5_scripts prepare_phase5a_rom.py]]
    set dir [file join $phase5_root Results Phase6A work project_$selection]
    create_project -force phase5a $dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    foreach name {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core cache instrcache rom ram io uart disk SDcard fpu sdram tb_cMIPS} {
        add_files -fileset sources_1 [list [file join $phase5_root cMIPS vhdl $name.vhd]]
    }
    foreach name {lfsr_16 phase_shifter plpf_dynamic basic_controller reg_IF_RF_scan lbist_test_controller} {
        add_files -fileset sources_1 [list [file join $phase5_root lbist rtl $name.vhd]]
    }
    foreach file [glob [file join $phase5_root lbist core_scan phase5a *.vhd]] {
        add_files -fileset sources_1 [list $file]
        set_property file_type {VHDL 2008} [get_files [list $file]]
    }
    set file [file join $phase5_root lbist core_scan core_scan_test.vhd]
    add_files -fileset sources_1 [list $file]
    set_property file_type {VHDL 2008} [get_files [list $file]]
    foreach name {phase2_tb_pkg phase5a_rom_pkg phase5a_processor_check tb_lbist_test_controller tb_core_scan_isolation tb_core_scan_shift_capture tb_core_fault_regression} {
        set file [file join $phase5_root lbist tb $name.vhd]
        if {[file exists $file]} {add_files -fileset sim_1 [list $file]}
    }

    foreach rel {lbist/rtl/misr_16.vhd lbist/rtl/misr_signature_checker.vhd lbist/rtl/lbist_misr_top.vhd lbist/core_scan/fault_injection/core_scan_fault.vhd} {
        set f [file join $phase5_root $rel];add_files -fileset sources_1 [list $f]
        set_property file_type {VHDL 2008} [get_files [list $f]]
    }
    foreach name {phase5bc_golden_pkg phase5bc_processor_check tb_misr_16 tb_misr_integration tb_lbist_fault_injection tb_phase6a_controller_integration tb_phase6a_fault_comparison} {
        add_files -fileset sim_1 [list [file join $phase5_root lbist tb $name.vhd]]
    }
    foreach n {swap_controller moving_controller lbist_pattern_router phase6a_safe_misr} {
      add_files -fileset sources_1 [list [file join $phase5_root lbist rtl $n.vhd]]
    }
    foreach n {phase6a_golden_pkg phase6a_processor_check tb_phase6a_controller_integration tb_phase6a_fault_comparison tb_phase6a_misr_safety} {
      add_files -fileset sim_1 [list [file join $phase5_root lbist tb $n.vhd]]
    }
    set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
}
proc phase5_case {group top tag generics {capture 1} {cpu 0}} {
    global phase5_root
    set phase Phase6A;set out [file join $phase5_root Results $phase $group]
    set cpu_exit [expr {$top in {tb_core_fault_regression tb_cMIPS}}]
    file mkdir [file join $out logs] [file join $out reports] [file join $out waveforms]
    set_property top $top [get_filesets sim_1]
    set_property generic $generics [get_filesets sim_1]
    update_compile_order -fileset sim_1
    set project_dir [get_property DIRECTORY [current_project]]
    set simdir [file join $project_dir phase5a.sim sim_1 behav xsim]
    file mkdir $simdir
    if {$cpu} {
        foreach image {prog.bin data.bin input.data serial.inp} {
            file copy -force [file join $phase5_root cMIPS $image] [file join $simdir $image]
        }
    }
    set simlog [file join $simdir simulate.log]
    if {[file exists $simlog]} {file delete $simlog}
    set problem [catch {
        launch_simulation -mode behavioral
        if {$capture} {phase5_capture $out $top $tag}
        if {$cpu_exit} {
            phase5_cpu_run $top $tag $out
        } else {
            set done 0
            for {set k 0} {$k<20000} {incr k} {
                set channel [open $simlog r];set progress [read $channel];close $channel
                if {[regexp {[[]FAIL[]]|Failure:|Fatal:|ERROR:} $progress]} {error "XSim assertion/error; do not resume a failed simulation"}
                if {[string tolower [get_value /$top/test_done]] in {true 1}} {set done 1;break}
                run 1 us
            }
            if {!$done} {error "Timeout without completion"}
        }
        if {$capture} {save_wave_config [file join $out waveforms $tag.wcfg]}
    } message]
    catch {close_vcd};catch {close_sim}
    set text ""
    if {[file exists $simlog]} {
        set f [open $simlog r];set text [read $f];close $f
        file copy -force $simlog [file join $out logs $tag.log]
        if {$capture} {file copy -force $simlog [file join $out waveforms $tag.log]}
    }
    foreach name {xvhdl.log elaborate.log} {
        set file [file join $simdir $name]
        if {[file exists $file]} {file copy -force $file [file join $out logs [format "%s_%s" $tag $name]]}
    }
    set result FAIL;set duration UNKNOWN;set bytes 0
    if {!$problem && !$cpu_exit && [regexp [format {[[]TB_COMPLETE[]] %s at ([0-9]+ ps)} $top] $text m duration] && ![regexp {[[]FAIL[]]|Failure:|Fatal:|ERROR:} $text]} {set result PASS}
    if {!$problem && $cpu_exit && [regexp {Time: ([0-9]+) ns[^\n]*RF_STOP_SIMULATION} $text m ns] && [regexp {cMIPS BREAKPOINT at PC=00000038} $text] && ![regexp {[[]FAIL[]]|SIMULATION ABORTED|Fatal:|ERROR:} $text]} {
        set result PASS;set duration "[expr {$ns*1000}] ps"
    }
    if {$result eq "PASS" && $capture} {
        set bytes [phase3_wave_finish [file join $out waveforms] $top $tag $simdir]
    }
    set f [open [file join $out reports $tag.csv] w]
    puts $f "Case,Testbench,Group,Result,CompletionTime,Capture,WDBBytes"
    puts $f "$tag,$top,$group,$result,$duration,$capture,$bytes";close $f
    puts "PHASE 5A RESULT: $result -- $tag -- $duration"
    if {$result ne "PASS"} {error "$tag failed: $message"}
}
proc phase5_capture {out top tag} {
    create_wave_config $tag
    set paths [get_objects /$top/*]
    if {$top in {tb_core_scan_isolation tb_core_scan_shift_capture tb_misr_integration tb_lbist_fault_injection tb_phase6a_controller_integration tb_phase6a_fault_comparison}} {set paths [get_objects /$top/engine/*]}
    set selected {}
    foreach p $paths {
        # Scalars/vectors only; real RTL state probes are explicitly exported.
        set name [file tail $p]
        if {$name in {clk rst start pause abort_test ack ready tm se ce pd done error_status state shift_count_v pattern_index test_mode scan_enable capture_enable core_tm core_se core_ce bad_command exit_attempt isolation_ack protocol_error test_phase scan_in scan_out scan_feedback protected_state scan_state pc_observe mode_select active_mode generator_state current_bit future1 future2 pattern_done event_id i_addr d_addr i_aval d_aval wr memory_write_attempt register_write_attempt register_write_actual protected_equal enable clear response_bit capture_ready fabric_idle bsel busfree signature misr_enable signature_valid signature_match fault_detected phase pos patterns unload response q valid match detected scenario err}} {
            lappend selected $p
            set radix hex
            if {$name in {test_phase state mode_select active_mode}} {set radix bin}
            if {$name in {shift_count_v pattern_index}} {set radix unsigned}
            add_wave -radix $radix $p;log_wave $p
        }
    }
    if {$top in {tb_core_scan_isolation tb_core_scan_shift_capture tb_misr_integration tb_lbist_fault_injection tb_phase6a_controller_integration tb_phase6a_fault_comparison}} {
        foreach name {clk rst phi1 phi2 isolation_hold phi1_sync phi2_sync ack_sync isolation_ack legal_capture increment_operand PCincd capture_word RF_PCincd RF_instruction} {
            set p /$top/engine/dut/$name
            if {[llength [get_objects $p]]==1} {
                lappend selected $p
                add_wave -radix hex $p;log_wave $p
            }
        }
    }
    open_vcd [file join $out waveforms $tag.vcd]
    foreach p $selected {log_vcd $p}
}

proc phase5_cpu_run {top tag out} {
    set samples [open [file join $out reports [format "%s_samples.csv" $tag]] w]
    puts $samples "TimePS,PC,RF_PCincd,RF_instruction,IF_RF_ld,WB_wreg,MM_wrmem,Result"
    set checked 0;set stalled 0;set exit_seen 0
    for {set step 1} {$step<=1000} {incr step} {
        run 5 ns
        if {[get_value /$top/cpu_reset] ne "1"} {continue}
        if {$top eq "tb_core_fault_regression"} {
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
            if {$top eq "tb_core_fault_regression"} {
                foreach name {RF_PC exception syscall_n} {
                    if {[get_value /$top/U_CORE/$name] ne [get_value /$top/U_SCAN/$name]} {close $samples;error "Exit decoder mismatch"}
                }
                if {$checked<100 || ($tag eq "functional_stalls" && $stalled<1)} {close $samples;error "Insufficient execution/stall comparisons"}
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

# Batch file addition avoids repeated native project updates.
proc phase5_project {selection} {
 global phase5_root
 set dir [file join $phase5_root Results Phase6A work project_$selection]
 if {[info exists ::env(PHASE6A_NATIVE_ROOT)]} {set dir [file join $::env(PHASE6A_NATIVE_ROOT) project_$selection]}
 create_project -force phase5a $dir -part xc7a35tcpg236-1
 set sources {}
 foreach n {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core cache instrcache rom ram io uart disk SDcard fpu sdram tb_cMIPS} {
  lappend sources [file join $phase5_root cMIPS vhdl $n.vhd]
 }
 foreach n {lfsr_16 phase_shifter plpf_dynamic basic_controller swap_controller moving_controller reg_IF_RF_scan lbist_test_controller misr_16 misr_signature_checker lbist_misr_top lbist_pattern_router phase6a_safe_misr} {
  lappend sources [file join $phase5_root lbist rtl $n.vhd]
 }
 set modern [concat [glob [file join $phase5_root lbist core_scan phase5a *.vhd]] [list [file join $phase5_root lbist core_scan core_scan_test.vhd] [file join $phase5_root lbist core_scan fault_injection core_scan_fault.vhd]]]
 add_files -fileset sources_1 [concat $sources $modern]
 set_property file_type {VHDL 2008} [get_files $modern]
 set benches {}
 foreach n {phase2_tb_pkg phase5a_rom_pkg phase6a_golden_pkg phase6a_processor_check tb_phase6a_controller_integration tb_phase6a_fault_comparison tb_phase6a_misr_safety tb_core_fault_regression tb_misr_16} {
  lappend benches [file join $phase5_root lbist tb $n.vhd]
 }
 add_files -fileset sim_1 $benches
 set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
}
