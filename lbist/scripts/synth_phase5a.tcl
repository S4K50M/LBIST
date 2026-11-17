source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
if {[catch {
    phase5_project synthesis
    add_files -fileset sources_1 [list [file join $phase5_root lbist rtl phase5a_ifrf_subsystem.vhd]]
    set report_dir [file join $phase5_root Results Phase5A Controller reports]
    set tops {lbist_test_controller phase5a_ifrf_subsystem core_scan_test}
    if {[info exists ::phase5a_synth_tops]} {set tops $::phase5a_synth_tops}
    set rows {}
    set summary [file join $phase5_root Results Phase5A phase5a_synthesis.csv]
    if {[file exists $summary]} {
        set f [open $summary r];set previous [split [string trim [read $f]] "\n"];close $f
        foreach row [lrange $previous 1 end] {
            if {[lindex [split $row ,] 0] ni $tops} {lappend rows [string trim $row]}
        }
    }
    foreach top $tops {
        synth_design -mode out_of_context -top $top -part xc7a35tcpg236-1
        set ff 0;set lut 0;set latch 0;set rams 0
        set latch_rows {}
        foreach cell [get_cells -hierarchical] {
            set ref [get_property REF_NAME $cell]
            if {[string match FD* $ref]} {incr ff}
            if {[string match LUT* $ref]} {incr lut}
            if {[string match LD* $ref]} {incr latch;lappend latch_rows "$cell,$ref"}
            if {[string match RAM* $ref]} {incr rams}
        }
        report_utilization -file [file join $report_dir $top.utilization.rpt]
        set f [open [file join $report_dir $top.latches.csv] w]
        puts $f "Cell,Primitive";foreach row $latch_rows {puts $f $row};close $f
        lappend rows "$top,$ff,$lut,$latch,$rams,PASS"
        puts "PHASE 5A SYNTHESIS: $top FF=$ff LUT=$lut latch=$latch RAM=$rams"
        close_design
    }
    set f [open [file join $phase5_root Results Phase5A phase5a_synthesis.csv] w]
    puts $f "Top,FlipFlops,LUTs,Latches,RAMPrimitives,Result"
    foreach row $rows {puts $f $row};close $f
    close_project
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
