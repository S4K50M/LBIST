# Phase 5B — real processor serial response analysis

The actual processor completed 256 patterns and accumulated exactly 16,384
pre-shift UNLOAD bits. The independent golden and actual final signature are
both **AFBC**. Python checks all 256 intermediate signatures against actual
captured/unloaded responses; an additional VCD checker verifies each clock
edge, hold interval and completion-qualified comparator.

The MISR polynomial is x^16+x^12+x^5+1, seed zero, MSB-first, left shift,
feedback=old_signature(15) XOR response_bit, XOR mask 1021.
Reset is asynchronous active-low; synchronous clear overrides enable.
The signature holds during SHIFT, CAPTURE, pause and DONE.

The five 256-bit unit streams (zeros, ones, alternating, walking ones and
deterministic random) passed, with clear priority and enable/hold checks.
The unit simulation took 25.670 us; the real processor run took 661.6002 us.
Its measured payload is 16,384 SHIFT + 256 CAPTURE + 16,384 UNLOAD =
33,024 enabled test cycles. Reset/setup/acknowledgement/pause/restart account
for another 56.01 elapsed 20 ns clock periods.

Normal and stalled fault-disabled core regressions match the original core,
emit FFFFFFF6 through FFFFFFFF and terminate at the expected PC 00000038,
in 1.670 us and 1.730 us. All processor experiments also check protected
storage on every CPU phase, suppress writes, and verify reset-only exit/restart.

Results:

- [Verification](reports/misr_verification.csv) and
  [all intermediate golden/actual signatures](reports/misr_golden_signature.csv).
- [Functional regressions](reports/functional_regression.csv).
- [Unit waveform layout](MISR/waveforms/misr_unit.wcfg).
- [Processor waveform layout](Integration/waveforms/fault_free.wcfg) and
  [actual scan-out entering MISR](Integration/waveforms/fault_free_first_unload.svg).
- [Validated SVG intervals](reports/waveform_validation.csv).
- [Protected-file hashes](reports/protected_integrity.csv).

Synthesis for xc7a35tcpg236-1:

| Boundary | FF | LUT | Latches |
| --- | ---: | ---: | ---: |
| MISR alone | 16 | 18 | 0 |
| Serial analyzer plus signature comparator | 16 | 18 | 0 |
| Test controller plus MISR/comparator | 39 | 61 | 0 |

See [synthesis.csv](reports/synthesis.csv) and the utilization reports.
These are standalone analyzer resources, with no fault mux or processor debug
overhead included. The complete processor-plus-MISR has not received a new combined utilization measurement;
no whole-chip overhead, timing closure or power claim is made.

The real processor integration is in the separate phase5bc_processor_check
variant. Synthesizable response analysis is in misr_16, misr_signature_checker
and lbist_misr_top. The verified Phase 5A controller, scan bank, LFSR, PLPF,
Basic controller and isolation helpers are reused unchanged.
The fault-capable core has injection disabled in the fault-free run.

See the [design, audit, exact fault sites and commands](../../docs/phase5bc_misr_faults.md)
and [Phase 5C results](../Phase5C/README.md).
Run run_all_phase5bc.tcl for all simulations, reporting and native waveform
validation; synth_phase5bc.tcl is a separate optional synthesis command.
WDB/VCD histories and work projects remain local Git-ignored artifacts.

Signatures are configuration-specific. Equal signatures can alias faulty
responses; AFBC is not evidence of complete CPU fault freedom. Coverage is
limited to the explicitly enumerated Phase 5C fault universe.
