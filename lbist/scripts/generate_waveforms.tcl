source [file join [file dirname [file normalize [info script]]] waveforms_common.tcl]
if {[catch {generate_lbist_waveforms all} message]} {
    puts stderr "\[FAIL\] $message"
    if {[info exists ::env(WAVEFORMS_GUI)]} {error $message} else {exit 1}
}
