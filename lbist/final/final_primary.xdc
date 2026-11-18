# Basys 3 primary oscillator: 100 MHz. No package assignments for OOC virtual I/O.
create_clock -name board_clk -period 10.000 -waveform {0 5} [get_ports board_clk]
