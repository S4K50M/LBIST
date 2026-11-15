# Uses capture hooks in the existing waveform infrastructure, new folders only.
source [file join [file dirname [file normalize [info script]]] phase3_common.tcl]
if {[catch {
    phase3_run waveforms
    set root [file normalize [file join $phase3_script_dir ../..]]
    set python [phase3_python]
    puts [exec $python -E [file join $phase3_script_dir collect_phase3_results.py] --no-figures]
    puts [exec $python -E [file join $phase3_script_dir render_waveform_previews.py] --phase3]
    set ::WAVEFORM_VERIFY_SCOPE phase3
    source [file join $phase3_script_dir verify_waveforms.tcl]
} message]} {
    puts stderr [format {[FAIL] %s} $message]
    if {[info exists ::env(PHASE3_GUI)]} {error $message} else {exit 1}
}
