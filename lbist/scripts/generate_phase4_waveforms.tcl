source [file join [file dirname [file normalize [info script]]] phase4_common.tcl]
if {[catch {
    phase4_run unit
    phase4_run plpf
    phase4_run core
    source [file join $phase4_scripts verify_phase4_waveforms.tcl]
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
