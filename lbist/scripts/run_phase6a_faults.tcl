source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 set first 0;set last 11
 if {[info exists ::config_first]} {set first $::config_first}
 if {[info exists ::config_last]} {set last $::config_last}
 phase5_project campaign_$first
 set approaches {0 1 2 3 4 2 2 3 3 4 4 4}
 set betas {20 20 20 16 20 4 12 4 12 4 12 19}
 set ids {}
 for {set config $first} {$config<=$last} {incr config} {lappend ids $config}
 if {[info exists ::configs]} {set ids $::configs}
 set fault_end 16
 if {[info exists ::fault_last]} {set fault_end $::fault_last}
 foreach config $ids {
  set approach [lindex $approaches $config];set beta [lindex $betas $config]
  for {set fault 0} {$fault<=$fault_end} {incr fault} {
   set tag [format c%d_f%d $config $fault]
   if {[info exists ::resume_verified] && $::resume_verified} {
    set report [file join $phase5_root Results Phase6A Faults reports $tag.csv]
    set log [file join $phase5_root Results Phase6A Faults logs $tag.log]
    if {[file exists $report] && [file exists $log]} {
     set f [open $report];set saved [read $f];close $f
     set f [open $log];set logged [read $f];close $f
     set config_line [format {[CONFIG] %d,%d,%d} $config $approach $beta]
     if {[string first ",PASS," $saved]>=0 && [string first $config_line $logged]>=0 &&
         [string first {[TB_COMPLETE] tb_phase6a_fault_comparison} $logged]>=0 &&
         [regexp -all {[[]SIGNATURE[]]} $logged]==256 && ![regexp {[[]FAIL[]]|Failure:|Fatal:} $logged]} {
      puts "RESUME VERIFIED COMPLETE CASE: $tag";continue
     }
    }
   }
   set capture [expr {$fault==0 || ($fault==1 && $config<5)}]
   phase5_case Faults tb_phase6a_fault_comparison $tag [list APPROACH=$approach BETA=$beta CONFIG_ID=$config FAULT_ID=$fault] $capture 1
  }
 }
 close_project
} message]} {puts stderr $message;exit 1}
