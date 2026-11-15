# Phase 4: verified initial IF/RF scan insertion

Completed the initial **64-bit** IF/RF scan scope on 2026-11-15 using Vivado/XSim
2025.1.1. **Processor-wide scan isolation is INCOMPLETE.** The processor variant
is verified with scan disabled; genuine scan shifting and functional
capture/unload are verified independently on its actual IF/RF register RTL.

All **22 simulation cases passed**: 20 normal completions and two intended
configuration rejections. Six captured-data/adversarial Python tests passed.
Three native WDB/WCFG pairs reopened successfully and **23 saved waveform SVGs**
were checked interval-by-interval against captured VCD transitions.

All **995 pre-existing protected files** are unchanged, including original
cMIPS RTL/images, Phase 1-3 RTL, scripts, reports, native captures, layouts and
previews. New files are confined to Phase 4 paths plus its dedicated source
files and documentation. The remaining 656 planned pipeline bits are untouched.

## What was implemented

- [reg_IF_RF_scan.vhd](../../lbist/rtl/reg_IF_RF_scan.vhd): one shared 64-bit bank,
  asynchronous active-low reset, scan priority over active-low functional load.
- [core_scan.vhd](../../lbist/core_scan/core_scan.vhd): original core ports plus
  four scan ports; only PIPESTAGE_IF_RF is replaced.
- [Register testbench](../../lbist/tb/tb_reg_IF_RF_scan.vhd): original-register
  differential comparison, full-state scan scoreboard and SCAN01..SCAN15.
- [Real-register PLPF testbench](../../lbist/tb/tb_if_rf_plpf_integration.vhd):
  existing LFSR/phase shifter/Basic controller/dynamic PLPF with actual FF feedback.
- [Processor differential testbench](../../lbist/tb/tb_core_scan_regression.vhd):
  original memory/cache/peripheral environment, original and scan cores, normal
  execution and common-input instruction-wait injection.
- Dedicated bounded runners, report collection, independent VCD/SVG validation,
  corruption tests, synthesis comparison and original-file hashing.

[Exact processor RTL diff](Core_Integration/reports/core_scan_changes.diff)
documents every core modification and retains the original GPL-3.0 notice.
[Full architecture and safety assessment](../../docs/phase4_scan_integration.md)
explains reset polarity, bit order, capture/unload and limitations.

## Actual verification outcomes

| Suite | Cases | Result |
| --- | ---: | --- |
| Register unit, two deterministic seeds | 2 | PASS |
| Invalid register pattern count | 1 | PASS: rejected at time zero |
| Real-feedback PLPF, beta0/16/20/36 | 4 | PASS |
| Illegal Basic beta1 | 1 | PASS: rejected at time zero |
| Dual-core normal/stalled execution | 2 | PASS |
| Existing Phase 2/3 testbenches | 11 | PASS |
| Original cMIPS baseline | 1 | PASS |

Each unit run verifies 256 main scan patterns, including zero/one/alternating,
walking-one/walking-zero and deterministic random data, plus 256 randomized
functional cycles and capture/unload tests. Actual scan shifts per unit:
16577, including additional directed checks. Both runs finish at 33.6762 us.

The canonical PLPF run measures 1024 patterns / 65536 enabled shifts and then
performs one functional capture and 64 unload shifts: **65600 total scan shifts**.
It completes at 131.2101 us. Other PLPF cases each measure 256 patterns and
complete at 32.9061 us.

The longest simulation, including prior-phase regressions, is 393.20901 us.
Every run finishes below 100 ms, with a 20-ms maximum watchdog/Tcl bound.
Positive standalone tests use TB_COMPLETE; expected negatives require a
time-zero CONFIG_ERROR. The original CPU's known intentional breakpoint is
classified separately from genuine failures.

## Measured scan activity

The measurement window excludes the later capture/unload. One real 64-bit chain,
seed AAAA, Basic control. Values below come from actual integer XSim counts.

| Beta | Main patterns | Estimated WTM | Measured WTM | Absolute error (pp) | Serial toggle rate | FF switching fraction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 256 | 7.142857% | 7.243465% | 0.100607 | 7.172069% | 7.166672% |
| 16 | 256 | 17.857143% | 17.237267% | 0.619876 | 17.280107% | 17.257023% |
| 20 | 1024 | 20.535714% | 20.095637% | 0.440077 | 20.202945% | 20.193315% |
| 36 | 256 | 31.250000% | 30.845102% | 0.404898 | 31.074895% | 31.016254% |

The canonical beta20 schedule is 22 low / 20 unfiltered / 22 low enabled shifts.
Its theoretical estimate is 20.535714%; measured WTM is 20.095637%.
Temporal and loaded-pattern WTM calculations agree exactly for every pattern.
All measured/estimated errors satisfy the fixed two-percentage-point bound.
These are activity measurements, not physical power results.

## Processor functional equivalence

| Case | Termination | Pipeline samples | Stall samples | Output |
| --- | ---: | ---: | ---: | --- |
| baseline_lwsw | 1670 ns | 0 | 0 | 10 words match baseline |
| core_scan_lwsw | 1670 ns | 313 | 0 | 10 words match baseline |
| core_scan_stalls | 1730 ns | 325 | 12 | 10 words match baseline |

The scan-disabled variant reproduces baseline execution and the breakpoint at
PC=00000038 at 1670 ns. Both exit decoders are checked before the intentional
termination assertion. All ten output words also match an independent expected
-10..-1 sequence.

A shared 60-ns instruction wait at 400 ns produces 12 observed stalled samples.
Both cores remain equivalent and stop at 1730 ns, exactly 60 ns later.
All functional output ports are compared after CPU phase changes. Tcl samples
PC, IF/RF state and load enable, execute operands, writeback data and write
controls every 5 ns after reset. Captured VCD independently confirms pipeline
equivalence and scan feedback/output mapping.

The original environment still receives requests from the reference core.
The scan variant drives separate signals; its requests/data/write controls
must match before using the shared responses. Memory/peripheral models and
original binary image contents are preserved.

## Processor-wide scan safety: incomplete

Scan enable currently affects IF/RF only. PC, architectural registers, later
stages, write strobes, interrupts, exceptions, caches and peripherals are not
globally frozen or isolated. Arbitrary shifted instructions could execute if
this input were enabled while the processor runs.

Therefore the core regressions keep scan_enable=0. Register-level and PLPF
capture/unload are complete; processor-wide scan entry, isolation, capture and
state restoration are not implemented or claimed. Reset is not an isolation
substitute because it clears this scan bank too. No further scan stages, MISR,
CUT fault model or fault-coverage measurement are included.

## Actual out-of-context synthesis

Target: xc7a35tcpg236-1, Vivado 2025.1.1, no I/O buffers.

| Register | Flip-flops | LUTs | Latches | FF type |
| --- | ---: | ---: | ---: | --- |
| Original IF/RF | 64 | 2 | 0 | FDCE |
| Scan IF/RF | 64 | 66 | 0 | FDCE |

Both implementations retain exactly 64 asynchronously cleared, clock-enabled
FFs. Scan input selection adds 64 LUTs on this FPGA target, with no shadow bank.
These register-level results do not imply a whole-processor area/power result.
Both runs emitted only Synth 8-7080 (parallel synthesis criteria not met);
neither reported an RTL/storage-inference warning.

[Synthesis CSV](IF_RF/reports/synthesis_comparison.csv),
[original utilization](IF_RF/reports/reg_IF_RF.utilization.rpt),
[scan utilization](IF_RF/reports/reg_IF_RF_scan.utilization.rpt),
[actual synthesis log](IF_RF/logs/synthesis_console.log).

## Reports and waveform evidence

- [All cases, timing, scan counts and equivalence](phase4_verification_summary.csv)
- [Measured activity and integer numerators](phase4_scan_metrics.csv)
- [Core execution, stalls and baseline output](phase4_core_regression.csv)
- [Captured-state behavior validation](phase4_waveform_validation.csv)
- [Every saved SVG interval validation](phase4_preview_validation.csv)
- [Actual event timestamps](phase4_waveform_events.csv)
- [VCD provenance and SHA-256](phase4_waveform_sources.csv)
- [Protected-file SHA-256 audit](protected_file_integrity.csv)
- [Files added and source hashes](phase4_source_manifest.csv)
- [Input image hashes](phase4_input_images.csv)
- [Six Python checker tests](IF_RF/logs/python_capture_tests.log)
- [Native waveform checks](Core_Integration/logs/native_validation.log)
- [Final acceptance](Core_Integration/logs/final_acceptance.log)

The three capture groups each contain an actual LOG, portable VCD, complete
native WDB and matching WCFG. WDB/VCD and working projects are Git-ignored local
artifacts, not committed full histories. Regenerate them after cloning.

Representative previews:
[asynchronous reset](IF_RF/waveforms/scan_unit_seed12345_asynchronous_reset.svg),
[functional capture](IF_RF/waveforms/scan_unit_seed12345_functional_capture.svg),
[captured unload](IF_RF/waveforms/scan_unit_seed12345_captured_unload.svg),
[first PLPF boundary](PLPF_Integration/waveforms/real_plpf_B20_P1024_first_mode_switch.svg),
[real scan-FF feedback](PLPF_Integration/waveforms/real_plpf_B20_P1024_real_ff_feedback.svg),
[core equivalence](Core_Integration/waveforms/core_scan_lwsw_overview.svg),
[actual scan-core pipeline](Core_Integration/waveforms/core_scan_lwsw_u_scan_pipeline.svg).

Register previews cover reset/load/hold/entry, propagation, scan-out, capture,
unload and reset during scan. PLPF previews cover both mode boundaries,
completion, pause/resume, real feedback, capture and unload. Core views include
clocks/reset, both address paths, write controls, real IF/RF state, scan pins and
the equivalence indicator.

## Reproduce from the cmips root on Windows

Python 3.9+ with matplotlib/numpy and Vivado/XSim 2025.1.1 are required.
Existing interpreter selection is reused; PHASE3_PYTHON can override its path.
Python -E avoids Vivado's bundled PYTHONHOME/PYTHONPATH settings.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase4.tcl
~~~

The full runner executes unit and PLPF suites before processor integration,
then runs prior-phase regressions, requires all 22 cases, reopens native
traces, checks captured data/SVGs, runs six Python tests, synthesizes both
registers and audits protected files.

Individual simulation runners:
run_if_rf_scan.tcl, run_if_rf_plpf.tcl, run_core_scan_regression.tcl and
run_phase4_regressions.tcl. Additional commands:

~~~powershell
python ./lbist/scripts/phase4_analysis.py --require-all
python ./lbist/scripts/test_phase4_analysis.py
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/generate_phase4_waveforms.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/verify_phase4_waveforms.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/synth_if_rf_scan.tcl
~~~

To view a local trace, open its WDB in Vivado and then the adjacent WCFG, or use
XSim's static viewer:

~~~powershell
& 'E:/2025.1.1/Vivado/bin/xsim.bat' './Results/Phase4/PLPF_Integration/waveforms/real_plpf_B20_P1024.wdb' -gui -view './Results/Phase4/PLPF_Integration/waveforms/real_plpf_B20_P1024.wcfg'
~~~

No older result writers are called. Projects, simulator image copies and tool
runtime profiles stay in Results/Phase4/work. Earlier debug attempts are
archived there; current case CSVs/raw logs record the final passing runs.

## Individual case status

| Case | Result | Actual time (us) |
| --- | --- | ---: |
| scan_unit_invalid_patterns | PASS (expected rejection) | 0.000000 |
| scan_unit_seed12345 | PASS | 33.676200 |
| scan_unit_seed67890 | PASS | 33.676200 |
| real_plpf_B0_P256 | PASS | 32.906100 |
| real_plpf_B16_P256 | PASS | 32.906100 |
| real_plpf_B20_P1024 | PASS | 131.210100 |
| real_plpf_B36_P256 | PASS | 32.906100 |
| real_plpf_invalid_beta | PASS (expected rejection) | 0.000000 |
| baseline_lwsw | PASS | 1.670000 |
| core_scan_lwsw | PASS | 1.670000 |
| core_scan_stalls | PASS | 1.730000 |
| regression_tb_basic_controller | PASS | 32.803100 |
| regression_tb_basic_integration | PASS | 131.457100 |
| regression_tb_lfsr_16 | PASS | 131.081200 |
| regression_tb_moving_controller | PASS | 32.801100 |
| regression_tb_moving_integration | PASS | 131.457100 |
| regression_tb_phase2_integration | PASS | 131.455100 |
| regression_tb_phase_shifter | PASS | 8.264736 |
| regression_tb_plpf_dynamic | PASS | 8.199100 |
| regression_tb_plpf_optimized | PASS | 393.209010 |
| regression_tb_swap_controller | PASS | 32.801100 |
| regression_tb_swap_integration | PASS | 131.457100 |
