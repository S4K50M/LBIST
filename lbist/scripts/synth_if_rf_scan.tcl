set root [file normalize [file join [file dirname [info script]] ../..]]
file mkdir [file join $root Results Phase4 work]
cd [file join $root Results Phase4 work]
set out [file join $root Results Phase4 IF_RF reports]
file mkdir $out
if {[catch {
    set rows {}
    foreach top {reg_IF_RF reg_IF_RF_scan} {
        create_project -in_memory -part xc7a35tcpg236-1
        read_vhdl [list [file join $root cMIPS vhdl packageWires.vhd] [file join $root cMIPS vhdl pipestages.vhd] [file join $root lbist rtl reg_IF_RF_scan.vhd]]
        synth_design -mode out_of_context -top $top -part xc7a35tcpg236-1
        set ff 0;set lut 0;set latch 0;set types [dict create]
        foreach cell [get_cells -hierarchical] {
            set ref [get_property REF_NAME $cell]
            if {[string match FD* $ref]} {incr ff;dict incr types $ref}
            if {[string match LD* $ref]} {incr latch}
            if {[string match LUT* $ref]} {incr lut}
        }
        report_utilization -file [file join $out $top.utilization.rpt]
        write_checkpoint -force [file join $root Results Phase4 work $top.dcp]
        if {$ff!=64 || $latch!=0} {error "Unexpected storage: $top FF=$ff latch=$latch"}
        lappend rows "$top,$ff,$lut,$latch,[dict keys $types],PASS"
        close_project
    }
    set f [open [file join $out synthesis_comparison.csv] w]
    puts $f "Top,FlipFlops,LUTs,Latches,FFPrimitiveTypes,Result"
    foreach row $rows {puts $f $row};close $f
    puts "REGISTER SYNTHESIS: PASS -- exactly 64 FFs in each implementation"
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
