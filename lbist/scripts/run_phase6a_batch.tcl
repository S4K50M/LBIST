source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
if {[catch {
 if {![info exists ::batch_configs]} {set ::batch_configs {0 1 2 3 4 5 6 7 8 9 10 11}}
 phase5_project batch_[lindex $::batch_configs 0]
 add_files -fileset sim_1 [list [file join $phase5_root lbist tb tb_phase6a_batch.vhd]]
 set approaches {0 1 2 3 4 2 2 3 3 4 4 4};set betas {20 20 20 16 20 4 12 4 12 4 12 19}
 set py [phase3_python]
 foreach cid $::batch_configs {
  set baseline [file join $phase5_root Results Phase6A Faults reports [format c%d_f0.csv $cid]]
  if {![file exists $baseline]} {error "Execute fault-free reference first: $cid"}
  set f [open $baseline];set baseline_text [read $f];close $f
  if {[string first ",PASS," $baseline_text]<0} {error "Invalid fault-free reference: $cid"}
  set first 1
  if {[info exists ::reuse_completed] && $::reuse_completed} {
   set first 0
   while {$first<=16} {
    set path [file join $phase5_root Results Phase6A Faults reports [format c%d_f%d.csv $cid $first]]
    if {![file exists $path]} {break}
    set f [open $path];set content [read $f];close $f
    if {[string first ",PASS," $content]<0} {break}
    incr first
   }
  }
  if {$first>16} {continue}
  if {$first==0} {error "Execute and verify fault-free baseline before batch $cid"}
  while {$first<=16} {
   set last [expr {min(16,$first+7)}]
   set tag [format batch_c%d_%d_%d $cid $first $last]
   phase5_case Batch tb_phase6a_batch $tag [list APPROACH=[lindex $approaches $cid] BETA=[lindex $betas $cid] CONFIG_ID=$cid FIRST_FAULT=$first LAST_FAULT=$last] 0 1
   puts [exec $py -E [file join $phase5_scripts phase6a_split_batch.py] $cid $first $last]
   set first [expr {$last+1}]
  }
 }
 close_project
} message]} {puts stderr $message;exit 1}
