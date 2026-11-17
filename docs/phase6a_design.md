# Phase 6A: completion safety and five-approach processor comparison

## Completion correction

The historical Phase 5B signature checker equates DONE with a valid result.
The unchanged test controller also enters DONE on abort or illegal restart.
Those old modules are retained for reproduction; new integrations should use
phase6a_controlled_misr, which has the same ports and generics as the historical
lbist_controlled_misr. phase6a_safe_misr provides the separate counting/analyzer
boundary used in processor verification.

Validity now requires active reset release, DONE, final controller state,
no controller error or sticky stream-protocol error, all expected captures,
all expected response bits, all completed unload words, and a matching completed
pattern count from the controller. A capture opens one response word; exactly
CHAIN_LENGTH unload edges close it. Repeated captures, unauthorized unload
edges and overlong streams poison validity until reset.

DONE, error_status, signature_valid, signature_match and fault_detected are
distinct. MATCH/MISMATCH outputs remain low until validity. An injected circuit
fault is not a controller error: a complete faulty response stream remains
valid and can report fault_detected. The last unload edge updates both the
MISR and completion counters; comparison settles after that edge.

Eight directed scenarios with the actual controller cover normal completion,
abort in SHIFT/CAPTURE/UNLOAD, a missing bit despite controller completion,
illegal restart, reset partway through UNLOAD, and completed faulty responses.
Normal/faulty cases also check the final edge and comparator settling.

## Router and scan-stream policy

Mapping is 000 Direct, 001 Constant n=3, 010 Basic, 011 Swap, 100 Moving.
Other codes report configuration_valid=0 and clamp scan_in=0. Approach and
beta are fixed generics in processor experiments. The host must reject an
invalid configuration and hold configuration stable throughout a test.
An odd beta is rejected when Basic is selected; its unused instance is safely
rounded only to permit legal odd-beta Moving configurations to elaborate.

All approaches reuse the original LFSR, phase shifter and dynamic PLPF. Direct
uses its unfiltered mode; Constant always uses its low-toggle mode. The feedback
wire is the actual IF/RF input-stage FF, and scan_out is its actual Q(63).
MISR input is the real pre-shift scan_out on enabled UNLOAD edges.

The LFSR advances on every SHIFT and UNLOAD edge, never CAPTURE or pause.
Each test pattern still costs 64 SHIFT + 1 CAPTURE + 64 UNLOAD = 129 payload
cycles. UNLOAD loads disposable bits; the next SHIFT loads a fresh pattern.

Swap and Moving have two scheduling instances, both of the unchanged Phase 3
controller: one enabled only for SHIFT and one only for UNLOAD. Exactly one
scheduling instance advances per accepted scan edge. Each completes one
64-bit word per captured pattern. Thus SHIFT and UNLOAD both use schedule p;
the next SHIFT uses p+1. Swap alternates on consecutive captured patterns;
Moving advances one window position and wraps at L-beta-27.

This avoids the single-controller trap where UNLOAD increments pattern parity
again and every SHIFT sees the same Swap orientation. It also preserves the
existing optimizer's one-schedule-step-per-captured-pattern interpretation.
Basic uses one controller advancing on both phases because its 64-bit schedule
is invariant. Original Phase 3 RTL is unchanged.

Physical order is scan-in -> alpha -> beta -> gamma -> scan-out; chronological
input order is gamma, beta, alpha. For single chain Swap, gamma alternates
32 and 32-beta. Moving gamma is 14 + p mod (37-beta). Both scheduling lanes
are independently checked against those formulas and actual scan FF state.

The standalone router test uses the actual reg_IF_RF_scan storage, not a
substitute hardware shift model. It verifies every bit and feedback edge over
36 captures' worth of SHIFT/UNLOAD words per approach, including two Moving
wraps, then tests invalid mode values. The separate processor campaigns use
the real isolated core_scan_fault, original capture adder and instruction path.

## Golden model, coverage and measurement

The independent Python reference starts from the established, verified entry
state PC=2C, IF/RF=0000002CAE040000, LFSR=AAAA, held ROM instruction=1460FFFA.
It computes every routed bit, scan FF update, aligned PC+4 response, fault mux
effect, unload stream and polynomial signature. VHDL independently checks
mode selection, source indexing, actual FF feedback, each scan bit, protected
storage on all CPU phases, writes and every MISR update.

Golden signatures are specific to approach, beta, scheduling policy, initial
state, ROM, 256-pattern count and zero MISR seed. Basic beta20 must reproduce
the complete original Phase 5C campaign, including every final faulty signature.
Other approaches never borrow Basic's golden.

The original eight input-net sites and both polarities remain the fixed
16-fault denominator for every configuration. Original program/processor,
capture muxes, fault sites, reset/isolation, 20 ns clock, and MISR polynomial
x^16+x^12+x^5+1 remain unchanged. Circuit faults are enabled only for legal
capture. No force/deposit or scan-output bit-flip substitutes for injection.

There are five initial configurations (85 cases) plus seven unique
optimizer-selected configurations (119 cases): 204 campaign cases total,
including twelve fault-free runs and 192 faulted runs. The initial betas are
20 for Basic/Moving and 16 for Swap. Target requests are 10%, 15%, 20%.
All target configurations have their own reference and all sixteen faults.

Measured WTM is sum(weighted scan-FF transitions) divided by
256*64*sum(1..64), with physical input-stage weight 1 and output-stage weight64.
Capture transitions are excluded. FF switching fraction uses 256*64*64.
The reported serial toggle rate samples the concatenated SHIFT input
subsequence, excluding disposable UNLOAD bits. These are scan-load activity
metrics, not physical power measurements.

Optimizer estimates use its original exact-rational regional model. Feasible
targets still have integer-beta quantization. Measured matching additionally
requires absolute target error <=0.5 percentage points; requested/estimated/
measured errors remain visible. Direct and Constant are fixed references.
Swap 20% is infeasible at L=64: the nearest legal beta18 estimate is 19.1964%,
reported separately without a fabricated measured matched-target result.

Direct detection is cumulative response mismatch; intermediate signature
mismatch and final MISR detection are separate. Equal final signatures after a
direct mismatch are aliases. Prefix MISR coverage is allowed to decrease.
Coverage thresholds use actual prefix signatures, with UNREACHED retained.
All incomplete/misconfigured runs fail analysis rather than becoming undetected.

## Boundaries and follow-up

The Phase 5A processor boundary, idle-fabric entry acknowledgement, CPU clock
relationships, state holds, write masks and reset-only exit remain unchanged.
The held instruction is constant: one polarity of each selected instruction
input can stay unexcited. Expanded input/output/carry fault inventories and
varying instruction stimulus are a second-stage follow-up, excluded from
the original-16 comparison and its denominator. The remaining 656 pipeline
scan bits are unchanged.

Standalone synthesis uses xc7a35tcpg236-1, matching the previous analyzer
measurements. New safe-analyzer and controller/analyzer counts can be compared
at those boundaries; router counts include its LFSR and both scheduling lanes.
No summed production-chip area or physical power is inferred from those counts.
Full processor-plus-router synthesis and constrained timing remain unmeasured.

## Reproduction

From the repository root, run build_phase6a.py, then run_all_phase6a.tcl with
Vivado 2025.1.1 batch mode. Separate router, campaign and regression runners
are provided; synth_phase6a.tcl and verify_phase6a_waveforms.tcl are separate
checks. Campaign workers accept config_first/config_last or an explicit
configs list. Optional resume_verified skips completed single-case logs;
reuse_completed enables batch resume for unchanged source/configurations.
The aggregate runner reruns faults by default. Final independent analysis rechecks every response and
signature. Work projects and large WDB/VCD remain local; portable WCFG, SVG,
CSV and logs are tracked.

Every individual simulation has a 20 ms watchdog and must terminate below
100 ms simulated time. No overall campaign wall-clock limit is imposed.
Baseline commit 40c9649 defines the protected prior-phase source/report set,
audited by SHA-256 after execution.
