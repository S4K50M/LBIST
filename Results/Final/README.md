# VL405 LBIST final submission

Start with [the final report](Final_Report.md), [verification evidence](final_verification_summary.md), and [the demo guide](DEMO.md). The PDF/LaTeX versions are supplied when the local PDF build succeeds.

**Latest FPGA revision:** [Timing closure and updated power](FPGA_Analysis/Timing_Closure/README.md) contains the matched 9.756097561 MHz implementations, fresh verification and activity, and reproduction commands. The original 50 MHz reports remain historical evidence. Run `powershell -File lbist/scripts/run_timing_revision.ps1` from the repository root to reproduce this revision.

The implemented scope is **one 64-bit IF/RF chain**, a real processor capture cone, 256 patterns, five pattern-generation approaches and the original **eight capture-input sites with both stuck-at polarities (16 faults)**. Every initial approach detects 12/16; this is not 75% whole-processor coverage. WTM is simulation switching activity, not measured physical power.

- [Primary experimental comparison](final_experimental_comparison.csv): Direct, constant n=3, Basic, Swap, Moving.
- [Tables](tables/): targets, signatures, latency, aliases, coverage, cycle counts and complete per-fault outcomes.
- [Architecture diagram](figures/architecture.svg), [scan/capture/unload waveform](figures/scan_capture_unload.png), [abort waveform](figures/misr_abort.svg), and readable graphs in `figures/`.
- [FPGA implementation study](FPGA_Analysis/README.md), [synthesis summary](final_synthesis_summary.md), native utilization/timing/power reports, execution logs and graphs.
- [Verification summary CSV](Verification/verification_summary.csv), archived independent campaign/waveform audits and preservation hashes.
- [Source manifest](source_manifest.csv): provenance of final integration and reporting sources.

The final FPGA configurations use the installed free-license Artix-7 `xc7a35tcpg236-1` on Vivado 2025.1.1. They are placed-and-routed **out-of-context processor boundaries** with related clock phases and virtual external buses. They are not a Basys3 board bitstream. The new constrained timing checks pass; narrow margins, incomplete external-port routing and partial SAIF annotation remain explicit limitations. The earlier 50 MHz timing failures are retained.

Earlier phases, their reports, RTL and result files remain unchanged. New wrappers connect the existing implementation; no extra scan chain, expanded fault universe or processor refactor is added. Native WDB/VCD/SAIF and checkpoints are regenerable local artifacts excluded from Git. Portable waveform figures and layouts, CSVs and native textual reports are supplied.

Rebuild only the final results using the commands in the demo guide. The essential runner does not regenerate the historical full matrix.
