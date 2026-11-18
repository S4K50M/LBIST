# FPGA implementation, area and estimated power

All three actual processor configurations synthesized, placed and routed using **Vivado 2025.1.1**, installed **xc7a35tcpg236-1** device support and the Artix-7 license. No board, paid IP or paid-only target was used. **None meets the requested 50 MHz setup/hold constraints.**

| Routed configuration | LUT | FF | LUTRAM | BRAM36 equivalent | DSP | CARRY4 | Latches | LUT utilization | FF utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A: original processor | 5380 | 2035 | 0 | 1 | 7 | 715 | 0 | 25.8654% | 4.8918% |
| B: scan + isolation | 6360 | 3101 | 0 | 0 | 7 | 715 | 0 | 30.5769% | 7.4543% |
| C: complete programmable LBIST | 6511 | 3240 | 0 | 0 | 7 | 725 | 0 | 31.3029% | 7.7885% |

The FPGA has 20,800 LUTs and 41,600 FFs. BRAM is expressed in 36 Kb equivalents: A uses two RAMB18 primitives. MMCM count is one in each configuration; actual pruned clock buffers are listed in the CSV/native reports. There is no single scalar utilization percentage across unlike FPGA resource types.

| Increment | LUT delta | LUT overhead | FF delta | FF overhead |
| --- | ---: | ---: | ---: | ---: |
| A → B | 980 | 18.2156% | 1066 | 52.3833% |
| A → C | 1131 | 21.0223% | 1205 | 59.2138% |
| B → C | 151 | 2.3742% | 139 | 4.4824% |

These are actual existing-implementation costs. The B/C storage implementation loses A's BRAM inference, so FF overhead includes that mapping change. Debug outputs are open and fault/debug hardware is absent from the production top, but existing helper coding/inference side effects remain. The figures do not isolate an ideal 64-mux scan cost. No memory refactor was performed.

| Configuration | Routed WNS (ns) | TNS (ns) | WHS (ns) | Setup failing endpoints |
| --- | ---: | ---: | ---: | ---: |
| A | -77.054 | -5443.598 | -2.793 | 356 |
| B | -77.212 | -7334.359 | -2.728 | 1157 |
| C | -76.315 | -7796.277 | -2.726 | 1278 |

C's first worst setup path has 96.283 ns data delay, from the registered control path `MM_cop0_reg_reg[2]_replica_4` to `U_ALU/U_HI/state_reg[30]`. Synthesis success is not timing closure. Maximum frequency is not derived from a single WNS number in this multiphase design.

## Comparable boundary and constraints

`lbist/final/final_fpga_top.vhd` selects `DESIGN_CONFIG=0/1/2`; all use the same part, common MMCM/reset wrapper, rebuilt hierarchy, and default optimization/place/phys-opt/route flow. Functional instruction/data ports remain real inputs. B uses `core_scan_test`; C adds the existing controller, router (including LFSR/phase shifter/PLPF/Basic/Swap/Moving) and safe MISR/comparator. No `core_scan_fault`, testbench, artificial keep bus or debug observation port drives production outputs.

The processor interface exceeds the device's 106 available I/O pins. These are **out-of-context processor implementations with virtual ports**, not complete Basys3 systems or bitstreams. They exclude external caches/memory/I/O peripherals and package I/O buffers/loading.

The 100 MHz primary feeds one MMCM with 1 GHz VCO and related 50 MHz outputs. Native generated-clock waveforms are clk `{0 10}`, phi1 `{15 20}`, phi2 `{0 5}` ns, each period 20 ns. Phi3 `{5 10}` is unused by the core and prunes. Related clocks are not grouped asynchronous. Virtual input/output delays are 2 ns max / 0.5 ns min relative to clk; uncertainty is 0.1 ns. Reset assertion is false-pathed only to asynchronous control pins, with two-cycle synchronized release. `check_timing` reports no unconstrained internal endpoints; its one no-input-delay item is the intentionally false-pathed reset.

Warnings remain: virtual ports lack HD.PARTPIN_LOCS and the input clock lacks a board-context HD.CLK_SRC, limiting external path/clock-delay estimates. DSP input/output pipeline warnings and CFGBVS/CONFIG_VOLTAGE warnings remain; no board bitstream is claimed. Internal setup/hold violations are retained. Original RTL sensitivity-list warnings remain in the logs.

## Power: actual activity, partial mapping, limited conclusions

The five approaches use the **same routed C hardware**, not five different area counts. Each has its own production-instance RTL SAIF at 50 MHz, 256 patterns, window **610–661150.001 ns**, duration **660540001 ps**. The window includes all SHIFT/CAPTURE/UNLOAD work and three pauses, and excludes entry/reset/restart. All five match the verified production wrapper and golden signatures. A/B separately use their own actual original/production-scan core activity under the same lwsw workload, window **100–1670 ns**.

| Approach | Measured SHIFT WTM | C dynamic estimate (W) | C total estimate (W) | Directly matched design nets |
| --- | ---: | ---: | ---: | ---: |
| Direct | 50.1154% | 0.124 | 0.193 | 1963/14106 |
| Constant n=3 | 7.0665% | 0.123 | 0.192 | 1963/14106 |
| Basic | 19.9764% | 0.124 | 0.192 | 1963/14106 |
| Swap | 17.7531% | 0.123 | 0.192 | 1963/14106 |
| Moving | 19.8701% | 0.124 | 0.192 | 1963/14106 |

Static power is 0.069 W; common MMCM power is 0.106 W. See [power_comparison.csv](power_comparison.csv) for clocks, logic, signals, DSP/BRAM, confidence and status. Values have native 0.001 W report precision, are independently rounded, and may not sum exactly. Plot error bars indicate rounding only, not uncertainty bounds.

**These whole-boundary values are assumption-dominated diagnostic estimates.** Direct SAIF matching is only **13.9161%** of C design nets; Vivado reports Medium overall confidence and propagates activity/defaults on the rest. Unknown-state warnings occur on uninitialized/unused processor nets. This does not establish reliable whole-processor power savings or a physically meaningful ranking from the 0.001 W differences. Timing failure also prevents treating 50 MHz as a demonstrated hardware operating point. WTM is not equivalent to total FPGA power.

A/B functional dynamic estimates are 0.187/0.163 W with 21.5681%/13.9894% direct mapping, respectively. The difference is not evidence that scan reduces physical power: memory inference and annotation differ. [functional_comparison.csv](power/functional_comparison.csv) retains the actual results, separate from the LBIST workload comparison.

As a limited fallback, [subsystem_comparison.csv](power/subsystem_comparison.csv) records the same native routed IF/RF hierarchy, including absorbed decode/comb logic. Direct prints 0.002 W; the other hierarchy rows are not printed at native report resolution and are marked `NOT_REPORTED`. No missing watt values are inferred. Fine subsystem ranking and reliable full-processor activity estimation remain unresolved limitations. The detailed reports/XML and [source-tag counts](power/annotation_by_boundary.csv) preserve the available evidence. Source tags include hierarchical aliases and therefore use a different denominator from Vivado's direct design-net coverage; they must not be combined as a coverage percentage.

All cases use typical process, 25°C ambient and default nominal supplies (Vccint/Vccbram 1.0 V, Vccaux 1.8 V). Generic Vivado thermal defaults include medium board/heatsink and 250 LFM airflow. These assumptions are consistent across runs and **not a calibrated Basys3 thermal model**. No package/board/regulator/external-memory power or physical measurement is included. RTL SAIF omits timing glitches.

The SAIF mapper renames hierarchy only (including VHDL generate scopes) and verifies every switching record is unchanged. [Mapping manifest](power/saif_mapping_manifest.json) records hashes/transformations; [activity windows](power/activity_windows.csv) records equal durations. XSim's SAIF exporter embeds a legacy `VERSION 2020.2` string; native compilation/execution logs identify the actual tool as 2025.1.1.

## Files and execution status

- `baseline/`, `scan_enabled/`, `full_lbist/`: native synthesis/routed utilization, timing, clock, interaction, DRC, initial vectorless power and execution logs.
- `synthesis_summary.csv`, `timing_summary.csv`, `area_overhead.csv`, `approach_comparison.csv`, `power_comparison.csv`: extracted actual results and explicitly shared area.
- `power/`: actual own-activity power reports, detailed hierarchy/XML reports, unmatched nets, switching-source reports and status.
- `figures/`: area, dynamic estimate and WTM-versus-estimate graphs (SVG/PNG/PDF).

Initial export attempts failed because `report_switching_activity` needed explicit object arguments. They did not invalidate completed synthesis/routing; raw `status.csv` files retain those failures. Corrected exports reopened the saved routed checkpoints. Final `power/status.csv` records seven successful SAIF exports and `power_details_console.log` records five successful detailed exports. All six final WDB/WCFG pairs were reopened and every displayed signal verified. The C synthesis invocation retained an obsolete `CONFIGURATION=2` warning; actual elaboration binds `DESIGN_CONFIG=2`, confirmed by the retained production router. The final runner uses the corrected name. Incorrect early A/B development attempts are not used in the tables.

## Reproduce

From the repository root, with Python/matplotlib and Vivado installed:

```powershell
$vivado = 'E:/2025.1.1/Vivado/bin/vivado.bat'
python lbist/scripts/build_final_sources.py
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_final_activity.tcl *> Results/Final/activity_console.log
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_final_functional_activity.tcl *> Results/Final/functional_activity_console.log
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_final_fpga_analysis.tcl *> Results/Final/fpga_console.log
python lbist/scripts/map_final_saif.py
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_final_power.tcl *> Results/Final/power_console.log
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_final_power_details.tcl *> Results/Final/power_details_console.log
python lbist/scripts/summarize_final_power.py
python lbist/scripts/build_final_report.py
```

Run sequentially to limit RAM use. Isolated projects and routed checkpoints are under `%TEMP%/vl405_final_fpga/{configuration}`; deleting the cache requires repeating synthesis/route. Device probing is available through `lbist/scripts/probe_final_device.tcl`. The flow needs normal Vivado user-cache write access. It does not generate a board bitstream or require a physical board.
