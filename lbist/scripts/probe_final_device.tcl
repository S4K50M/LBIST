set root [file normalize [file join [file dirname [info script]] ../..]]
file mkdir [file join $root Results Final work]
cd [file join $root Results Final work]
puts "TOOL_VERSION: [version -short]"
set part [get_parts -quiet xc7a35tcpg236-1]
if {[llength $part]!=1} {error "Required free-license Artix-7 part is not installed"}
report_property $part
foreach cmd {read_saif report_switching_activity report_power open_saif log_saif close_saif} {
 puts "COMMAND $cmd: [info commands $cmd]"
 catch {help $cmd}
}
puts "FINAL_DEVICE_INSTALLED_SUPPORTED: PASS"
