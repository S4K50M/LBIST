# Phase 5C — measured capture-cone stuck-at campaign

All **16 eligible faults** completed valid, independent 256-pattern processor
experiments. The universe contains eight explicitly selected capture-input
sites, with SA0 and SA1 at each. Fault-free golden signature: **AFBC**.

| Metric | Actual result |
| --- | ---: |
| Direct response detections | 12 / 16 |
| Final MISR detections | 12 / 16 |
| Direct coverage | 75.00% |
| Final MISR coverage | 75.00% |
| Undetected by final MISR | 4 |
| MISR aliases | 0 |
| Invalid experiments | 0 |
| Patterns per experiment | 256 |
| Actual SHIFT / CAPTURE / UNLOAD cycles | 16384 / 256 / 16384 |
| Enabled payload cycles per experiment | 33024 |

Each fault experiment finished at 661.6002 us, below the 100 ms limit.
Setup, acknowledgement, pauses, reset and restart add 56.01 elapsed 20 ns
clock periods outside the payload. All 4,096 faulty captured responses and
their serial unloads matched independent injection-aware predictions.
Python checked every per-pattern MISR result by polynomial division of the
actual response stream. Protected processor state and actual write strobes
remained isolated in every experiment.

## Results and figures

- [Defined eligible inventory](reports/fault_inventory.csv).
- [All actual fault outcomes/signatures](reports/fault_campaign.csv).
- [Detection latency](reports/fault_detection_latency.csv).
- [Aliasing classification](reports/misr_aliasing.csv).
- [Coverage at 1/4/8/16/32/64/128/256 patterns](reports/fault_coverage_summary.csv).
- [Actual cycle counts and overheads](reports/test_time_comparison.csv).
- [Cycles to common coverage thresholds](reports/coverage_threshold_cycles.csv).
- [Actual per-pattern responses and signatures](reports/signature_evolution.csv).
- [Direct versus MISR coverage growth](Comparison/figures/coverage_growth.svg).
- [Detections by region](Comparison/figures/detections_by_region.svg).
- [First-detection distribution](Comparison/figures/latency_distribution.svg).
- [Coverage versus test cycles](Comparison/figures/test_cycles.svg).
- [Representative signature evolution versus golden](Comparison/figures/signature_evolution.svg).

Native representative captures are in
[fault 1](Faults/waveforms/fault_1.wcfg) and
[fault 10](Faults/waveforms/fault_10.wcfg).
The focused [fault 1 capture cone](Faults/waveforms/fault_1_capture_cone.svg)
uses its first directly detected pattern rather than an assumed timestamp.
Full WDB/VCD stay local; portable WCFG and verified SVG previews are tracked.
[SVG interval checks](../Phase5B/reports/waveform_validation.csv) also cover
the unit and fault-free captures. Every recorded MISR clock edge and settled
completion comparator is independently checked from VCD.

## Scope and reproduction

The muxes alter actual incrementer inputs or actual instruction capture inputs,
before the functional response is stored. They never force scan FF outputs or
MISR state. Fault-ID headers, complete pattern indices, final signatures,
serial responses, completion markers and isolation assertions are checked;
a missing or misconfigured experiment fails analysis.

Only the eight enumerated input-net sites are covered. Instruction bits at the
held fetch address are constant, so a stuck-at polarity already equal to the
functional bit can remain unobservable. Such faults stay in the denominator.
An equal final signature with a direct mismatch is reported as an alias;
equal signatures alone do not establish fault freedom.

The experiment uses the unchanged Basic 22/20/22 controller and real PLPF
feedback. Faults can change later feedback-dependent stimulus; this is the
same configured closed-loop sequence, not an assertion that all faulty scan
words remain identical to fault-free words.

Run lbist/scripts/run_all_phase5bc.tcl in Vivado batch mode, then optionally
lbist/scripts/synth_phase5bc.tcl. Separate runners are provided for unit,
integration, campaign and functional regressions. The campaign also accepts
global fault_first/fault_last bounds, enabling independent workers in separate
projects. This execution used independent workers for the remaining faults.

See [design/protocol and polynomial](../../docs/phase5bc_misr_faults.md) and
[Phase 5B verification/synthesis](../Phase5B/README.md).
All 1211 tracked pre-Phase5B/C files retained their SHA-256;
the original Phase 5A preservation audit also remains unchanged.
Unfiltered/constant PLPF/Swap/Moving comparison and matched-WTM plots are
explicit follow-up work. No full MIPS32 coverage, power savings, remaining
656-bit scan conversion or fault-free guarantee is claimed.
