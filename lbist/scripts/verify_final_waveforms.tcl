set root [file normalize [file join [file dirname [info script]] ../..]]
cd [file join $root Results Final work]
if {[catch {
 set count 0
 foreach group {Activity FaultDemo} {
  set folder [file join $root Results Final Verification $group waveforms]
  foreach cfg [glob [file join $folder *.wcfg]] {
   set db [file rootname $cfg].wdb
   if {![file exists $db] || [file size $db]==0} {error "Missing WDB: $db"}
   set f [open $cfg r];set layout [read $f];close $f
   if {![regexp [format {<db_ref path="%s"} [file tail $db]] $layout]} {error "Nonportable DB reference"}
   open_wave_database $db
   open_wave_config $cfg
   set objects [regexp -all -inline {fp_name="([^"]+)"} $layout]
   foreach {ignored path} $objects {
    if {[llength [get_objects $path]]!=1} {error "Missing recorded signal $path"}
   }
   puts "FINAL NATIVE WAVEFORM PASS: [file tail $cfg], [expr {[llength $objects]/2}] recorded signals"
   close_sim
   incr count
  }
 }
 if {$count!=6} {error "Expected five production and one fault waveform"}
 puts "FINAL NATIVE WAVEFORM AUDIT: 6/6 PASS"
} reason]} {puts stderr $reason;exit 1}
