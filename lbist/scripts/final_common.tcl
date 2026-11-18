# Reuse proven helpers, redirecting every new output into Results/Final.
source [file join [file dirname [file normalize [info script]]] phase6a_common.tcl]
set final_scripts [file dirname [file normalize [info script]]]
set final_root $phase5_root
file mkdir [file join $final_root Results Final work]
cd [file join $final_root Results Final work]
set ::env(PHASE6A_NATIVE_ROOT) [file join $::env(TEMP) vl405_final_sim]
set final_case_body [string map {Phase6A Final/Verification {PHASE 5A RESULT} {FINAL VERIFICATION RESULT}} [info body phase5_case]]
proc phase5_case {group top tag generics {capture 1} {cpu 0}} $final_case_body
set final_capture_body [string map [list tb_phase6a_fault_comparison {tb_phase6a_fault_comparison tb_final_activity}] [info body phase5_capture]]
set final_capture_body [string map {{current_bit future1 future2 } {} { active_mode } { }} $final_capture_body]
proc phase5_capture {out top tag} $final_capture_body
rename phase3_wave_finish final_wave_finish_base
proc phase3_wave_finish {folder top tag simdir} {
 global final_root
 set bytes [final_wave_finish_base $folder $top $tag $simdir]
 exec [phase3_python] -E [file join $final_root lbist scripts normalize_final_waveforms.py] --folder $folder
 return $bytes
}
rename phase5_project final_base_project
proc phase5_project {selection} {
 global final_root
 final_base_project final_$selection
 add_files -fileset sources_1 [list [file join $final_root lbist final final_processor_system.vhd]]
 foreach n {final_activity_check tb_final_activity} {
  add_files -fileset sim_1 [list [file join $final_root lbist tb $n.vhd]]
 }
}
