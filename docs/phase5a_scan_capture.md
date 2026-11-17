# Phase 5A: isolated processor scan, capture and unload

## Scope and isolation boundary

The actual cMIPS core and its existing 64-bit IF/RF scan bank are used.
The original core, pipestages, core_scan, Phase 2/3 generators and all earlier
results remain unchanged. New CE variants are generated from those sources
by generate_phase5a_variants.py and retain their GPL-3.0 notices.

The verified boundary includes every processor storage primitive: PC, unscanned
pipeline banks, exception pipeline, both GPR memory replicas and registered
reads, HI/LO, CP0, COUNT, LL state, all TLB records, RANDOM and phi2 stall flags.
The [pre-implementation audit](phase5a_isolation_audit.md) and
[instance coverage](../Results/Phase5A/phase5a_state_coverage.json) enumerate it.

External caches, bus bridges, clock generators and autonomous peripheral timers
are outside this boundary. The host must assert fabric_idle only when no
transaction is outstanding. Verified scan tests use an actual core with a
zero-wait memory model and a side-effect-free ROM made from the real prog.bin.
No processor model substitutes for the core. Normal-mode tests additionally use
the unchanged original cMIPS memory/cache/peripheral environment.

## Entry and clock-domain holding

Inputs start, pause, abort and fabric_idle obey synchronous setup/hold
requirements. Start requests entry; it does not authorize an immediate shift.
Until the host accepts the entry request, ordinary CPU execution may continue,
including normal interrupt handling. This is the unacknowledged ENTRY part of
controller code 001, not an already frozen processor.

Once fabric_idle is true, a falling-clk sticky master hold:

- disables all clk-domain storage enables;
- masks instruction/data requests, memory writes and byte enables;
- suppresses GPR write strobes;
- masks IRQ/NMI, bus errors, wait inputs and data input to the functional logic;
- makes functional RF decoding see NOP while the real IF/RF bits shift.

Two-stage hold synchronizers update on inactive edges of phi1 and phi2.
The GPR registered reads use the phi1 hold; phi2 flags use the phi2 hold.
Both acknowledgements then pass through a two-stage clk synchronizer.
Only this final acknowledgement permits SHIFT or CAPTURE.
No clocks are ANDed with test control, stopped, or synthesized from it.

Architectural state can settle during entry. The independent snapshot starts
after all domains acknowledge holding, and checks every subsequent CPU phase.
The observation port contains 4,287 meaningful encoded bits, padded to 8,192.
It includes actual GPR arrays/read registers, every storage output and two
decoder diagnostics. This is an observation encoding, not a scan length or a
physical FF-count claim. Enum values have explicit observation encodings;
their original storage types remain unchanged.

Original unreset GPR/pipeline data may be unknown in simulation. Those values
are preserved honestly, not replaced with zeros. Reset-defined scan storage
must remain known. The new VCD reader correctly preserves compressed buses
that contain both known and unknown bits.

## Controller sequence and interface

| Code | Meaning |
| --- | --- |
| 000 | NORMAL |
| 001, ack=0 | ENTRY: request pending, no scan/capture |
| 001, ack=1 | TEST_IDLE: all domains held |
| 010 | SHIFT |
| 011 | CAPTURE |
| 100 | UNLOAD |
| 101 | TEST_DONE |

The controller uses asynchronous active-low reset, matching the processor.
Existing LFSR and Basic reset polarity is adapted with generator_reset=not rst.
Reset is held through a clock edge to align the synchronous Basic controller.

~~~mermaid
stateDiagram-v2
    NORMAL --> ENTRY: start
    ENTRY --> TEST_IDLE: fabric idle and all hold acknowledgements
    TEST_IDLE --> SHIFT
    SHIFT --> CAPTURE: 64 enabled edges
    CAPTURE --> UNLOAD: one ready capture edge
    UNLOAD --> SHIFT: 64 enabled edges, more patterns
    UNLOAD --> TEST_DONE: final pattern
    TEST_DONE --> NORMAL: reset only
~~~

Pause holds counters and suppresses both shift and capture enables.
CAPTURE also waits for capture_ready. An abort or repeated start fails closed
into TEST_DONE with error_status. DONE remains isolated until reset.
The core independently rejects wrong-phase controls, simultaneous scan/capture,
capture repetition and scan before all hold acknowledgements.

The schedule is explicitly non-overlapped:

1. SHIFT loads a complete 64-bit pattern.
2. CAPTURE uses exactly one edge and does not advance either generator.
3. UNLOAD shifts 64 response bits while loading disposable new bits.
4. A fresh SHIFT begins the next complete test pattern.

UNLOAD does not reuse its newly loaded word as the next test pattern.
The LFSR and Basic controller therefore advance 128 times per test pattern.
Basic wraps at both 64-bit boundaries, so its 22/20/22 scheduling remains
aligned. PLPF feedback is the actual IF/RF input-stage Q, never a shadow FF.

## Genuine, limited capture cone

Only during a legal capture, an explicit synthesizable mux routes the
scan-loaded PC half, aligned to four bytes, into the existing U_INCPC
PC+4 adder. The architectural PC and external fetch address remain held.
The instruction half captures the ordinary instruction input supplied by
the ROM at that held architectural PC.

The test mux bypasses the ordinary instruction opcode annul/flush selection.
It does not inject a completed 64-bit expected response. The actual adder
computes the PC response, and the actual 64 IF/RF FFs capture it.

Independent expected response:

~~~text
loaded_pc = independently scored scan_word[63:32]
expected_pc = ((loaded_pc AND FFFFFFFC) + 4) modulo 2^32
expected_instruction = ROM[held_architectural_pc / 4]
expected_response = expected_pc || expected_instruction
~~~

The expected PC is calculated from the reference scan word, not the DUT adder
or captured output. Scan-out is checked before every unload edge, then
assembled independently into the reported response.

The pre-edge adder result is captured. Immediately after the edge, the mux
returns the adder to the architectural PC input; the post-edge combinational
adder output can therefore differ from the response now stored in IF/RF.
The focused real-increment waveform shows both values explicitly.

This exercises the limited alignment/increment path and instruction-input
plumbing. It does not exercise a full processor execution/capture cycle,
ALU datapath, all pipeline logic, or fault detection. No MISR, fault injection,
fault coverage or physical-power result is provided.

## Test exit and restart

Dropping test_mode cannot resume execution: master and domain holds remain
sticky. The attempted exit sets protocol_error, with requests still inactive.
Reset is the only supported exit. Interrupted instruction execution and its
pipeline context are discarded.

The original reset does not clear all GPRs or pipeline data. Firmware must
initialize the state it uses after reboot. The post-test restart comparison
checks every instruction request and every valid data transaction. Inactive
data/address buses are not compared after different drain histories because
the original design deliberately leaves their underlying data unreset.
The independent fresh-reset normal regressions compare all functional ports
and selected pipeline fields through complete program termination.

IRQ/NMI pulses during acknowledged testing are masked and not queued.
After reset, the host must reissue still-required interrupts. No handler can
execute during acknowledged SHIFT/CAPTURE/UNLOAD: PC and exception state hold.

## Verification, tools and reproduction

The register files, CP0/TLB, flags and other storage are checked via a snapshot
at every CPU phase, with actual memory/GPR write monitoring. One case enters
with a pending memory-write request, and another freezes an active GPR write
request, proving suppression rather than only testing an idle pipeline.

Controller cases cover chain lengths 1/2/64, 256 patterns, entry delay, pauses
in SHIFT/UNLOAD, capture-ready delay, exact counters, DONE, abort, illegal
restart and asynchronous mid-pattern reset. Processor cases cover eight
isolation patterns, 256 principal patterns and sixteen pending-write patterns.
Both fresh-reset normal and injected-stall regressions reproduce lwsw output
and intentional breakpoint termination in the original environment.

[Actual results and all cases](../Results/Phase5A/README.md) include native
captures, event timestamps, per-pattern responses, write attempts/actual
writes, synthesis and SHA-256 preservation.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase5a.tcl
~~~

Separate runners are run_test_controller.tcl, run_core_scan_isolation.tcl,
run_core_shift_capture.tcl and run_phase5a_functional.tcl. Native/portable
audits are in verify_phase5a_waveforms.tcl; optional OOC synthesis is in
synth_phase5a.tcl. Python 3.9+ with matplotlib/numpy is detected using the
existing interpreter resolver; PHASE3_PYTHON may override its executable.

Full WDB/VCD histories and work projects are local Git-ignored artifacts.
Readable SVGs and portable WCFG layouts are included with the new sources.
Earlier waveform tools and results are reused without modification.

Synthesis resource counts describe the instrumented debug-observable variant.
No authoritative clock constraints were supplied, so timing closure and
silicon CDC sign-off are not claimed by behavioral XSim verification.
