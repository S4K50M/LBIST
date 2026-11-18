set root [file normalize [file join [file dirname [info script]] ../..]]
cd [file join $root Results Final FPGA_Analysis Timing_Closure work]
open_checkpoint [file join $::env(TEMP) vl405_timing m8_d82 full_lbist routed.dcp]
foreach c [get_cells irq_hold_delay_*] {
 puts "CELL $c INIT=[get_property INIT $c]"
 foreach pin {I0 O} {
  set net [get_nets -of_objects [get_pins $c/$pin]]
  puts "PIN $c/$pin NET=$net"
  puts "SINKS [get_pins -leaf -of_objects $net -filter {DIRECTION == IN}]"
 }
}
puts "IRQ3 SEGMENTS [get_nets -segments -of_objects [get_ports {irq[3]}]]"
puts "IRQ3 ACTUAL REG NET [get_nets -of_objects [get_pins {u_system/scan_cpu.u_cpu/PIPESTAGE_EXCP_EX_MM/MM_int_req_reg[3]/D}]]"
puts "INSERT BUFFER COMMANDS [info commands *buffer*]"
close_design
