# Phase 5A pre-implementation isolation audit

The source audit inspected original core, pipeline, exception, auxiliary, ALU
and register-file processes. The proposed boundary is the processor entity,
not the external clock generator or autonomous peripheral timers.

| State | Required control |
| --- | --- |
| PC/CP0/TLB registers | register32/registerN hold enables |
| RF/EX, EX/MM, MM/WB | load-bank hold enables |
| Exception pipeline | hold enables including resetless IF/RF exception bank |
| CAUSE/LLbit/RANDOM | guard all three core sequential processes |
| COUNT | counter CE freezes increment and load |
| Stall and exception flags | FFD hold enable |
| Register file | freeze both RAM writes and registered reads |
| ALU HI/LO | hold both internal register32 banks |
| Selected IF/RF | legal scan or one capture only |
| External fabric | mask i_aVal,d_aVal,wr,b_sel; fabric_idle entry contract |
| Mode control | sticky isolation latch; reset-only exit |
| Decoder temporaries | feed NOP during isolation; suppress simulation exit assertion |
| Caches/peripheral timers | explicit exclusion: autonomous device state not frozen |

Only IF/RF changes during scan or capture. All unrelated storage needs explicit
hold enables; clocks keep their original waveforms. Reset remains asynchronous
active-low and overrides holding. Both register-file architectures and internal
RAM read registers must be covered. COUNT, CAUSE, RANDOM, LLbit, phi2 flags and
ALU HI/LO cannot be omitted.

Entry requires an external fabric_idle acknowledgement (no outstanding bus
transaction). A falling-clk sticky hold masks requests. Separate two-stage
falling-edge synchronizers establish the phi1 register-file read hold and phi2
flag hold. A two-stage rising-clk acknowledgement confirms both phase holds;
the controller waits for this acknowledgement before SHIFT. A snapshot is
taken only after all domains acknowledge, then monitored across all CPU phases.
Autonomous external clocks/peripheral timers are excluded; CPU requests and
actual memory/peripheral writes must remain inactive.

Exit is reset-only. Dropping test_mode cannot resume corrupted pipeline state.
Pending IRQ/NMI pulses during test are not queued and must be reissued after
reset. No clock gating is introduced.

The final capture policy routes the actual scan-loaded IF/RF PC field through
the original PC alignment/increment adder. Only the adder operand has a test
mux; the architectural PC stays held. The lower word samples the raw instruction
input from a side-effect-free ROM at the held architectural PC. Test capture
bypasses the ordinary opcode annul/flush selection explicitly. Thus responses
depend on the shifted pattern through a real functional adder, with a limited
instruction-fetch cone rather than a full CPU combinational test. No complete
test-only 64-bit response injection is used.

The implemented state coverage is recorded in
[phase5a_state_coverage.json](../Results/Phase5A/phase5a_state_coverage.json).
The observation vector contains 4,287 meaningful encoded bits, including the
full register-file arrays and read registers; this is an observation encoding,
not an extra scan chain or a physical flip-flop count. All three processor
experiments reported zero protected-state changes and zero actual memory or
register writes. The earlier store-entry experiment exercised 2,065 suppressed
memory-write attempts.
