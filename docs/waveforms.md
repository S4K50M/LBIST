# Phase 2 and Basic Control waveforms

Actual XSim captures and saved layouts are generated separately from the existing
verification reports. Processor RTL, LBIST RTL, testbenches, baseline data and
prior report CSVs are not changed by waveform generation.

## Open the default Basic Control capture

In a fresh **Vivado GUI Tcl console**, from the repository root:

```tcl
source ./lbist/scripts/open_lbist_waveforms.tcl
```

Or use the absolute path:

```tcl
source {C:/Users/Saksham Setia/OneDrive/Desktop/VLSI/cmips/lbist/scripts/open_lbist_waveforms.tcl}
```

This opens the full trace and saved signal layout for the 64-bit Basic integration
run with beta=20 (alpha=gamma=22). It does not rerun the test. To choose another:

```tcl
set ::WAVEFORM_CASE tb_phase2_integration
source ./lbist/scripts/open_lbist_waveforms.tcl
```

A PowerShell viewer is also provided (starts standalone XSim GUI):

```powershell
& ./lbist/scripts/open_lbist_waveforms.ps1
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_lfsr_16
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_basic_integration_L64_B36
```

Its `-XSim` parameter defaults to `E:/2025.1.1/Vivado/bin/xsim.bat`; override it
for a different installation. Use a fresh viewer session or close a previously
opened simulation first. Each WCFG and matching WDB should remain together.

## Captures available

[Phase 2 waveform folder](../Results/Phase2/waveforms/):

| Case name | Signals emphasized |
| --- | --- |
| tb_lfsr_16 | Clock, reset, enable, LFSR state/output, zero/custom seed states |
| tb_phase_shifter | LFSR state, current/future bits, enable, manual-state test |
| tb_plpf_optimized | Mode, source bits, feedback, filter output, modeled chain |
| tb_plpf_dynamic | Mode/active mode, validity, state, feedback chain/output |
| tb_phase2_integration | Entire LFSR -> lookahead -> filter -> scan-chain path |

[Phase 3 Basic waveform folder](../Results/Phase3/Basic/waveforms/):

- `tb_basic_controller_L64_B20`: position, mode, completion, reset and pauses.
- `tb_basic_integration_L64_B0`
- `tb_basic_integration_L64_B8`
- `tb_basic_integration_L64_B16`
- `tb_basic_integration_L64_B20`
- `tb_basic_integration_L64_B28`
- `tb_basic_integration_L64_B36`

Every case has these artifacts:

| Extension | Contents |
| --- | --- |
| .wdb | Full-time native XSim signal history, including integer/Boolean signals |
| .wcfg | Ordered signals, radix settings, matching WDB reference, initial 0..300 ns zoom |
| .vcd | Actual logic/vector signal transitions during 0..512 ns; portable to VCD viewers |
| .svg | Browser/IDE-readable preview rendered from VCD, first 300 ns |
| .log | Self-checking test output from this waveform capture run |

`waveform_summary.csv` records completion time, WDB size and actual capture status.
A WCFG is a layout, not the signal history: the matching WDB is needed to inspect
values. WDB/VCD files are generated locally and ignored by Git; configurations,
previews, logs and summaries can be tracked. Regenerate databases after a fresh
clone. XSim does not export VHDL Boolean or natural signals through this VCD path;
those remain available in the WDB/WCFG. The preview is not fabricated test data.

## Reading the traces

In Basic integration, `count` is the pre-edge shift position. Binary mode `00`
selects n=3 filtering; `11` selects unfiltered n=1. For beta=20 the regions contain
22,20,22 enabled shifts. Inspect `mode`, `count`, `done`, `scan_enable`, `scan_in`,
and hexadecimal `chain`. At the completing edge, count rolls to zero and done
pulses; the mode after that edge describes the following shift. Expand `chain`
to inspect individual FFs; bit 0 is the scan-input stage. Clock period is 2 ns.

The initial view is 300 ns for readable edges. Use Zoom Fit or enter a later time
range to see the rest of the full WDB, including end-of-test reset/hold cases.
The optimized PLPF unit's long rate-measurement epochs change modes around
131 us and 262 us; its short VCD/preview does not cover those epochs. Phase 2
unit tests also deliberately inject invalid modes/unknown feedback in negative
cases; those expected test windows may display X values.

## Regenerate

From the repository root in PowerShell:

```powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/generate_waveforms.tcl
python ./lbist/scripts/render_waveform_previews.py
```

Subset runners are `run_phase2_waveforms.tcl` and `run_basic_waveforms.tcl`.
For generation in a fresh Vivado GUI, set `::env(WAVEFORMS_GUI)=1` then source a
runner. The dedicated waveform project is inside the already ignored Phase 2
`work/waveform_project` directory. It does not open or overwrite the original
verification projects, logs or reports. Each capture records signals before the
first clock edge and requires normal testbench completion without failure markers.
All runs are bounded by 2 ms; their original self-checking assertions remain active.

Native static viewing follows AMD's documented
[open_wave_database / open_wave_config workflow](https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/open_wave_database).

## Verification of these artifacts

All 12 simulations completed with PASS markers. All 12 saved WDB/WCFG pairs
were reopened successfully in Vivado 2025.1.1, including native integer counters.
The audit is saved in `Results/Phase2/waveforms/static_validation.log`. XML,
VCD/SVG artifact presence, database references, and prior-file SHA-256 integrity
were checked. All 475 pre-existing repository files were unchanged.

Recheck native viewing with:

```powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/verify_waveforms.tcl
```


## Phase 3 additions: Swap, Moving and comparisons

The original 12 Phase 2/Basic captures above are preserved. Phase 3 adds five
native captures in Results/Phase3/Swap/waveforms, Moving/waveforms and
Comparison/waveforms. Two unit tops, two four-chain integrations and one
five-approach comparison each have a WCFG, full-history WDB, portable VCD,
actual XSim log and SVG preview.

WDB and VCD are Git-ignored generated files. WCFG, SVG, CSV and logs are
reviewable repository artifacts. After a fresh clone, regenerate native
databases before using either opening script. The new generator writes only
new capture folders and additional focused Basic images; it never regenerates
the old captures.

~~~powershell
# Regenerate five Phase 3 captures, previews and native/temporal checks.
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/generate_phase3_waveforms.tcl

# Equivalent entry through the original generator, from the Vivado Tcl console:
set ::WAVEFORM_SCOPE phase3
source ./lbist/scripts/generate_waveforms.tcl

# Rerender from existing captured VCDs without running HDL:
python ./lbist/scripts/render_waveform_previews.py --phase3

# Check VCD behavior independently:
python ./lbist/scripts/phase3_waveform_analysis.py --verify-only
python ./lbist/scripts/test_phase3_waveforms.py
~~~

The two set/source lines use the Vivado Tcl console. For full
experiments, CSVs, matplotlib charts and native checks, run run_all_phase3.tcl.
A focused generation need not rerun the other 64 simulation cases and leaves
their unexecuted statuses as NOT RUN when collecting from a fresh clone.

Native WDB covers every enabled shift through successful completion. The
portable VCD covers 0..12 us, including full 64-bit patterns, pause/resume and
the complete captured Moving cycle. Simulation-only vector mirrors expose
integer counters in VCD; native debug outputs and per-chain alpha/gamma buses
remain available in WDB. There are no RTL changes made just for rendering.

### Open an existing local database

~~~powershell
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_swap_integration_L64_B16
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_moving_integration_L64_B16
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_phase3_comparison_L64_T20
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_basic_integration_L64_B20
~~~

The first two names accept the optional _N4 suffix. In Vivado, set
::WAVEFORM_CASE to the same case name, then source open_lbist_waveforms.tcl.
The default Basic case is unchanged. Use PHASE3_PYTHON to select Python when
needed; matplotlib and numpy are required for figures. The runner detects a\nWindows Python installation with those packages because Vivado puts its own\nbundled Python first in PATH. Python -E also ignores the PYTHONHOME and
PYTHONPATH overrides without changing the Vivado process environment.

### Boundary previews and data provenance

[Basic focused previews](../Results/Phase3/Basic/waveforms/basic_beta20_first_switch.svg),
[Swap boundary](../Results/Phase3/Swap/waveforms/swap_beta16_first_switch.svg),
[Swap per-chain placement](../Results/Phase3/Swap/waveforms/swap_beta16_variation.svg),
[Moving boundary](../Results/Phase3/Moving/waveforms/moving_beta16_first_switch.svg)
and [Moving progression](../Results/Phase3/Moving/waveforms/moving_beta16_progression.svg)
derive entirely from real VCD samples.

Basic, Swap and Moving each have overview, first_switch, second_switch,
pattern_wrap, pause_resume and consecutive_patterns SVGs. Integrations also
show the actual LFSR state, lookahead bits, active/valid PLPF modes, scan input,
past-bit feedback and all scan storage in an integration SVG. Swap adds separate
per-chain modes and a placement map. Moving adds movement-counter wrap and a
placement map. The comparison stores separate Swap beta18 and Moving beta19
views; the additive Basic beta20 views use the actual comparison Basic engine.

Focused windows use about 20 ns, with decimal counters, binary modes and a
00=n=3 / 11=n=1 legend. Real X/U/Z values remain visible. An annotated rising
edge samples the PRE-edge mode; its displayed POST-edge mode prepares the
next shift. Event labels sit above the waveforms.

The analyzer discovers event times from captured transitions and checks them
against an independent counter/schedule model. It checks every clock edge,
scan pause, complete-pattern boundary, full scan-register contents, LFSR
advancement, phase-distinct inputs, Swap parity and Moving reach/wrap. The
waveform-checker tests deliberately corrupt counter, mode and scan-data reads,
and saved SVG values, and require rejection. A preview outside the captured
range is rejected. Every saved waveform SVG interval is read back from XML
and matched against source VCD values and transition times; the results are
in phase3_preview_validation.csv.

Provenance is recorded in Comparison/reports/phase3_preview_sources.csv
(source VCD, SHA-256, hierarchy, available end time) and
phase3_waveform_events.csv (event timestamp, pre/post count, mode and index).
phase3_waveform_summary.csv records actual capture behavior. Native reopening
alone is not accepted as evidence of temporal correctness.

~~~powershell
# Audit all 12 preserved and five new local WDB/WCFG pairs:
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/verify_waveforms.tcl
~~~

To audit only the five new captures in a fresh clone, set
::WAVEFORM_VERIFY_SCOPE to phase3 before sourcing verify_waveforms.tcl.
Actual final verification counts are recorded with the Phase 3 results.
