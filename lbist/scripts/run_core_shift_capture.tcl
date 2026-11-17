source [file join [file dirname [file normalize [info script]]] phase5a_common.tcl]
if {[catch {
    phase5_project shiftcapture
    phase5_case ShiftCapture tb_core_scan_shift_capture core_shift_capture_P256 {PATTERNS=256 ENTRY_NS=380} 1 1
    phase5_case ShiftCapture tb_core_scan_shift_capture core_shift_capture_P16 {PATTERNS=16 ENTRY_NS=200} 1 1
    close_project
} message]} {puts stderr [format {[FAIL] %s} $message];exit 1}
