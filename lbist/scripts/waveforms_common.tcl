# Vivado project-mode waveform generation, independent of verification runners.
set waveform_script_dir [file dirname [file normalize [info script]]]
proc generate_lbist_waveforms {selection} {
    global waveform_script_dir
    set root [file normalize [file join $waveform_script_dir ../..]]
    set project_dir [file join $root Results Phase2 work waveform_project]
    create_project -force lbist_waves $project_dir -part xc7a35tcpg236-1
    set_property target_language VHDL [current_project]
    foreach name {lfsr_16 phase_shifter plpf_optimized plpf_dynamic basic_controller} {
        add_files -fileset sources_1 [list [file join $root lbist rtl $name.vhd]]
    }
    foreach name {phase2_tb_pkg tb_lfsr_16 tb_phase_shifter tb_plpf_optimized tb_plpf_dynamic tb_phase2_integration tb_basic_controller tb_basic_integration} {
        add_files -fileset sim_1 [list [file join $root lbist tb $name.vhd]]
    }
    set_property file_type VHDL [get_files *.vhd]
    set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
    set cases {}
    if {$selection ne "basic"} {
        foreach top {tb_lfsr_16 tb_phase_shifter tb_plpf_optimized tb_plpf_dynamic tb_phase2_integration} {
            lappend cases [list phase2 $top $top {}]
        }
    }
    if {$selection ne "phase2"} {
        lappend cases {basic tb_basic_controller tb_basic_controller_L64_B20 20}
        foreach beta {0 8 16 20 28 36} {
            lappend cases [list basic tb_basic_integration tb_basic_integration_L64_B${beta} $beta]
        }
    }
    set summaries [dict create]
    foreach phase {phase2 basic} {
        if {$phase eq "phase2"} {set folder [file join $root Results Phase2 waveforms]} else {
            set folder [file join $root Results Phase3 Basic waveforms]
        }
        file mkdir $folder
        if {($phase eq "phase2" && $selection ne "basic") || ($phase eq "basic" && $selection ne "phase2")} {
            set channel [open [file join $folder waveform_summary.csv] w]
            puts $channel "Case,Testbench,Beta,CompletionTime,WDBBytes,VCDWindow,Result"
            dict set summaries $phase $channel
        }
    }
    set failures 0
    foreach case $cases {
        lassign $case phase top tag beta
        if {$phase eq "phase2"} {set folder [file join $root Results Phase2 waveforms]} else {
            set folder [file join $root Results Phase3 Basic waveforms]
        }
        puts "=== WAVEFORM: $tag ==="
        set_property top $top [get_filesets sim_1]
        if {$beta ne ""} {set generics [list CHAIN_LENGTH=64 BETA=$beta]} else {set generics {}}
        set_property generic $generics [get_filesets sim_1]
        update_compile_order -fileset sim_1
        set simdir [file join $project_dir lbist_waves.sim sim_1 behav xsim]
        set simlog [file join $simdir simulate.log]
        if {[file exists $simlog]} {file delete $simlog}
        set wcfg [file join $folder $tag.wcfg]
        set problem [catch {
            launch_simulation -simset sim_1 -mode behavioral
            create_wave_config $tag
            switch $top {
                tb_lfsr_16 {set signals {clk rst en state bit_out zero_state custom_state test_done}}
                tb_phase_shifter {set signals {clk rst en state c f1 f2 manual selected test_done}}
                tb_plpf_optimized {set signals {clk mode manual c f1 f2 past y valid chain test_done}}
                tb_plpf_dynamic {set signals {clk rst en state c f1 f2 mode active valid chain y test_done}}
                tb_phase2_integration {set signals {clk rst scan_enable state c f1 f2 mode active valid y chain test_done}}
                tb_basic_controller {set signals {clk rst scan_enable count mode done test_done}}
                tb_basic_integration {set signals {clk rst scan_enable count mode done state c f1 f2 active valid scan_in chain test_done}}
            }
            foreach name $signals {
                set path /$top/$name
                if {[llength [get_objects $path]] != 1} {error "Missing waveform signal: $path"}
                set radix default
                if {$name in {state zero_state custom_state selected chain}} {set radix hex}
                if {$name in {mode active}} {set radix bin}
                if {$name eq "count"} {set radix unsigned}
                if {$radix eq "default"} {add_wave $path} else {add_wave -radix $radix $path}
                log_wave $path
            }
            # A compact portable trace covers the initial few complete patterns.
            # Full-time activity remains available in the WDB.
            open_vcd [file join $folder $tag.vcd]
            foreach name $signals {if {$name ni {test_done manual count}} {log_vcd /$top/$name}}
            run 512 ns
            close_vcd
            set finished 0
            for {set step 0} {$step<2000} {incr step} {
                set done [string tolower [get_value /$top/test_done]]
                if {$done eq "true" || $done eq "1"} {set finished 1; break}
                run 1 us
            }
            if {!$finished} {error "Waveform simulation timeout"}
            save_wave_config $wcfg
        } message]
        catch {close_vcd}
        catch {close_sim}
        set text ""
        if {[file exists $simlog]} {
            file copy -force $simlog [file join $folder $tag.log]
            set f [open $simlog r]; set text [read $f]; close $f
        }
        set complete [regexp [format {[[]TB_COMPLETE[]] %s at ([^[:cntrl:]]+)} $top] $text whole duration]
        set result FAIL
        set size 0
        if {!$problem && $complete && ![regexp {[[]FAIL[]]|Failure:|Fatal:|ERROR:} $text]} {
            set database [file join $simdir ${top}_behav.wdb]
            if {[file exists $database] && [file exists $wcfg]} {
                file copy -force $database [file join $folder $tag.wdb]
                set size [file size [file join $folder $tag.wdb]]
                # Keep the WCFG/WDB pair relocatable together.
                set f [open $wcfg r]; set cfg [read $f]; close $f
                regsub -all {(<db_ref path=")[^"]*(")} $cfg [format {\1%s.wdb\2} $tag] cfg
                # Full WDB is retained; start with a readable 300-ns view.
                regsub {<zoom_setting>[^<]*</zoom_setting>} $cfg {<zoom_setting>
      <ZoomStartTime time="0.000 ns"></ZoomStartTime>
      <ZoomEndTime time="300.000 ns"></ZoomEndTime>
      <Cursor1Time time="0.000 ns"></Cursor1Time>
   </zoom_setting>} cfg
                set f [open $wcfg w]; puts $f $cfg; close $f
                set result PASS
            }
        }
        if {$result eq "FAIL"} {incr failures; set duration UNKNOWN; puts stderr "Waveform failed: $tag -- $message"}
        if {$beta eq ""} {set beta NA}
        set channel [dict get $summaries $phase]
        puts $channel "$tag,$top,$beta,$duration,$size,0..512 ns,$result"
        flush $channel
        puts "WAVEFORM RESULT: $result -- $tag ($size bytes)"
    }
    dict for {phase channel} $summaries {close $channel}
    close_project
    if {$failures} {error "$failures waveform simulations failed"}
    puts "WAVEFORM GENERATION: PASS ([llength $cases] captures)"
}
