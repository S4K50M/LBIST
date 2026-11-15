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
