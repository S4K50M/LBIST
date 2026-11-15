# Native Vivado static-view validation; does not rerun any HDL simulation.
set wave_verify_root [file normalize [file join [file dirname [info script]] ../..]]
set wave_checked 0
foreach relative {Results/Phase2/waveforms Results/Phase3/Basic/waveforms} {
    set folder [file join $wave_verify_root $relative]
    set f [open [file join $folder waveform_summary.csv] r]
    set rows [split [string trim [read $f]] "\n"]; close $f
    foreach row [lrange $rows 1 end] {
        set fields [split [string trim $row] ,]
        lassign $fields tag top beta duration size window result
        if {$result ne "PASS"} {error "Capture has not passed: $tag"}
        open_wave_database [file join $folder $tag.wdb]
        open_wave_config [file join $folder $tag.wcfg]
        if {[llength [get_objects /$top/clk]] != 1} {error "Missing clock in saved database: $tag"}
        if {[string match tb_basic* $top] && [llength [get_objects /$top/count]] != 1} {
            error "Missing integer shift counter in native database: $tag"
        }
        close_sim
        incr wave_checked
        puts "STATIC WAVEFORM CHECK: PASS -- $tag"
    }
}
if {$wave_checked != 12} {error "Expected 12 waveform captures, found $wave_checked"}
puts "STATIC WAVEFORM VALIDATION: PASS ($wave_checked captures)"
