# Native Vivado static-view validation; does not rerun any HDL simulation.
set wave_verify_root [file normalize [file join [file dirname [info script]] ../..]]
set wave_checked 0
foreach relative {Results/Phase2/waveforms Results/Phase3/Basic/waveforms Results/Phase3/Swap/waveforms Results/Phase3/Moving/waveforms Results/Phase3/Comparison/waveforms} {
    if {[info exists ::WAVEFORM_VERIFY_SCOPE] && $::WAVEFORM_VERIFY_SCOPE eq "phase3" &&
        $relative in {Results/Phase2/waveforms Results/Phase3/Basic/waveforms}} {continue}
    set folder [file join $wave_verify_root $relative]
    if {![file exists [file join $folder waveform_summary.csv]]} {continue}
    set f [open [file join $folder waveform_summary.csv] r]
    set rows [split [string trim [read $f]] "\n"]; close $f
    foreach row [lrange $rows 1 end] {
        set fields [split [string trim $row] ,]
        lassign $fields tag top beta duration size window result
        if {$result ne "PASS"} {error "Capture has not passed: $tag"}
        set db [file join $folder $tag.wdb]
        set cfg [file join $folder $tag.wcfg]
        if {![file exists $db] || ![file exists $cfg]} {error "Missing WDB/WCFG for $tag; regenerate locally"}
        set cf [open $cfg r]; set cfg_text [read $cf]; close $cf
        if {![regexp {<db_ref path="([^"]+)"} $cfg_text whole referenced] || $referenced ne "$tag.wdb"} {error "Wrong WCFG database reference for $tag"}
        if {[file size $db] != $size} {error "Database byte count differs from capture manifest: $tag"}
        open_wave_database $db
        open_wave_config $cfg
        set prefixes [list /$top]
        if {$top in {tb_swap_controller tb_moving_controller tb_swap_integration tb_moving_integration}} {set prefixes [list /$top/engine]}
        if {$top eq "tb_phase3_comparison"} {
            set prefixes [list /$top/direct_engine /$top/low_engine /$top/basic_engine /$top/swap_engine /$top/moving_engine]
        }
        foreach prefix $prefixes {
            if {[llength [get_objects $prefix/clk]] != 1} {error "Missing clock in saved database: $tag"}
            if {$prefix ne "/$top"} {
                foreach signal {rst scan_enable shift_count_v pattern_index moving_position_v mode_select pattern_done mode_0 mode_1 mode_2 mode_3 alpha_0 beta_v gamma_0 alpha_debug gamma_debug} {
                    if {[llength [get_objects $prefix/$signal]] != 1} {error "Missing saved signal: $prefix/$signal"}
                }
                if {$top ni {tb_swap_controller tb_moving_controller}} {
                    foreach signal {state current_bits future1_bits future2_bits active_mode mode_valid scan_in past_bits chain_flat} {
                        if {[llength [get_objects $prefix/$signal]] != 1} {error "Missing integration signal: $prefix/$signal"}
                    }
                }
            }
        }
        if {[string match tb_basic* $top] && [llength [get_objects /$top/count]] != 1} {
            error "Missing integer shift counter in native database: $tag"
        }
        close_sim
        incr wave_checked
        puts "STATIC WAVEFORM CHECK: PASS -- $tag"
    }
}
set minimum_captures 12
if {[file exists [file join $wave_verify_root Results Phase3 Comparison waveforms waveform_summary.csv]]} {set minimum_captures 17}
if {[info exists ::WAVEFORM_VERIFY_SCOPE] && $::WAVEFORM_VERIFY_SCOPE eq "phase3"} {set minimum_captures 5}
if {$wave_checked < $minimum_captures} {error "Insufficient native waveform captures: $wave_checked"}
# Reopening a database proves availability, not behavior. Independently inspect VCD
# transitions, pre/post-edge modes, pauses, FF contents and annotation times.
if {[file exists [file join $wave_verify_root Results Phase3 Comparison reports phase3_waveform_summary.csv]]} {
    if {![llength [info commands phase3_python]]} {
        source [file join $wave_verify_root lbist scripts phase3_common.tcl]
    }
    set python [phase3_python]
    puts [exec $python -E [file join $wave_verify_root lbist scripts phase3_waveform_analysis.py] --verify-only]
}
puts "STATIC WAVEFORM VALIDATION: PASS ($wave_checked captures)"
