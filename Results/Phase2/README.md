# Phase 2 measured verification results

Executed on 15 November 2026 using AMD Vivado/XSim **2025.1.1** on Windows.
All four RTL modules compiled; all five testbenches elaborated and passed.
The full-suite Vivado process exited with status **0**. No successful test used
an assertion failure as its termination mechanism.

## Test status and simulated duration

| Testbench | Result | Completion time (microseconds) |
| --- | --- | ---: |
| tb_lfsr_16 | PASS | 131.081200 |
| tb_phase_shifter | PASS | 8.264736 |
| tb_plpf_optimized | PASS | 393.209010 |
| tb_plpf_dynamic | PASS | 8.199100 |
| tb_phase2_integration | PASS | 131.455100 |

These are measured testbench completion times from the log markers, not elapsed
wall-clock time or the next 1-us Tcl polling boundary. The largest is below
0.4 ms. Each test also has a 2-ms watchdog; the 100-ms maximum is respected.

## Measured serial toggle rates

Rates below are percentages. CSV rates are fractions; the error column is in
percentage points. Each fixed-mode optimized-filter run uses 65535 bits (65534
adjacent-pair opportunities). Integration runs use 16384 bits (16383 opportunities).
The first bit of each measurement epoch is excluded from serial counting.

| Testbench | Mode | Expected (%) | Measured (%) | Absolute error (pp) | Transitions | Sample bits |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| tb_plpf_optimized | 1 | 50.000000 | 50.001530 | 0.001526 | 32768 | 65535 |
| tb_plpf_optimized | 2 | 16.666670 | 16.666160 | 0.000509 | 10922 | 65535 |
| tb_plpf_optimized | 3 | 7.142857 | 7.138279 | 0.004578 | 4678 | 65535 |
| tb_phase2_integration | 1 | 50.000000 | 50.070190 | 0.070195 | 8203 | 16384 |
| tb_phase2_integration | 2 | 16.666670 | 16.742970 | 0.076299 | 2743 | 16384 |
| tb_phase2_integration | 3 | 7.142857 | 7.172069 | 0.029211 | 1175 | 16384 |
| tb_phase2_integration | dynamic | N/A | 24.995420 | N/A | 4095 | 16384 |

All fixed-mode errors passed their numerical assertions: 0.5 percentage points
for optimized-filter units and 1 point for integration. The dynamic epoch changes
mode every 17 enabled shifts and includes mode-switch transitions. It has no
single stationary theoretical rate, so expected rate/error are marked N/A.

## Scan-in WTM and actual chain activity

Every integration epoch loads 256 complete 64-bit patterns. Normalized WTM below
uses transition propagation weights and includes the prior scan-input-stage
value at every pattern boundary. The independent pattern-domain calculation
matched the chronological weighted sum at every full pattern. Actual chain
activity counts all FF changes per enabled shift and includes initial contents.
These are separate quantities from serial output transition rate.

| Mode | Chain length | Complete patterns | Normalized scan-in WTM | Actual chain toggle fraction |
| --- | ---: | ---: | ---: | ---: |
| 1 | 64 | 256 | 0.50063480 | 0.49971870 |
| 2 | 64 | 256 | 0.16837060 | 0.16710950 |
| 3 | 64 | 256 | 0.07243465 | 0.07166672 |
| dynamic | 64 | 256 | 0.25219350 | 0.24944590 |

The scan-chain-length generic supports 2..1024 stages. **64 stages were simulated**;
other lengths were not run. No capture phase, MISR, or processor scan chain is
part of this verification. WTM does not establish physical power or fault coverage.

## Files and reproduction

- [Design, interfaces, equations, test coverage, deviations, GUI and batch instructions](../../lbist/README.md)
- [RTL modules](../../lbist/rtl/): `lfsr_16`, `phase_shifter`, `plpf_optimized`, `plpf_dynamic`.
- [Five self-checking testbenches and independent reference package](../../lbist/tb/).
- [Vivado project-mode runners](../../lbist/scripts/), including five dedicated runners.
- [Verification status CSV](reports/verification_summary.csv).
- [Toggle-rate CSV](reports/toggle_rate_summary.csv).
- [WTM and scan-length CSV](reports/wtm_summary.csv).
- [Simulation and build logs](logs/).
- [Verified source hashes](reports/source_sha256.csv).
- [Protected-file integrity evidence](reports/baseline_integrity.csv).

From the repository root in PowerShell:

```powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase2.tcl
```

In a fresh Vivado GUI Tcl console:

```tcl
set ::env(PHASE2_GUI) 1
source {C:/Users/Saksham Setia/OneDrive/Desktop/VLSI/cmips/lbist/scripts/run_all_phase2.tcl}
```

The runner creates an isolated project under `work/project`, selects each top,
compiles/elaborates, runs bounded increments and verifies completion plus absence
of failure markers. It writes these summary CSVs from actual simulation reports.
Compile/elaboration failures and incomplete simulations yield a failing batch exit.
Only Phase 2 sources enter this project. Build outputs under `work/` are ignored;
measured logs and reports are retained. A single-test runner replaces summary CSVs
with that invocation's results, so rerun the full suite for the complete tables.

## Integrity and remaining scope

All **356 pre-existing files** under `cMIPS/` and `Results/Baseline/`
matched their SHA-256 hashes from before this implementation. Existing processor
RTL, testbench, binaries, input files, and baseline results remain unchanged.

No unresolved compile or simulation failures remain in the required five tests.
Synthesis, gate-level area equivalence to Figure 5(b), physical power, other chain
lengths, and fault-coverage experiments have not been run. The documented shared
AND/OR implementation reproduces the requested filter functions, with explicit
invalid-mode hold behavior and a new, documented LFSR state convention.
