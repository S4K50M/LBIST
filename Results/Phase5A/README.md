# Phase 5A: processor isolation and real IF/RF scan/capture/unload

**PASS within the processor boundary described below.** Vivado/XSim 2025.1.1
ran eight behavioral cases against the actual cMIPS implementation. All 280
processor captures matched independently calculated responses and their serial
unloads. All 1,169 protected original/earlier-phase files retained their SHA-256.

The new core uses clock enables for all processor storage, masks requests and
writes, and waits for holds to acknowledge across clk, phi1 and phi2. The host
must indicate an idle external fabric before isolation begins. The unchanged
64-bit IF/RF bank is the only processor state intentionally modified during
acknowledged testing. Reset is the only supported exit.

See the [design and protocol](../../docs/phase5a_scan_capture.md),
[initial audit and final policy](../../docs/phase5a_isolation_audit.md),
[machine-readable audit](phase5a_isolation_audit.csv) and
[storage-instance coverage](phase5a_state_coverage.json).

## Executed cases

Durations are simulated time through the explicit completion marker or the
verified original CPU breakpoint, including directed checks after the main
sequence. Controller cases include pauses, capture-ready delays, abort,
illegal restart, DONE holding and asynchronous mid-pattern reset.

| Case | Patterns | SHIFT / CAPTURE / UNLOAD edges | Duration | Result |
| --- | ---: | --- | ---: | --- |
| controller_L1 | 256 | 256 / 256 / 256 | 1.5812 us | PASS |
| controller_L2 | 256 | 512 / 256 / 512 | 2.6052 us | PASS |
| controller_L64 | 256 | 16,384 / 256 / 16,384 | 66.0932 us | PASS |
| core_isolation | 8 | 512 / 8 / 512 | 21.7802 us | PASS |
| core_shift_capture_P256 | 256 | 16,384 / 256 / 16,384 | 661.6002 us | PASS |
| core_shift_capture_P16 | 16 | 1,024 / 16 / 1,024 | 42.2202 us | PASS |
| functional_lwsw | — | normal CPU execution | 1.670 us | PASS |
| functional_stalls | — | normal CPU, 60 ns instruction stall | 1.730 us | PASS |

The sequence counts describe the completed main run. The controller's separate
mid-pattern-reset test deliberately performs one additional partial SHIFT,
which the independent VCD checker counts explicitly; it is not an extra edge
in a successful pattern. Controller unit benches have no pattern generator;
their generator-advance CSV entry is NA.

The real processor schedule is 64 SHIFT edges, one CAPTURE edge, then 64 UNLOAD
edges, without overlap. UNLOAD simultaneously loads disposable bits; the next
pattern starts with a fresh 64-edge SHIFT. The unchanged LFSR and Basic
22/20/22 PLPF controller advance on both shift phases: 128 advances per pattern,
32,768 in the principal 256-pattern run, and none during capture or pause.
PLPF feedback comes from the actual IF/RF input-stage flip-flop.

## Isolation, capture and functional results

Every processor case observes 4,287 meaningful encoded state bits, including
both GPR RAM replicas and registered reads, all unscanned pipeline/exception
banks, PC, CP0/TLB, COUNT/RANDOM/LL, HI/LO and phase-clocked flags. This debug
encoding is not a physical flip-flop count or an additional scan chain.

| Processor case | Protected changes | Memory attempts / actual | GPR attempts / actual |
| --- | ---: | --- | --- |
| core_isolation | 0 | 0 / 0 | 1,033 / 0 |
| core_shift_capture_P256 | 0 | 0 / 0 | 33,025 / 0 |
| core_shift_capture_P16 | 0 | 2,065 / 0 | 0 / 0 |

Attempts count cycles with a held internal request, not distinct transactions.
The earlier-entry P16 case deliberately freezes a pending store. Independent
memory monitors and actual GPR write strobes verify suppression. IRQ, NMI and
bus errors are injected and masked; they cause no protected-state changes.
Dropping test_mode remains isolated, flags the protocol violation, and requires
reset before restart.

Capture explicitly routes the scan-loaded PC half, aligned to four bytes,
through the **existing PC+4 adder**. The architectural PC/fetch address stay
held. The other half captures the ordinary ROM instruction at that address,
with the opcode annul/flush selection explicitly bypassed. The expected
response is computed from an independent bit-by-bit scan reference and the
original program image, rather than the DUT adder or captured output.

All 280 actual/correct/serial response triples are in
[phase5a_capture_unload.csv](phase5a_capture_unload.csv). The 256-pattern run
produced 254 distinct responses; the other cases produced 8 and 16.
For example, its first three responses are 00003E741460FFFA,
001FFF481460FFFA and FF8000681460FFFA.

Fresh-reset scan-disabled regressions compare the new core with the original
core in the unchanged cMIPS memory/cache/peripheral environment. Both emit the
ten expected lwsw words FFFFFFF6 through FFFFFFFF and terminate at PC 00000038.
There are 313 normal and 325 stalled comparison samples, including 12 stall
samples. The runner accepts the original breakpoint only with all expected
output and comparison markers; other failures return a nonzero exit.
Post-test reset/restart is also checked in each processor scan experiment.

The [verification](phase5a_verification_summary.csv),
[sequence](phase5a_scan_sequence.csv),
[isolation](phase5a_isolation_summary.csv) and
[functional](phase5a_functional_regression.csv) CSVs record the actual metrics.
Eight independent Python checks pass, including deliberate corruption of
protected state, external writes, serial response and a saved SVG.

## Actual waveforms and logs

Four native captures are present locally, each with WDB, VCD and portable WCFG:

- [Controller layout](Controller/waveforms/controller_L64.wcfg) and
  [overview](Controller/waveforms/controller_L64_overview.svg).
- [Isolation layout](Isolation/waveforms/core_isolation.wcfg) and
  [protected-state preview](Isolation/waveforms/core_isolation_protected_state_hold.svg).
- [256-pattern layout](ShiftCapture/waveforms/core_shift_capture_P256.wcfg),
  [overview](ShiftCapture/waveforms/core_shift_capture_P256_overview.svg) and
  [actual increment/capture](ShiftCapture/waveforms/core_shift_capture_P256_real_increment_capture.svg).
- [Pending-store layout](ShiftCapture/waveforms/core_shift_capture_P16.wcfg) and
  [write-suppression preview](ShiftCapture/waveforms/core_shift_capture_P16_write_suppression.svg).

All four WDB/WCFG pairs were reopened by native Vivado. All **63 saved SVGs**,
covering **3,482 plotted intervals**, were checked against captured VCD values
and transition boundaries. Focused events include entry, acknowledgement,
first/last SHIFT, both PLPF mode changes, capture, response unloading, pattern
increment, DONE, rejected exit, reset and functional restart. Event timestamps
come from actual transitions. Unknown original resetless state is retained.

See [events](phase5a_waveform_events.csv),
[VCD source hashes](phase5a_waveform_sources.csv),
[behavioral checks](phase5a_waveform_validation.csv) and
[SVG interval checks](phase5a_preview_validation.csv).
WDB/VCD/work projects are Git-ignored local artifacts; readable SVG and WCFG
files are committed. Open each WCFG with its matching WDB in the same folder.

Compile, elaboration and simulation logs are separate for each case in
Controller/logs, Isolation/logs and ShiftCapture/logs. The definitive native
consoles are [controller](Controller/logs/controller_console.log),
[processor and functional cases](Isolation/logs/final_capture_console.log),
[native waveform/final audit](Isolation/logs/final_acceptance.log) and
[Python checks](Controller/logs/python_final_tests.log).

## Synthesis

Out-of-context synthesis used xc7a35tcpg236-1. Resource counts describe the
instrumented, debug-observable design rather than a production chip.

| Top | FFs | LUTs | Latches | RAM primitives |
| --- | ---: | ---: | ---: | ---: |
| lbist_test_controller | 23 | 44 | 0 | 0 |
| phase5a_ifrf_subsystem | 87 | 97 | 0 | 0 |
| core_scan_test | 3,086 | 6,505 | 0 | 0 |

See [summary](phase5a_synthesis.csv) and Controller/reports utilization/latch
reports. The [initial synthesis console](Controller/logs/synthesis_console.log)
contains the final controller/subsystem runs and an earlier core revision.
The [final core synthesis](Controller/logs/synthesis_final_core.log) supersedes
that earlier core result. Vivado reported 95 warnings at the controller
checkpoint, 109 at the subsystem checkpoint (cumulative session totals), and
161 in the separate final-core run; each reported zero critical warnings and
zero errors. Diagnostics include constant debug/counter bits, unused original
ports, inherited sensitivity-list warnings and CE inputs read in clocked
processes without appearing in their clock/reset sensitivity lists.
No latches were inferred. No authoritative clock constraints were supplied,
so timing closure or silicon CDC sign-off is not claimed.

## Reproduction and preservation

Run from the repository root with Vivado/XSim 2025.1.1 and Python 3.9+.
The existing resolver selects Python with matplotlib/numpy support;
PHASE3_PYTHON can specify the executable.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase5a.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/synth_phase5a.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/verify_phase5a_waveforms.tcl
python ./lbist/scripts/phase5a_analysis.py --require-all --waves
python ./lbist/scripts/test_phase5a_analysis.py
python ./lbist/scripts/audit_phase5a.py
python ./lbist/scripts/phase5a_manifest.py
~~~

The aggregate runner generates helper variants, regenerates the ROM package
from the original prog.bin, runs all eight cases, validates captures/previews
and native layouts, runs independent Python checks, audits preservation and
records source/image hashes. Behavioral watchdogs are bounded by 20 ms; every
actual run is below 0.662 ms, well below the 100 ms hard limit.

New source groups are the test-mode controller and OOC subsystem, isolated core
plus 14 generated CE helpers, six test/support VHDL files, Phase 5A scripts,
two design/audit documents and this result tree. No previously tracked source
or result was modified. [Source hashes](phase5a_source_manifest.csv),
[original four input images](phase5a_input_images.csv) and
[1,169 before/after hashes](protected_file_integrity.csv) provide provenance.
prog.bin is the original 80-byte lwsw image. Its empty data.bin/input.data are
valid for this program; serial.inp is the existing 22-byte input fixture.

## Architectural limits

The verified boundary is the processor entity after all hold acknowledgements.
Autonomous external cache/device state and timers are excluded; the host must
quiesce outstanding fabric transactions before entry. Scan experiments use a
side-effect-free ROM and zero-wait memory model, while normal regressions use
the original environment. IRQ/NMI events during test are discarded and must
be reissued after reset if still required.

Reset discards the interrupted pipeline context. Original GPR/unreset pipeline
contents are not guaranteed to clear, so firmware must initialize what it
uses. Restart comparison qualifies data buses by valid transactions; separate
fresh-reset regressions compare all functional ports.

Capture exercises a limited alignment/increment and instruction-input cone.
This is not full CPU combinational fault detection. The remaining 656 pipeline
bits, MISR, fault injection, fault coverage and physical power savings remain
outside Phase 5A.
