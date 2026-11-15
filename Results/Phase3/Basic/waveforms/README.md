# Basic Control waveforms

Each capture includes `.wcfg` (layout), `.wdb` (full XSim history), `.vcd`
(first 512 ns), and `.svg` (first 300 ns preview). See `waveform_summary.csv`
for actual capture status. WDB and VCD are local generated files ignored by Git.

Open a matching WCFG and WDB together in Vivado/XSim. The default viewer script is
`lbist/scripts/open_lbist_waveforms.tcl` from the repository root. Full case list,
GUI/PowerShell commands and regeneration instructions are in `docs/waveforms.md`.

All captures were executed in XSim 2025.1.1 and passed their self-checking tests.
Every WDB/WCFG pair was also reopened successfully in native Vivado static
viewing mode. Prior RTL and verification reports remain unchanged.
