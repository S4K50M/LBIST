set root [file normalize [file join [file dirname [info script]] ../..]]
if {[llength $argv]!=2} {error "Arguments: VCO_MULT CPU_DIVIDE"}
lassign $argv m d
set base [file join $root Results Final FPGA_Analysis Timing_Closure]
cd [file join $base work]
if {[catch {
 set count 0
 foreach group {Activity Fault} {
  foreach cfg [glob [file join $base verification m${m}_d${d} $group waveforms *.wcfg]] {
   set db [file rootname $cfg].wdb
   if {![file exists $db] || [file size $db]==0} {error "Missing WDB: $db"}
   set f [open $cfg r];set layout [read $f];close $f
   if {![regexp [format {<db_ref path="%s"} [file tail $db]] $layout]} {error "Nonportable database reference"}
   open_wave_database $db
   open_wave_config $cfg
   set objects [regexp -all -inline {fp_name="([^"]+)"} $layout]
   foreach {ignored path} $objects {
    if {[llength [get_objects $path]]!=1} {error "Missing recorded signal $path"}
   }
   puts "TIMING NATIVE WAVEFORM PASS: [file tail $cfg], [expr {[llength $objects]/2}] recorded signals"
   close_sim
   incr count
  }
 }
 if {$count!=6} {error "Expected five production and one fault waveform"}
 puts "TIMING NATIVE WAVEFORM AUDIT: 6/6 PASS"
} reason]} {puts stderr $reason;exit 1}
