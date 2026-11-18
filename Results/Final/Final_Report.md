# VL405: Scan-Based Low-Switching LBIST for cMIPS32

**Final submission report — repository S4K50M/LBIST.** Historical implementation baseline: commit `2c9b90c` (Phase 6A). Target: Basys 3 Artix-7 `xc7a35tcpg236-1`; tool: AMD Vivado/XSim 2025.1.1. All numerical experiment results below are derived from retained native logs/CSVs. FPGA figures use the final native reports, with analysis stage explicitly identified.

## 1. Abstract

This project implements and verifies a programmable pseudorandom scan-test system around one 64-bit IF/RF pipeline register in cMIPS32. A 16-bit LFSR, combinational phase shifter and dynamic PLPF supply Direct, constant n=3, Basic, Swap and Moving approaches. Processor isolation protects architectural state while a controller performs 64 SHIFT, one CAPTURE and 64 UNLOAD edges per pattern. A completion-safe 16-bit MISR compresses actual serial responses. With 256 patterns, every initial approach detects 12 of the same 16 capture-input stuck-at faults, with no observed final-signature alias. Measured SHIFT WTM spans 7.0665%–50.1154%. These are simulation switching metrics; the FPGA power study is a separate tool estimate. The results establish this limited capture-cone experiment, not whole-processor fault coverage or measured physical power savings.

## 2. Introduction and problem statement

Scan shifting can cause sustained internal transitions. Filtering pseudorandom stimulus offers a controllable activity tradeoff, but it must preserve scan ordering, functional behavior, capture timing and response integrity. The project asks whether the existing filter/control approaches can operate on real cMIPS pipeline storage with reproducible results and safe error handling. The submission freezes the verified Phase 6A architecture. It adds production integration wrappers, final verification, reporting and FPGA analysis; no additional scan chain or fault site is introduced.

## 3. Reference paper and proposed methodology

Kato, Wang, Sato, Kajihara and Wen [1] motivate programmable scan-in activity using modified pseudorandom patterns. This project evaluates that principle on cMIPS. It reuses the established Basic/Swap/Moving schedules and independently checks every applied scan bit. The RTL uses counters and combinational decoders; it does not claim the paper's exact gate structure, silicon area, TEG measurements or general fault-coverage results. This report's measured values come from the repository's own experiment evidence.

## 4. cMIPS32 architecture

cMIPS is a five-stage VHDL processor: instruction fetch, register fetch, execute, memory and writeback [2]. Pipeline boundaries are `reg_IF_RF`, `reg_RF_EX`, `reg_EX_MM` and `reg_MM_WB` in `cMIPS/vhdl/pipestages.vhd`. The original functional core, exception/control logic and register storage are preserved. `docs/scan_register_inventory.csv` records widths, resets, types and scan decisions. Boolean/enumerated state needs deliberate encoding; it is not silently flattened into the implemented chain. The remaining 656 pipeline candidate bits are unscanned.

## 5. LBIST system architecture

![Production architecture](figures/architecture.png)

`final_processor_system.vhd` selects original core (A), scan/isolation core (B), or the complete programmable LBIST core (C). C instantiates the verified controller, router, `core_scan_test` and safe MISR. Real scan Q(0) feeds the filter and Q(63) supplies the analyzer. Approach and golden signature are external configuration inputs held stable throughout a test. Test mode remains a real runtime control. Fault injection and wide debug probes are absent from production C; observation outputs on the core are open.

## 6. LFSR and phase shifter

The polynomial is x^16+x^15+x^13+x^4+1. State bit i denotes sequence position j+i; output is state(0), and feedback is state(15) XOR state(13) XOR state(4) XOR state(0). Reset seeds AAAA; zero/unknown seed protection is retained. The period bench checks all 65,535 unique nonzero states, sequence recurrence, bit balance, pause, resume and reset. The phase shifter exposes state(0), state(1), state(2) as current/next/next-next without extra cycles. The integrated experiment uses one scan chain; historical multi-chain standalone tests do not imply multiple processor scan chains.

## 7. PLPF design and WTM control

The dynamic PLPF is combinational. Mode 11 passes the current LFSR bit (n=1). Mode 01 combines two consecutive bits and real scan-input-stage feedback (n=2). Mode 00 similarly uses three bits (n=3). For feedback zero, the selected bits are ANDed; for feedback one they are ORed. Invalid mode holds feedback and raises invalid status. There is no extra shift for mode changes.

Measured WTM = 100 × sum over 256 patterns, 64 SHIFT edges and physical stages k of (k+1) × [Q_k changes], divided by 256 × 64 × 2080. Input-stage weight is 1 and output-stage weight is 64. CAPTURE and UNLOAD transitions are excluded from this metric. Serial toggle rate and unweighted scan-FF switching are separate CSV columns. Theoretical WTM is an optimization estimate, not an assertion that a finite deterministic sequence reaches an arbitrary requested target.

## 8. Basic, Swap and Moving controllers

Basic beta=20 uses physical regions alpha/beta/gamma=22/20/22. Physical order is scan-in → alpha → beta → gamma → scan-out; chronological injection reverses it. Swap beta=16 alternates gamma=32 and 16 on successive captured patterns. Moving beta=20 uses gamma=14+p mod 17 and alpha=64−20−gamma. The minimum 14-cell filtered ends restrict the reachable unfiltered region. The offline optimizer chooses legal integer lengths; it is not on-chip optimization hardware.

Swap and Moving have separate SHIFT and UNLOAD scheduling instances. Both process schedule p; only the next SHIFT uses p+1. This avoids double-advancing the schedule during disposable unload shifts. LFSR state advances on every accepted SHIFT or UNLOAD, and holds during CAPTURE/pause. C's shared runtime router uses beta=20 and Swap beta=16 for all five modes; changing runtime mode does not change synthesized area.

## 9. Scan-chain insertion

Only IF/RF is replaced by verified `reg_IF_RF_scan`: 32 PC-increment bits plus 32 instruction bits. The combined word is PCincd_q & RF_instr, with serial insertion at bit0, output at bit63 and MSB-first unload. Scan disabled reproduces original load/reset behavior. The unit bench checks all 64 positions, feedback, reset, load/hold and scan priority. Native original-versus-scan processor regression compares internal pipeline values and functional buses under lwsw and memory stalls.

## 10. Processor test-mode isolation

Entry waits for idle external fabric and synchronized phase acknowledgements. The isolation boundary holds PC, downstream pipeline registers, general registers, exception/CP0 storage and side effects. Memory and register write attempts are monitored; committed writes remain suppressed. Only a legal CAPTURE updates IF/RF. Tests perturb interrupts, waits, errors, readiness, pause and attempted early exit. Exit is reset-only; arbitrary resume from destructively shifted IF/RF state is unsupported. Autonomous external peripherals are outside the protected core boundary.

## 11. MISR response compression

The analyzer polynomial is x^16+x^12+x^5+1 (mask 1021), seed zero. Each UNLOAD edge uses actual pre-shift scan_out. The last response bit updates the signature before comparison settles. Phase 6A validity requires DONE phase 101, successful controller completion, 256 captures, 16,384 response bits, 256 complete unload words, matching controller pattern count and no sticky stream/controller error. MATCH and fault_detected stay low until signature_valid. A completed faulty stream is valid and may mismatch; abort/incomplete streams cannot claim MATCH. Eight safety scenarios cover normal/faulty completion, abort in each active phase, missing response, illegal restart and reset. Historical unsafe Phase 5B files remain unchanged for provenance and are not used in production C.

![Abort does not produce a valid signature](figures/misr_abort_trace.png)

## 12. Fault-injection methodology

The primary universe contains eight sites × SA0/SA1: increment_operand bits 2,3,16,31 before the original +4 adder, and instruction_input bits 0,1,16,31 before IF/RF capture. Fault muxes act only during legal CAPTURE. Injection is on real capture inputs, not scan-output corruption. Upper response is the aligned scan-loaded operand plus4 through the original processor adder; lower response is actual held-ROM instruction 1460FFFA at PC 2 C. Other processor logic remains held. This small cone is not the full datapath, ALU or instruction-set universe. Detected IDs are 1–8,10,11,14,16; IDs 9,12,13,15 have the already-held instruction polarity and are not excited. `tables/fault_inventory.csv` supplies exact sites and activation paths.

## 13. Verification and experimental setup

All accepted simulations remain below 100 ms simulated time. The full 256-pattern processor experiments finish at 661.6002 us. Original Phase 1–6A artifacts are retained. Finalization rechecks the archived 204 experiments against independent stimulus/response/MISR/activity models, rather than rewriting historical campaigns. Fresh native tests exercise generator/filter/controllers, scan, isolation, safe analyzer/router, functional equivalence, and production C against the verified reference. The production fixture checks functional ports, real scan interface and analyzer outputs at all CPU phases, while recording its own switching activity.

| Category | Passed | Total |
| --- | --- | --- |
| Fresh essential XSim | 13 | 13 |
| Fresh production equivalence/activity | 5 | 5 |
| Fresh original/production-scan functional activity | 1 | 1 |
| Fresh representative original-universe fault | 1 | 1 |
| Fresh native WDB/WCFG pairs reopened | 6 | 6 |
| Archived processor experiments independently rechecked | 204 | 204 |
| Archived waveform figures rechecked against VCD | 45 | 45 |
| Earlier files unchanged by SHA-256 | 2486 | 2486 |

The expected original `RF_STOP_SIMULATION` assertion at breakpoint PC00000038 terminates lwsw. It counts as success only with matching differential state, the exact breakpoint and ten printed values FFFFFFF6…FFFFFFFF. Other failures are rejected. The old incomplete sixteen-replica Moving native attempt is excluded; its smaller retries provide complete accepted records. Fresh script errors, if any, remain in execution logs and are not relabeled as simulation passes. See `Verification/` and `final_verification_summary.md`.

## 14. WTM results

| Approach | Beta | WTM | Coverage | Golden | Aliases | Patterns | Cycles |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Direct | fixed | 50.1154% | 12/16 | 9A6A | 0 | 256 | 33024 |
| Constant n=3 | fixed | 7.0665% | 12/16 | 5DCB | 0 | 256 | 33024 |
| Basic | 20 | 19.9764% | 12/16 | AFBC | 0 | 256 | 33024 |
| Swap | 16 | 17.7531% | 12/16 | 9C7F | 0 | 256 | 33024 |
| Moving | 20 | 19.8701% | 12/16 | F21E | 0 | 256 | 33024 |

![Measured WTM](figures/wtm_comparison.png)

![Requested and measured WTM](figures/target_vs_measured.png)

| Approach | Target | Beta | Estimate | Measured | Within 0.5 pp |
| --- | --- | --- | --- | --- | --- |
| Basic | 10 | 4 | 9.8214 | 9.4801 | False |
| Basic | 15 | 12 | 15.1786 | 14.6669 | True |
| Basic | 20 | 20 | 20.5357 | 19.9764 | True |
| Swap | 10 | 4 | 9.8214 | 9.4866 | False |
| Swap | 15 | 12 | 15.1786 | 15.0168 | True |
| Swap | 20 | 18 | 19.1964 | NOT_RUN (infeasible) | False |
| Moving | 10 | 4 | 9.8214 | 9.4148 | False |
| Moving | 15 | 12 | 15.1786 | 14.8169 | True |
| Moving | 20 | 19 | 19.8661 | 19.1090 | False |

Target 10% optimizer configurations achieve 9.4148–9.4866%: close to one another but outside the declared ±0.5 percentage-point target tolerance. At 15%, Basic/Swap/Moving achieve 14.6669/15.0168/14.8169%, respectively. Swap 20% is infeasible with the legal L64 bounds; nearest beta 18 estimates 19.1964%. Moving beta 19 is the optimizer-selected 20% candidate and measures 19.1090%; the separately tested beta 20 calibration measures 19.8701%. Neither is relabeled. All exact feasibility and pairwise match decisions are retained in `tables/feasibility.csv` and `tables/matched_comparisons.csv`.

## 15. Fault-coverage results

![Original fault coverage](figures/fault_coverage.png)

All five initial approaches reach 75% of the 16 eligible capture-input faults after four complete patterns. All retain 12/16 direct and final-MISR detections at 256 patterns. No final alias is observed in these deterministic experiments. Four unexcited faults produce equal direct responses and equal signatures; they are not aliases. A 16-bit signature still has a finite alias risk for other responses and workloads; zero observed aliases is not proof of zero alias probability. The complete80 primary faulty signatures, first direct/prefix-MISR detection indices and outcomes are retained in the campaign/aliasing CSVs. Additional measured target profiles are secondary evidence and preserve the same denominator.

## 16. Test-time analysis

| Approach | Detected | Undetected | First direct min | First direct max | Mean (detected) | Patterns to 75% | Cycles to 75% | Full cycles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Direct | 12 | 4 | 1 | 4 | 1.7500 | 4 | 516 | 33024 |
| Constant n=3 | 12 | 4 | 1 | 4 | 1.7500 | 4 | 516 | 33024 |
| Basic | 12 | 4 | 1 | 4 | 1.5833 | 4 | 516 | 33024 |
| Swap | 12 | 4 | 1 | 4 | 1.5833 | 4 | 516 | 33024 |
| Moving | 12 | 4 | 1 | 4 | 1.6667 | 4 | 516 | 33024 |

Each test executes 256 × (64+1+64)=33,024 payload cycles:16,384 SHIFT,256 CAPTURE,16,384 UNLOAD. The native experiment has 33,080 rising edges, including 3 paused and 53 other setup/handshake/exit/reset/restart overhead edges. Completion is 200 ps after its final falling edge. Payload time at 50 MHz is 660.48 us; the full bench duration is 661.6002 us. The power window separately spans 610 ns–661150.001 ns, covering the complete payload plus the three pauses and excluding reset/restart. Threshold 516 cycles is an observed coverage prefix; the actual runs still execute all 256 patterns. The architecture uses non-overlapped unloading, so it does not claim an overlapped test-time improvement.

## 17. FPGA Implementation, Area Overhead and Power Estimation

### Comparable hardware and implementation boundary

Vivado's installed part database confirms `xc7a35tcpg236-1`. Native synthesis obtains the Artix-7 license; no paid-only device or IP is selected. Configurations share source versions, flattened/rebuilt out-of-context synthesis, default optimization/place/phys-opt/route settings and common clock/reset infrastructure. A instantiates original `core`; B instantiates `core_scan_test` with an external tester interface; C adds the runtime router, generator, controller and safe MISR. Functional instruction/data ports remain unconstrained runtime inputs so valid processor hardware is retained. Debug ports are open, and neither `core_scan_fault` nor testbench logic is included. No artificial KEEP/preservation bus is added.

The processor's parallel bus exceeds Basys3's 106 available I/O pins. These are therefore **out-of-context placed-and-routed processor configurations**, with virtual ports and no IBUF/OBUF or board bitstream. Counts include the real core and common MMCM/reset infrastructure, but exclude external caches/ROM/RAM/I/O peripherals and physical package I/O loading. They are not whole-board utilization or power. The Basys3 device is the implementation target; a board is not required.

### Clock and interface constraints

One100 MHz primary drives one MMCM (1 GHz VCO) generating related50 MHz processor phases. Relative to clk rising at 0 ns, phi1 is high15–20 ns and phi2 high0–5 ns; phi3 high5–10 ns is unused by the core and may prune. Auto-derived generated clocks maintain the true phase relationship. No asynchronous grouping is applied between these clocks. The virtual external interface assumes2 ns maximum and 0.5 ns minimum input/output delays relative to main clk; uncertainty is 0.1 ns. Reset assertion paths to asynchronous control pins are false-pathed, with synchronous two-cycle release. These are documented interface assumptions, not Basys board memory timing. Native clocks/check_timing/interaction reports expose remaining limitations; multiphase paths can have less than 20 ns available.

### Area and timing

| Configuration | LUT | FF | Latches | BRAM | DSP | Stage |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 5380 | 2035 | 0 | 1 | 7 | Routed |
| scan_enabled | 6360 | 3101 | 0 | 0 | 7 | Routed |
| full_lbist | 6511 | 3240 | 0 | 0 | 7 | Routed |

![Area](FPGA_Analysis/figures/area_comparison.png)

| Comparison | LUT delta | LUT overhead (%) | FF delta | FF overhead (%) | Stage |
| --- | --- | --- | --- | --- | --- |
| Scan/isolation vs baseline | 980 | 18.2156 | 1066 | 52.3833 | Routed |
| Complete LBIST vs baseline | 1131 | 21.0223 | 1205 | 59.2138 | Routed |
| LBIST addition vs scan/isolation | 151 | 2.3742 | 139 | 4.4824 | Routed |

Overhead=(configuration−reference)/reference×100, separately for LUT and FF. The B→C row is incremental LBIST overhead; A→B isolates scan/isolation overhead. Full resource counts include LUTRAM, carry, BRAM, DSP and clock primitives in `synthesis_summary.csv`; LUT/FF utilization uses20,800/41,600 available. Primitive versus packed LUT counts can differ after physical optimization, so report_utilization is the area-table authority. There is no single meaningful FPGA utilization percentage across unlike resources.

Baseline maps two RAMB18 primitives (one 36 Kb equivalent); B/C map no BRAM and use more FFs. Thus the large FF increase includes a storage-inference change in the existing isolation-helper implementation, not simply64 scan muxes. Wide observation ports are open and no debug bus is retained, but source coding/inference side effects are not eliminated by a memory refactor. These are the actual existing-implementation costs. They should not be interpreted as a technology-independent or memory-inference-neutral scan overhead.

| Configuration | Stage | WNS (ns) | TNS (ns) | WHS (ns) | Setup fails | Path (ns) | Closure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | Routed | -77.054 | -5443.598 | -2.793 | 356 | 96.980 | FAIL |
| scan_enabled | Routed | -77.212 | -7334.359 | -2.728 | 1157 | 97.136 | FAIL |
| full_lbist | Routed | -76.315 | -7796.277 | -2.726 | 1278 | 96.283 | FAIL |

All reported50 MHz timing violations are retained. Successful synthesis, placement or routing does not imply timing closure. A maximum achievable frequency is not inferred from20 ns minusWNS because the worst path may cross phase-related clocks. No board operation or maximum frequency is established. Working RTL is preserved rather than altered to repair timing for this submission.

### Switching capture and estimated power

The five LBIST approaches share **one implemented C netlist**. Each approach's exact production wrapper is simulated with its own real switching activity, fixed clock/pattern count/window and the same test environment. The router's unselected scheduling lanes use the same fixed production generics in every trace. A hierarchy-only SAIF mapping preserves all switching records and maps production instances to routed u_system. MMCM/clock activity derives from timing constraints. RTL SAIF does not include routed glitches or establish gate-level timing behavior.

Actual C annotation is 1,963/14,106 design nets (13.9161%) in each mode; Vivado reports Medium overall confidence. Remaining nets use propagation/default activity. Unknown-state warnings also occur on unused or uninitialized processor logic. The whole-C watt values below are therefore **assumption-dominated diagnostic estimates**, not a reliable whole-processor power-saving measurement. A and B have separate actual lwsw SAIF captures over 100–1670 ns; their partial mapping is 21.5681% and 13.9894%, respectively. Their dynamic estimates are 0.187 W and 0.163 W. Because storage inference and annotation differ, that difference is not evidence that adding scan lowers physical power. Vectorless initial reports remain separately labeled historical run artifacts.

| Approach | WTM | Dynamic (W) | Shared LUT | Shared FF | WNS (ns) |
| --- | --- | --- | --- | --- | --- |
| Direct | 50.1154% | 0.124 | 6511 | 3240 | -76.315 |
| Constant n=3 | 7.0665% | 0.123 | 6511 | 3240 | -76.315 |
| Basic | 19.9764% | 0.124 | 6511 | 3240 | -76.315 |
| Swap | 17.7531% | 0.123 | 6511 | 3240 | -76.315 |
| Moving | 19.8701% | 0.124 | 6511 | 3240 | -76.315 |

| Approach | TotalW | StaticW | DynamicW | ClockW | LogicW | SignalsW | BRAMW | DSPW | MMCMW |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Direct | 0.193 | 0.069 | 0.124 | 0.006 | 0.005 | 0.007 | 0.000 | 0.000 | 0.106 |
| Constant n=3 | 0.192 | 0.069 | 0.123 | 0.006 | 0.005 | 0.006 | 0.000 | 0.000 | 0.106 |
| Basic | 0.192 | 0.069 | 0.124 | 0.006 | 0.005 | 0.007 | 0.000 | 0.000 | 0.106 |
| Swap | 0.192 | 0.069 | 0.123 | 0.006 | 0.005 | 0.007 | 0.000 | 0.000 | 0.106 |
| Moving | 0.192 | 0.069 | 0.124 | 0.006 | 0.005 | 0.007 | 0.000 | 0.000 | 0.106 |

![Estimated dynamic power with rounding resolution](FPGA_Analysis/figures/dynamic_power.png)

![WTM versus estimated power](FPGA_Analysis/figures/wtm_vs_power.png)

Error bars indicate only the 0.001 W report rounding (±0.0005 W), not model confidence bounds. Separate static/dynamic/total values are independently rounded and may not sum exactly. The common MMCM alone estimates 0.106 W, dwarfing the reported differences. No statistically or physically established power improvement is claimed from the 0.001 W mode differences.

As a limited fallback, the detailed reports retain the **same routed IF/RF hierarchy** across modes, including any synthesis-absorbed decode/comb logic. Direct reports0.002 W; other per-mode rows are not printed at the native report's hierarchy resolution and are explicitly marked unavailable. Router/controller/MISR source-tag counts and unmatched nets are retained separately; they are not extrapolated into missing watt values. Reliable finer subsystem power ranking and reliable whole-processor activity analysis remain unresolved limitations, rather than fabricated results. `power/subsystem_comparison.csv` and `power/annotation_by_boundary.csv` preserve that boundary and availability.

WTM weights SHIFT transitions in 64 scanFFs. Vivado power includes clocks, processor logic, routing and other resources across SHIFT/CAPTURE/UNLOAD. WTM reduction therefore cannot be equated to total FPGA dynamic-power reduction. Power uses the selected part's default nominal supply assumptions and documented25°C ambient/typical process settings when accepted by Vivado. It is an **estimated on-chip power study**, not physical board measurement. Timing failure at the requested frequency further limits interpreting these estimates as an operable hardware point. `FPGA_Analysis/README.md` records exact mapping, confidence and run status.

All runs accept25°C ambient and typical process. Native supplies include 1.0 V Vccint / Vccbram and 1.8 V Vccaux. Generic Vivado thermal defaults (medium board/heatsink, 250 LFM airflow) are consistent across runs and are not a calibrated Basys3 thermal model. External memory, package I/O and regulator/board losses are excluded. Initial reporting-call failures were repaired using saved checkpoints; all final seven SAIF power exports and five detailed exports completed. The C synthesis log's obsolete CONFIGURATION generic warning is retained: actual elaboration binds DESIGN_CONFIG=2 and the post-route hierarchy check confirms the production router. The reproducible script uses the corrected generic name.

## 18. Discussion and limitations

The strongest result is reproducible control of scan switching with preserved capture ordering and safe completion handling on real cMIPS storage. The small fault universe saturates quickly and cannot distinguish coverage quality among the five approaches. It says little about random-pattern-resistant faults or broader datapath observability. The held instruction limits excitation, and only 64 of 720pipeline candidate bits are scanned. Other architectural state remains protected, not tested. A reset is required after destructive testing. Target quantization and finite sequence effects make measured WTM differ from theoretical targets. FPGA overhead depends on this virtual processor boundary and synthesis settings; timing failure and partial activity annotation must accompany any area/power figures. No 75% whole-processor coverage, measured energy savings, silicon measurement, post-route functional equivalence or successful board deployment is claimed.

## 19. Conclusion

The final submission preserves the verified Phase6A LBIST architecture and consolidates native evidence, reproducible essential demonstrations and an explicit FPGA evaluation boundary. The primary256-pattern original16-fault comparison achieves12 detections per approach without observed final aliases, while measured scan WTM varies with filter/control choice. Safe MISR completion prevents aborted or incomplete streams from reporting MATCH. The available FPGA reports establish actual resource/timing/power estimates at their stated stages and limitations. Broader scan insertion, fault universes and physical measurement are deferred beyond this completed experimental scope.

## 20. References

1. T. Kato, S. Wang, Y. Sato, S. Kajihara and X. Wen, “A Flexible Scan-in Power Control Method in Logic BIST and Its Evaluation with TEG Chips,” IEEE Transactions on Emerging Topics in Computing,8(3),591–601,2020. [DOI10.1109/TETC.2017.2767070](https://doi.org/10.1109/TETC.2017.2767070); [author repository record](https://kyutech.repo.nii.ac.jp/records/6935). Paper results are distinct from this project's measurements.
2. R. A. Hexsel, cMIPS VHDL processor and documentation, supplied GPLv3 sources, `cMIPS/docs/cMIPS.pdf` and `cMIPS/vhdl/`.
3. Digilent, [Basys3 reference manual](https://digilent.com/reference/_media/basys3%3A%20basys3_rm.pdf) and [official master XDC](https://github.com/Digilent/digilent-xdc/blob/master/Basys-3-Master.xdc). Used for target/100 MHz oscillator reference, not as an applied pinout in the virtual-I/O flow.
4. AMD Vivado2025.1.1 installed command help and native utilization/timing/power/switching reports under `FPGA_Analysis/`; `device_probe.log` records tool/part availability.
5. Repository experimental records, `Results/Phase1` (where present), `Results/Phase2`, `Results/Phase3`, `Results/Phase4`, `Results/Phase5A`, `Results/Phase5B`, `Results/Phase5 C`, `Results/Phase6A`, and final read-only audits. Earlier result directories remain authoritative historical evidence.

## Reproduction and evidence index

See [README](README.md), [demo guide](DEMO.md), [final verification summary](final_verification_summary.md), [FPGA study](FPGA_Analysis/README.md), [primary comparison CSV](final_experimental_comparison.csv), and [source provenance](source_manifest.csv). Full per-fault tables are in `tables/`. Relevant actual waveform excerpts are [capture/unload](figures/scan_capture_unload.png) and [abort suppression](figures/misr_abort.svg); the latter is copied unchanged from its VCD-verified historical figure. Native WDB/VCD/SAIF/checkpoints are local regenerable artifacts rather than required Git payloads.
