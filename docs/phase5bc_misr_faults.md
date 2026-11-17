# Phase 5B/C: serial response analysis and enumerated capture-cone faults

The Phase 5A audit established scan_out=actual IF/RF Q(63), feedback=Q(0).
At each enabled rising edge, Q shifts left. The MISR samples Q(63) on that
same edge, before the bank updates. Only accepted UNLOAD enables reach it.
SHIFT, CAPTURE, pauses and DONE hold the signature. Captured responses unload
MSB first, 64 bits per pattern, continuously across 256 patterns.

## Polynomial and initialization

The 16-bit serial-input MISR uses x^16+x^12+x^5+1 (mask 1021), zero seed,
left shift and feedback=q(15) XOR response_bit. The next state is
(q << 1) XOR 1021 when feedback=1, otherwise q << 1, truncated to 16 bits.
Active-low asynchronous reset overrides synchronous clear, which overrides
enable. There is no clock gating. This single-response-input implementation
is equivalent to a serial polynomial signature register.

The Python reference uses polynomial long division, separately from VHDL's
feedback recurrence. It never reads a DUT signature to compute the golden.
The configured golden is AFBC for the unchanged Phase 5A Basic sequence:
LFSR AAAA, Basic 64/20 (22/20/22), real FF feedback, entry 380 ns, 256
patterns, 64 SHIFT + 1 CAPTURE + 64 UNLOAD, zero MISR seed, original lwsw
ROM SHA-256 fbb3da2760faf41147f751b857cb8b2c0105cec1e03fd824fa64387f45abae50.
It must be regenerated for other configurations.

signature_valid follows completed test_done; signature_match and fault_detected
are both low before completion. The last serial bit updates the signature
on the edge that completes UNLOAD; combinational comparison settles after
that edge. Integrators sample these settled outputs synchronously.
An equal 16-bit signature does not prove the absence of faults.

## Separate injection variant

core_scan_fault is generated from core_scan_test, retaining its GPL notice,
all holds, acknowledgement synchronizers and reset-only exit policy.
FAULT_ID=0 disables injection. Each nonzero generic selects exactly one
synthesizable stuck-at mux, active only at a legal capture. No force/deposit
or post-capture storage flip is used.

The defined universe contains eight input-net sites, each with SA0 and SA1:
incrementer operand bits 2, 3, 16, 31 and instruction input bits 0, 1, 16, 31.
Odd IDs are SA0, even IDs SA1. PC faults precede the original PC+4 adder;
instruction faults precede the actual IF/RF data input. Eligibility is fixed
before simulation and does not depend on detection. All other nets are outside
this initial universe. In particular, aligned operand bits 0/1 are constants,
adder-internal carry nodes are not exposed by the original abstraction, and
other operand/output/fetch-mux nets need a larger follow-up inventory.

Only this eight-site, sixteen-fault universe is used as the denominator.
No full processor fault coverage is claimed. Fault-free instructions at the
held address are constant, so one polarity of an instruction site can be
unobservable. Such cases remain eligible and must be reported undetected.

## Independent experiment checks

Each fault run starts from reset, uses the same generator configuration and
executes all 256 patterns. The inherited independent scan model checks every
edge, actual serial feedback, protected state on all CPU phases, suppressed
writes, entry/exit and restart against the original processor.
An independent fault transformation in the checker predicts the functional
adder/input response before capture; this expected word never drives the DUT.
The actual pre-edge scan-out alone drives the hardware MISR.

Per-pattern reports record actual captured, expected and serially unloaded
words and actual MISR signatures. Python independently compresses the actual
unloaded responses and compares them with VHDL, then compares the faulty
streams with the separately executed fault-free stream. A direct mismatch
with an equal final signature is explicitly classified as aliasing.

PLPF feedback is the real scanned FF. A fault can therefore influence later
feedback-dependent scan stimuli through the response/unload history. Both runs
use identical seeds and control schedules; the campaign measures detection
under that closed-loop architecture rather than claiming identical scan words
at every pattern.

Payload cycles are measured as SHIFT+CAPTURE+UNLOAD (33024 at 256 patterns).
Reset, entry, acknowledgement, pause and restart overhead are reported separately
from elapsed simulated clock periods. Coverage at a prefix compares signatures
at that prefix; prefix signature coverage need not be monotonic because aliases
can appear or disappear. Direct coverage accumulates first response mismatches.

Basic Control is the verified initial approach. Unfiltered, constant n=3,
Swap/Moving and matched-WTM comparisons remain explicit follow-up work.
The remaining 656 pipeline bits are unchanged.

## Reproduction

From the repository root:

~~~powershell
python lbist/scripts/build_phase5bc.py
python lbist/scripts/misr_golden.py --unit
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source lbist/scripts/run_all_phase5bc.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source lbist/scripts/synth_phase5bc.tcl
~~~

All runners use a 20 ms watchdog, below the 100 ms limit. Unexpected assertions,
missing completion, missing signatures or incomplete fault records fail
verification; a correctly detected injected fault is a valid experiment.
Full WDB/VCD are local artifacts, with portable WCFG and VCD-validated SVG
previews tracked alongside CSVs and graphs. Previous-phase files are hashed
before generation and checked after the campaign.
