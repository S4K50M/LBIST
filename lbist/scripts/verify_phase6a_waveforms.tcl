source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 set checked 0
 foreach group {Router Faults} {
  foreach report [glob [file join $phase5_root Results Phase6A $group reports *.csv]] {
   set f [open $report];set lines [split [string trim [read $f]] "\n"];close $f
   set fields [split [lindex $lines 1] ,]
   if {[lindex $fields 5] ne "1"} {continue}
   lassign $fields tag top
   set folder [file join $phase5_root Results Phase6A $group waveforms]
   set db [file join $folder $tag.wdb];set cfg [file join $folder $tag.wcfg]
   if {![file exists $db] || ![file size $db]} {error "Missing native capture $tag"}
   set f [open $cfg];set layout [read $f];close $f
   if {![regexp [format {<db_ref path="%s.wdb"} $tag] $layout]} {error "Wrong database reference $tag"}
   open_wave_database $db;open_wave_config $cfg
   set prefix /$top
   if {$group eq "Faults"} {append prefix /engine}
   if {[llength [get_objects $prefix/clk]]!=1} {error "Missing actual clock $tag"}
   close_sim;incr checked
   puts "PHASE6A NATIVE WAVEFORM PASS: $tag"
  }
 }
 puts "PHASE6A NATIVE CAPTURES VERIFIED: $checked"
} message]} {puts stderr $message;exit 1}
