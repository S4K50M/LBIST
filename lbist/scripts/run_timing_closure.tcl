# vivado -mode batch -source ... -tclargs full_lbist 8 82
# Every candidate is synthesized and physically implemented independently.
set root [file normalize [file join [file dirname [info script]] ../..]]
if {[llength $argv]!=3} {error "Arguments: baseline|scan_enabled|full_lbist VCO_MULT CPU_DIVIDE"}
lassign $argv config mult divide
set index [lsearch -exact {baseline scan_enabled full_lbist} $config]
if {$index<0 || ![string is integer -strict $mult] || ![string is integer -strict $divide] || $mult<6 || $mult>12 || $divide<4 || $divide>84 || $divide%2!=0} {error "Invalid MMCM VCO/quarter-duty/phase configuration"}
set period [expr {10.0*$divide/$mult}]
set tag m${mult}_d${divide}
set base [file join $root Results Final FPGA_Analysis Timing_Closure]
set out [file join $base sweep $tag $config];file mkdir $out [file join $base work]
cd [file join $base work]
set cache [file join $::env(TEMP) vl405_timing $tag $config]
set f [open [file join $out status.csv] w];puts $f "Stage,Status,Detail";flush $f
set stage setup
if {[catch {
 if {[llength [get_parts -quiet xc7a35tcpg236-1]]!=1} {error "Requested Artix-7 part not installed"}
 create_project -force timing_closure $cache -part xc7a35tcpg236-1
 set_property target_language VHDL [current_project]
 set files {}
 foreach n {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core} {lappend files [file join $root cMIPS vhdl $n.vhd]}
 foreach n {lfsr_16 phase_shifter plpf_dynamic basic_controller swap_controller moving_controller reg_IF_RF_scan lbist_test_controller misr_16 lbist_pattern_router phase6a_safe_misr} {lappend files [file join $root lbist rtl $n.vhd]}
 set modern [concat [glob [file join $root lbist core_scan phase5a *.vhd]] [list [file join $root lbist core_scan core_scan_test.vhd]]]
 foreach n {final_processor_system final_clock_tree final_fpga_top} {lappend files [file join $root lbist final $n.vhd]}
 add_files -fileset sources_1 [concat $files $modern]
 set_property file_type {VHDL 2008} [get_files $modern]
 add_files -fileset constrs_1 [list [file join $root lbist final final_primary.xdc]]
 set_property top final_fpga_top [get_filesets sources_1]
 set stage synthesis
 synth_design -mode out_of_context -flatten_hierarchy rebuilt -top final_fpga_top -part xc7a35tcpg236-1 -generic [list DESIGN_CONFIG=$index CPU_VCO_MULT=$mult CPU_CLK_DIVIDE=$divide]
 puts $f "synthesis,PASS,native completed";flush $f
 report_utilization -file [file join $out synthesis_utilization.rpt]
 set mmcm [get_cells -hier -filter {REF_NAME =~ MMCME2*}]
 foreach pin {CLKOUT0 CLKOUT1 CLKOUT2} {
  set c [get_clocks -of_objects [get_pins $mmcm/$pin]]
  if {[llength $c]!=1 || abs([get_property PERIOD $c]-$period)>0.002} {error "Unexpected generated frequency"}
  puts "GENERATED $pin: $c [get_property PERIOD $c] [get_property WAVEFORM $c]"
 }
 # OOC environment: external provider launches at the ideal CPU phase origin.
 # This prevents incorrectly including the MMCM's negative compensation latency
 # in an external input's launch clock. All CPU phases remain related and timed.
 create_clock -name virtual_cpu_io -period $period -waveform [list 0 [expr {$period/2.0}]]
 # Use the device/MMCM-derived jitter and phase uncertainty; a blanket
 # smaller override can understate generated-to-virtual clock uncertainty.
 set inputs [get_ports -filter {DIRECTION == IN && NAME != board_clk && NAME != reset_button}]
 set_input_delay -clock virtual_cpu_io -max 2.000 $inputs
 set_input_delay -clock virtual_cpu_io -min 0.500 $inputs
 set_output_delay -clock virtual_cpu_io -max 2.000 [get_ports -filter {DIRECTION == OUT}]
 set_output_delay -clock virtual_cpu_io -min 0.500 [get_ports -filter {DIRECTION == OUT}]
 # Asynchronous assertion only; synchronized reset release is still timed.
 set reset_pins [get_pins -hier -filter {REF_PIN_NAME == CLR || REF_PIN_NAME == PRE || REF_PIN_NAME == RST}]
 set_false_path -from [get_ports reset_button] -to $reset_pins
 report_clocks -file [file join $out clocks.rpt]
 write_xdc -force [file join $out applied_constraints.xdc]
 write_checkpoint -force [file join $cache synthesis.dcp]
 set stage implementation
 opt_design
 # Demand-driven physical input hold repair is a separate reproducible ECO
 # step (close_timing_io.tcl), with checked hierarchy-local connections.
 place_design
 phys_opt_design
 route_design
 # Real hold optimization inserts physical delay; it adds no timing exceptions.
 set worst_hold [get_timing_paths -delay_type min -max_paths 1]
 if {[llength $worst_hold] && [get_property SLACK $worst_hold]<0} {
  phys_opt_design -aggressive_hold_fix
  route_design
 }
 puts $f "implementation,PASS,native placement and routing completed";flush $f
 write_checkpoint -force [file join $cache routed.dcp]
 report_utilization -file [file join $out routed_utilization.rpt]
 report_timing_summary -report_unconstrained -file [file join $out routed_timing.rpt]
 report_timing -delay_type min -max_paths 20 -file [file join $out hold_paths.rpt]
 report_timing -delay_type max -max_paths 20 -file [file join $out setup_paths.rpt]
 report_clock_interaction -file [file join $out clock_interaction.rpt]
 report_route_status -file [file join $out route_status.rpt]
 report_drc -file [file join $out drc.rpt]
 set tf [open [file join $out clock_configuration.csv] w]
 puts $tf "Configuration,InputMHz,Mult,InputDivide,OutputDivide,VCOMHz,CPUMHz,PeriodNS,IRQHoldBuffers"
 puts $tf "$config,100,$mult,1,$divide,[expr {100*$mult}],[expr {100.0*$mult/$divide}],$period,0";close $tf
 puts $f "reports,PASS,read timing summary separately; successful routing does not imply closure"
 close_project
} reason]} {
 puts $f "$stage,FAIL,[string map {, ; \n { }} $reason]";close $f
 puts stderr "TIMING CLOSURE RUN FAILED: $reason";exit 1
}
close $f
puts "TIMING CLOSURE IMPLEMENTATION FINISHED: $config $tag; inspect setup AND hold"
