set final_scripts [file dirname [file normalize [info script]]]
set final_root [file normalize [file join $final_scripts ../..]]
set final_out [file join $final_root Results Final FPGA_Analysis]
file mkdir $final_out [file join $final_root Results Final work]
cd [file join $final_root Results Final work]
set part xc7a35tcpg236-1
if {[llength [get_parts -quiet $part]]!=1} {error "Required Artix-7 part unavailable"}
set configurations {baseline scan_enabled full_lbist}
set failed 0
if {[info exists ::final_configuration]} {set configurations [list $::final_configuration]}
foreach config $configurations {
 set index [lsearch -exact {baseline scan_enabled full_lbist} $config]
 if {$index<0} {error "Invalid final configuration"}
 set out [file join $final_out $config];file mkdir $out
 set status_file [open [file join $out status.csv] w];puts $status_file "Configuration,Stage,Status,Detail";flush $status_file
 set stage setup
 if {[catch {
  set cache [file join $::env(TEMP) vl405_final_fpga $config]
  create_project -force final_fpga $cache -part $part
  set_property target_language VHDL [current_project]
  set sources {}
  foreach name {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core} {
   lappend sources [file join $final_root cMIPS vhdl $name.vhd]
  }
  foreach name {lfsr_16 phase_shifter plpf_dynamic basic_controller swap_controller moving_controller reg_IF_RF_scan lbist_test_controller misr_16 lbist_pattern_router phase6a_safe_misr} {
   lappend sources [file join $final_root lbist rtl $name.vhd]
  }
  set modern [concat [glob [file join $final_root lbist core_scan phase5a *.vhd]] [list [file join $final_root lbist core_scan core_scan_test.vhd]]]
  set wrappers {}
  foreach name {final_processor_system final_clock_tree final_fpga_top} {lappend wrappers [file join $final_root lbist final $name.vhd]}
  add_files -fileset sources_1 [concat $sources $modern $wrappers]
  set_property file_type {VHDL 2008} [get_files $modern]
  add_files -fileset constrs_1 [list [file join $final_root lbist final final_primary.xdc]]
  set_property top final_fpga_top [get_filesets sources_1]
  set stage synthesis
  synth_design -mode out_of_context -flatten_hierarchy rebuilt -top final_fpga_top -part $part -generic DESIGN_CONFIG=$index
  puts $status_file "$config,synthesis,PASS,actual native synthesis";flush $status_file
  set routers [get_cells -hier -quiet -filter {REF_NAME =~ *lbist_pattern_router* || ORIG_REF_NAME =~ *lbist_pattern_router*}]
  if {($index==2 && [llength $routers]!=1) || ($index!=2 && [llength $routers]!=0)} {error "Incorrect elaborated configuration/router count"}
  report_utilization -file [file join $out synthesis_utilization.rpt]
  write_checkpoint -force [file join $cache synthesis.dcp]
  set mmcm [get_cells -hier -filter {REF_NAME =~ MMCME2*}]
  if {[llength $mmcm]!=1} {error "Expected one common phase-generating MMCM"}
  # Clock constraints are derived from the actual MMCM, not unrelated primaries.
  if {[llength [get_clocks -quiet board_clk]]!=1} {
   read_xdc [file join $final_root lbist final final_primary.xdc]
  }
  set cpu_clock [get_clocks -of_objects [get_pins $mmcm/CLKOUT0]]
  if {[llength $cpu_clock]!=1} {error "MMCM clock derivation missing"}
  foreach pin {CLKOUT0 CLKOUT1 CLKOUT2} {
   set clock [get_clocks -of_objects [get_pins $mmcm/$pin]]
   puts "RELATED CLOCK $pin: $clock period=[get_property PERIOD $clock] waveform=[get_property WAVEFORM $clock]"
   if {abs([get_property PERIOD $clock]-20.0)>0.001} {error "Incorrect CPU phase frequency"}
  }
  set_clock_uncertainty 0.100 [get_clocks]
  set data_inputs [get_ports -filter {DIRECTION == IN && NAME != board_clk && NAME != reset_button}]
  set_input_delay -clock $cpu_clock -max 2.000 $data_inputs
  set_input_delay -clock $cpu_clock -min 0.500 $data_inputs
  set_output_delay -clock $cpu_clock -max 2.000 [get_ports -filter {DIRECTION == OUT}]
  set_output_delay -clock $cpu_clock -min 0.500 [get_ports -filter {DIRECTION == OUT}]
  set reset_pins [get_pins -hier -filter {REF_PIN_NAME == CLR || REF_PIN_NAME == PRE || REF_PIN_NAME == R || REF_PIN_NAME == S || REF_PIN_NAME == RST}]
  set_false_path -from [get_ports reset_button] -to $reset_pins
  report_clocks -file [file join $out clocks.rpt]
  report_timing_summary -report_unconstrained -file [file join $out synthesis_timing.rpt]
  set stage implementation
  opt_design
  place_design
  phys_opt_design
  route_design
  puts $status_file "$config,implementation,PASS,placement and routing completed";flush $status_file
  write_checkpoint -force [file join $cache routed.dcp]
  report_utilization -file [file join $out routed_utilization.rpt]
  report_timing_summary -report_unconstrained -file [file join $out routed_timing.rpt]
  report_clock_interaction -file [file join $out clock_interaction.rpt]
  report_drc -file [file join $out drc.rpt]
  set stage power
  catch {set_operating_conditions -ambient_temp 25 -process typical}
  report_power -file [file join $out power_assumption_based.rpt]
  report_switching_activity -file [file join $out switching_assumptions.rpt] [get_nets -hier]
  set f [open [file join $out resources.csv] w];puts $f "Configuration,FF,LUT,LUTRAM,BRAM,DSP,Carry,Latches"
  set ff 0;set lut 0;set ram 0;set bram 0;set dsp 0;set carry 0;set latch 0
  foreach cell [get_cells -hier] {
   set ref [get_property REF_NAME $cell]
   if {[string match FD* $ref]} {incr ff}
   if {[string match LUT* $ref]} {incr lut}
   if {[string match RAM* $ref] && ![string match RAMB* $ref]} {incr ram}
   if {[string match RAMB* $ref]} {incr bram}
   if {[string match DSP* $ref]} {incr dsp}
   if {[string match CARRY* $ref]} {incr carry}
   if {[string match LD* $ref]} {incr latch}
  }
  puts $f "$config,$ff,$lut,$ram,$bram,$dsp,$carry,$latch";close $f
  puts $status_file "$config,power,PASS,assumption-based initial estimate"
  close_project
 } reason]} {
  set failed 1
  puts $status_file "$config,$stage,FAIL,[string map {, ; \n { }} $reason]"
  puts stderr "FINAL FPGA $config $stage FAILED: $reason"
  catch {close_project}
 }
 close $status_file
}
if {$failed} {exit 1}
