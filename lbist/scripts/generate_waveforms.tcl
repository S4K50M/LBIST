# Set WAVEFORM_SCOPE=phase3 to extend generation without touching legacy captures.
if {[info exists ::WAVEFORM_SCOPE] && $::WAVEFORM_SCOPE eq "phase3"} {
    source [file join [file dirname [file normalize [info script]]] generate_phase3_waveforms.tcl]
} else {
source [file join [file dirname [file normalize [info script]]] waveforms_common.tcl]
if {[catch {generate_lbist_waveforms all} message]} {
    puts stderr "\[FAIL\] $message"
    if {[info exists ::env(WAVEFORMS_GUI)]} {error $message} else {exit 1}
}

}
