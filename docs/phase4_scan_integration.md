# Phase 4: initial 64-bit IF/RF scan insertion

## Original behavior and the shared-state implementation

The original reg_IF_RF in cMIPS/vhdl/pipestages.vhd resets both 32-bit outputs
asynchronously to zero when rst=0. On a rising clk, ld=0 loads PCincd_d and instr;
ld=1 holds. The inventory counts 64 directly scannable vector bits here. The
other stages contain partially reset state, Boolean values and an ALU enumeration;
they are not converted in this phase.

lbist/rtl/reg_IF_RF_scan.vhd uses exactly one 64-bit state vector:

| Physical positions | Functional mapping |
| --- | --- |
| q(63 downto 32) | PCincd_q |
| q(31 downto 0) | RF_instr |
| q(0) | scan-input stage and scan_feedback |
| q(63) | scan-output stage |

The priority is asynchronous active-low reset, rising-edge scan shift,
rising-edge active-low functional load, then hold. Scan shifts q left and
inserts scan_in at bit zero, overriding either value of ld. To load a desired
64-bit word in 64 cycles, send bits 63 through 0. Read scan_out before each edge;
the edge then overwrites the oldest bit. Scan and functional operation share
these actual FFs. There is no shadow bank, clock gating or derived clock.

Reset polarity must be adapted when connecting the existing generators:
generator_rst=not rst. Hold reset through a rising edge because the unchanged
Basic controller resets synchronously, while the scan bank and LFSR reset
asynchronously. Releasing reset between edges prepares the first scan bit
without consuming a shift.

When scan_enable=0, ld=1 pauses/holds scan storage. ld=0 instead performs a
functional capture. Deasserting scan enable alone therefore does not imply
a scan pause unless the functional load is also inhibited.

## Independent verification

tb_reg_IF_RF_scan instantiates both the original and scan-capable stages. It
checks SCAN01..SCAN15 with a separate 64-bit scoreboard: asynchronous reset
between edges, original load/hold behavior, 256 random functional cycles, scan
priority, every state bit, pre-edge scan-out, post-edge feedback, one-edge
capture, unload, mode transitions and reset during incomplete shifting.
Two seeds are tested. Each run includes 256 complete main scan patterns with
zero/one/alternating/walking-one/walking-zero/deterministic-random words.
Falling edges must leave storage unchanged.

tb_if_rf_plpf_integration connects the existing LFSR, phase shifter, Basic
controller and dynamic PLPF directly to reg_IF_RF_scan.scan_feedback. It uses
the independent Phase 2 sequence/filter functions and a separate storage
scoreboard. Canonical configuration: L=64, beta20, alpha=gamma=22, seed AAAA.
Controller, LFSR and scan bank sample the same enabled edge. Pre-edge mode
determines that shift; post-edge mode prepares the next shift.

Canonical measurement spans 1024 complete patterns. Beta0/16/36 provide
additional 256-pattern checks. After measurement, the test captures
PC=1234ABCD and instruction=89EF5670 on one functional edge and unloads exactly
64 bits. The model advances the LFSR/controller during unloading and checks
that unloading simultaneously loads the next pattern. Capture itself does
not advance either generator.

Unit PATTERNS<256 and illegal Basic beta1 are separate expected time-zero
configuration rejections. Standalone successful tests emit TB_COMPLETE without
a failure assertion. Every watchdog is bounded by 20 ms; Tcl rejects missing
completion or unexpected failures.

## Metrics

The measurement window excludes functional capture and its subsequent unload.
Reports retain actual integer counts and derive:

- Serial toggle rate: transitions between consecutive scan inputs / (shifts-1).
- Normalized scan-in WTM: sum of temporal input transitions weighted 64..1 per
  pattern / (patterns*2080), including the first-stage initial value.
- Scan FF switching fraction: all 64 FF changes / (64*enabled shifts).

An independent loaded-pattern calculation must match temporal WTM exactly on
every pattern. The Eq. 3 estimate uses low-region probability 1/14 and high
region probability 1/2. Symmetric beta20 gives 23/112 = 20.535714% estimated WTM.
A fixed absolute measured/estimated tolerance of two percentage points allows
finite-sequence and mode-boundary effects. The CSV computes exact ratios from
integer counts, avoiding rounding in VHDL real'image output. These are scan
activity metrics, not physical power measurements.

## Separate processor variant and functional regression

lbist/core_scan/core_scan.vhd retains the original GPL-3.0 notice. Its only
processor RTL edits are the entity/architecture name, four scan ports, and
the PIPESTAGE_IF_RF instance replacement. RF/EX, EX/MM, MM/WB, PC, register
bank, exceptions, MMU and other logic remain unchanged. The original core.vhd
and pipestages.vhd are preserved byte-for-byte.

tb_core_scan_regression derives its memory, cache, peripheral and clock/reset
environment from the original tb_cMIPS. An original core drives the existing
environment; core_scan consumes identical responses and drives separate
comparison signals. All functional output ports are compared at CPU phase
edges. Tcl compares PC, IF/RF outputs, IF/RF load enable, operands, writeback
data and write controls every 5 ns after reset. VCD analysis independently
compares both pipeline traces and confirms the real feedback/output mapping.

The normal case uses the original inst_wait connection. A second case inserts
a shared 60-ns instruction wait at 400 ns, then restores the original response.
It must exercise IF/RF stall/hold, preserve differential equivalence and print
the same ten lwsw output words before normal termination.

Original prog.bin, data.bin, input.data and serial.inp are copied into each
isolated simulator working directory. Their content is not changed. Empty
data/input files are valid for this program. No placeholder image is generated.

The original processor intentionally ends simulation with a severity failure
for wait 0. Tcl checks both exit decoders before that assertion, then requires
the known breakpoint at PC=00000038. The log collector compares all ten printed
words against the saved baseline and independently expected -10..-1 sequence.
It accepts only the known termination, not an arbitrary simulator error.

## Processor-wide scan isolation remains incomplete

Adding four scan ports to the IF/RF stage does not freeze the processor.
PCload and all later stage enables still follow ordinary pipeline/stall logic.
The architectural register bank continues using WB_wreg, and memory/peripheral
requests still follow unmodified active-low write/address-valid controls.
Interrupts, exceptions, flushes, coprocessor state and caches are still live.

Consequently this variant is verified only with scan disabled at processor
level. Standalone register and PLPF tests prove genuine shifting/capture of the
same 64 FFs, but arbitrary CPU-level scan patterns must not be shifted while
the rest of this core runs. There is no verified scan-entry protocol, global
freeze, write masking, full-processor capture protocol or state restoration.
Asserting reset would clear this scan bank too and is not a useful isolation
solution for shifting it.

Future work needs a reviewed processor-wide test-mode design, architectural
write/peripheral isolation, interrupt/exception policy and controlled clock/
capture sequencing before enabling processor-level scan operations. No further
656 pipeline bits, MISR or fault model are implemented here.

## Automation, waveforms and preservation

[Actual results](../Results/Phase4/README.md) and [case CSV](../Results/Phase4/phase4_verification_summary.csv)
record measured status and durations.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase4.tcl
~~~

Individual entry points are run_if_rf_scan.tcl, run_if_rf_plpf.tcl,
run_core_scan_regression.tcl, run_phase4_regressions.tcl and synth_if_rf_scan.tcl.
generate_phase4_waveforms.tcl regenerates the three new captures;
verify_phase4_waveforms.tcl reopens their WDB/WCFG pairs and validates VCD/SVG
behavior. phase4_analysis.py recollects existing logs; --require-all refuses
completion if any planned case is missing or failed.

Phase 4 scripts import existing common Python selection, waveform formatting,
VCD parsing, preview rendering and saved-SVG checking functions without editing
Phase 1-3 tools or their outputs. Native WDBs retain full runs. VCDs capture
all selected signals through completion. SVG event windows use real transition
timestamps and about 20 ns around boundaries; previews retain actual unknowns
before valid reset. Legacy unreset pipeline data may remain unknown until used;
the newly scanned state must be defined after reset.

The tool working directory and projects are under Results/Phase4/work. All
logs/reports/waveforms go under Phase4. WDB/VCD and working projects are ignored
by Git. Native traces must be regenerated after a fresh clone. New scripts
never invoke earlier report writers. audit_phase4.py records SHA-256 before/
after protection for original sources/results, including preserved waveforms.
