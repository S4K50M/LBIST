# Phase 3 completed verification

Verified on 2026-11-15 with Vivado/XSim 2025.1.1. **All 69 planned simulation
cases passed:** 55 normal completions and 14 expected invalid-configuration
rejections. All 22 Python checks passed (six legacy optimizer, nine Phase 3
optimizer and seven captured-waveform checks).

The longest simulation completed at **410.8011 us**. Every run was bounded by
20 ms and finished below the required 100 ms limit. The five new waveform
captures regenerated successfully. All **17 local WDB/WCFG pairs** (12 preserved,
five new) reopened in Vivado; 50 actual event timestamps and 44 saved waveform
SVGs passed independent source-data checks.

## Simulation status and duration

| Suite | Positive | Expected rejection | Result |
| --- | ---: | ---: | --- |
| Swap controller | 7 | 5 | PASS |
| Swap integration | 3 | 0 | PASS |
| Moving controller | 8 | 5 | PASS |
| Moving integration | 3 | 0 | PASS |
| Five-approach comparisons | 15 | 0 | PASS |
| Existing Phase 2 regressions | 5 | 0 | PASS |
| Existing Basic regressions | 14 | 4 | PASS |

Unit tests verify 256 complete patterns plus reset/pause scenarios, completing
in 14.3631..102.4331 us. The four-chain integrations/comparisons verify 1024
complete patterns. Their actual durations are:

| Chain length | Simulation duration | Enabled shifts per chain |
| ---: | ---: | ---: |
| 64 | 131.4571 us | 65536 |
| 128 | 262.9131 us | 131072 |
| 200 | 410.8011 us | 204800 |

Each comparison runs direct LFSR, constant PLPF n=3, Basic, Swap and Moving with
identical seed AAAA, polynomial, 2-ns clock, initialization and enable schedule.
Chain phases are 0,257,514,771, with separate real scan-input FF feedback.
These are correlated phases of one LFSR. The independent VHDL reference checks
every scan FF after every shift and checks chronological/loaded-pattern WTM
identity exactly.

The 15 comparisons cover L=64/128/200 and requests 10/15/20/25/30%. The reports
contain 75 comparison measurements plus six dedicated integration measurements,
324 per-chain diversity records and 42336 physical-exposure records.

## Representative measured WTM: L=64, controlled request 20%

| Approach | Beta | Estimated WTM | Measured WTM | Absolute target error (pp) | Serial toggle rate | Actual FF toggle fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct LFSR | 0 | 50.000000% | 49.992112% | NA | 50.000763% | 49.976593% |
| Constant n=3 | 0 | 7.142857% | 7.152170% | NA | 7.137789% | 7.136112% |
| Basic | 20 | 20.535714% | 20.123056% | 0.123056 | 20.240711% | 20.231712% |
| Swap (nearest feasible) | 18 | 19.196429% | 18.890193% | 1.109807 | 18.996338% | 18.988395% |
| Moving | 19 | 19.866071% | 19.501214% | 0.498786 | 19.601358% | 19.590563% |

Direct/constant rows are references with no requested control target.
Every row above observed 1024 distinct four-chain pattern tuples. Per-chain
distinct counts are reported separately; a sum across chains is not a global
unique count.

Swap's maximum estimated WTM is 19.196429% at L=64. Requests 20/25/30% use beta18
and are explicitly nearest-feasible. At L=128, requests 25/30% are outside its
23.883929% maximum; at L=200, 30% exceeds its 25.571429% maximum. Graphs mark
these points with a black x. They are not equivalent matched-target points.

Quantization, measured/requested error and measured/estimated error are separate
CSV fields. The largest measured/estimated difference across the 75 comparison
records was 0.462038 percentage points, within the fixed 2-pp test bound. The
exact optimizer evaluates Eq. 3 weighted sums over every pattern and chain in
the complete control cycle; finite-run schedule estimates are reported too.

## Observed schedules and physical exposure

Physical order is IN -> alpha -> beta -> gamma -> OUT; chronological loading is
gamma -> beta -> alpha. Controllers emit 00=n=3 and 11=n=1 using a two-bit slice
per chain. Modes before a rising edge determine that edge's shift.

With L=64 and beta16, Swap alternates physical windows 16..31 and 32..47 by
pattern/chain parity. It reaches 32 physical positions per chain over its two
patterns. Moving visits all 21 legal placements from (alpha,beta,gamma)=(34,16,14)
through (14,16,34), then wraps. It reaches exactly 36 of 64 physical positions,
14..49. Required 14-bit low regions at each end constrain reach.

At the requested 20% comparison settings, Basic beta20 reaches 20 positions;
Swap beta18 and Moving beta19 both reach 36. Exposure is a count of patterns
receiving n=1 data, not fault coverage or a switching probability.

## CSVs, model output and evidence

- [Every simulation case and duration](reports/phase3_simulation_summary.csv)
- [Comparison measurements and feasible ranges](reports/phase3_wtm_comparison.csv)
- [Per-chain observed pattern diversity](reports/phase3_pattern_diversity.csv)
- [Physical scan-position exposure](reports/phase3_position_exposure.csv)
- [Exact configurations, complete cycles and expected exposure](reports/phase3_configuration_schedules.json)
- [Captured waveform summary](reports/phase3_waveform_summary.csv)
- [Actual event timestamps and pre/post-edge states](reports/phase3_waveform_events.csv)
- [VCD source hashes and hierarchy](reports/phase3_preview_sources.csv)
- [Saved SVG interval verification](reports/phase3_preview_validation.csv)
- [Protected-file SHA-256 audit](reports/protected_file_integrity.csv)
- [Source files added/modified and hashes](reports/phase3_source_manifest.csv)
- [Final native audit, opening aliases and Tcl dispatch checks](logs/final_native_validation.log)
- [Successful waveform generation](logs/waveform_generation_console.log)
- [Comparisons and unchanged-design regressions](logs/comparison_regression_console.log)
- [Phase 3 optimizer tests](logs/optimizer_tests.log)
- [Legacy optimizer tests](logs/basic_optimizer_regression.log)
- [Waveform checker and intentional-corruption tests](logs/waveform_checker_tests.log)

Individual raw XSim logs and compile/elaboration logs are under the three new
logs folders, with a per-case CSV under reports/cases. Successful expected
negatives require CONFIG_ERROR at time zero and no normal completion marker.
No failed/absent simulation is reported as PASS.

## Report figures and focused waveforms

- [Estimated/measured WTM](figures/wtm_comparison.svg)
- [Requested/measured WTM](figures/requested_vs_measured_wtm.svg)
- [Target error](figures/wtm_target_error.svg)
- [Actual scan FF switching](figures/ff_switching_vs_target.svg)
- [Observed unfiltered-position exposure](figures/position_exposure.svg)
- [Observed distinct pattern tuples](figures/distinct_pattern_counts.svg)
- [Representative captured mode boundary](figures/representative_mode_switch.svg)
- [Captured Moving progression](figures/moving_control_progression.svg)

Matplotlib figures have SVG/PNG versions. Boundary and progression images are
derived from actual captured transitions, with source hashes and event times.
All 44 saved waveform SVGs were parsed back and every plotted interval checked
against VCD values and real transition times. Intentional saved-SVG corruption
is rejected by the checker.

New native captures are in ../Swap/waveforms, ../Moving/waveforms and waveforms.
The additional Basic beta20 previews are in ../Basic/waveforms. Each integration
has overview, boundaries, rollover, pause/resume, consecutive-pattern and
source/feedback SVGs. Swap adds per-chain variation; Moving adds movement wrap.

WDB retains full history through completion. VCD covers the first 12 us,
including full captured movement cycles and pauses. WCFG/SVG/CSV/logs are
available as repository artifacts; WDB and VCD are generated locally and
Git-ignored. Full traces are not claimed as committed.

## Files and preservation

Added RTL: swap_controller.vhd, moving_controller.vhd and the separate
multi_chain_phase_shifter.vhd. Added five requested testbench tops and three
shared checking/reference files. Added the exact optimizer, unified plan/log
collection, temporal VCD/SVG checker, tests and seven requested Tcl runners,
plus a separate regression runner and common execution code.

Extended the six existing waveform scripts and two documentation files.
555 of 563 pre-existing files are byte-for-byte unchanged; the remaining eight
are the explicitly extended waveform scripts/documentation. This includes
unchanged processor files, Phase 2/Basic RTL and benches, prior results, native
traces, layouts, screenshots and logs.

Architecture details:
[Swap](../../../docs/swap_control.md),
[Moving](../../../docs/moving_control.md),
[comparison definitions](../../../docs/phase3_comparison.md),
[waveform workflow](../../../docs/waveforms.md).

## Reproduce on Windows

Run from the cmips repository root with Vivado 2025.1.1 and Python 3.9+ containing
matplotlib/numpy. The runner detects a Windows Python installation and uses -E
to avoid Vivado's PYTHONHOME/PYTHONPATH overrides. PHASE3_PYTHON can specify an
explicit executable.

~~~powershell
python ./lbist/scripts/test_basic_wtm_optimizer.py
python ./lbist/scripts/test_phase3_wtm_optimizer.py
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase3.tcl
python ./lbist/scripts/test_phase3_waveforms.py

# Regenerate only the five new waveform captures and previews:
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/generate_phase3_waveforms.tcl

# Open a locally generated capture:
& ./lbist/scripts/open_lbist_waveforms.ps1 -Case tb_moving_integration_L64_B16
~~~

run_all_phase3.tcl runs all 69 cases, collects/checks logs, generates charts and
waveform previews, and reopens the five new WDB/WCFG pairs. Its regression
outputs go only into new folders. The final audit in this workspace additionally
reopened the 12 preserved captures and exercised all four opening aliases.

After a fresh clone, native databases must be regenerated. The new runner does
not require the old 12 ignored databases; to audit all 17, first regenerate the
legacy databases with the existing generate_waveforms.tcl workflow described
in docs/waveforms.md, then run verify_waveforms.tcl.

## Scope and limitations

The paper's Figure 8 is followed for alpha=L-beta-gamma. The inconsistent
L/2 expression in adjacent prose is documented. Inclusive movement endpoints,
14-bit minima and deterministic wrap are explicit implementation policy.
Swap rejects odd chain lengths; Moving supports them. Maximum RTL length is
4096 and maximum chain count is 16; measured sweeps use the lengths above.

This is stimulus-only functional verification. There is no processor scan
insertion, capture logic, MISR, CUT fault model, area estimate or physical
power measurement. Pattern diversity and exposure do not establish stuck-at
or transition fault coverage. No acceptance item remains unverified for the
tested Phase 3 configurations.

## Status by individual case

PASS (reject) means the intended invalid configuration was rejected at time zero.
All other durations below are actual simulated time from TB_COMPLETE.

| Case | Result | Time (us) |
| --- | --- | ---: |
| tb_swap_controller_L64_B0_N4 | PASS | 32.8011 |
| tb_swap_controller_L64_B16_N4 | PASS | 32.8011 |
| tb_swap_controller_L64_B18_N4 | PASS | 32.8011 |
| tb_swap_controller_L128_B16_N4 | PASS | 65.5691 |
| tb_swap_controller_L200_B32_N4 | PASS | 102.4331 |
| tb_swap_controller_L28_B0_N1 | PASS | 14.3631 |
| tb_swap_controller_L64_B16_N3 | PASS | 32.8011 |
| tb_swap_controller_L65_B16_N4 | PASS (reject) | 0 |
| tb_swap_controller_L64_B19_N4 | PASS (reject) | 0 |
| tb_swap_controller_L64_B65_N4 | PASS (reject) | 0 |
| tb_swap_controller_L1_B0_N4 | PASS (reject) | 0 |
| tb_swap_controller_L64_B16_N17 | PASS (reject) | 0 |
| tb_swap_integration_L64_B16_N4 | PASS | 131.4571 |
| tb_swap_integration_L128_B16_N4 | PASS | 262.9131 |
| tb_swap_integration_L200_B32_N4 | PASS | 410.8011 |
| tb_moving_controller_L64_B0_N4 | PASS | 32.8011 |
| tb_moving_controller_L64_B16_N4 | PASS | 32.8011 |
| tb_moving_controller_L64_B36_N4 | PASS | 32.8011 |
| tb_moving_controller_L128_B16_N4 | PASS | 65.5691 |
| tb_moving_controller_L200_B32_N4 | PASS | 102.4331 |
| tb_moving_controller_L28_B0_N1 | PASS | 14.3631 |
| tb_moving_controller_L65_B17_N4 | PASS | 33.3131 |
| tb_moving_controller_L64_B16_N4_I5 | PASS | 32.8011 |
| tb_moving_controller_L64_B37_N4 | PASS (reject) | 0 |
| tb_moving_controller_L64_B65_N4 | PASS (reject) | 0 |
| tb_moving_controller_L1_B0_N4 | PASS (reject) | 0 |
| tb_moving_controller_L64_B16_N4_I21 | PASS (reject) | 0 |
| tb_moving_controller_L64_B16_N17 | PASS (reject) | 0 |
| tb_moving_integration_L64_B16_N4 | PASS | 131.4571 |
| tb_moving_integration_L128_B16_N4 | PASS | 262.9131 |
| tb_moving_integration_L200_B32_N4 | PASS | 410.8011 |
| tb_phase3_comparison_L64_T10 | PASS | 131.4571 |
| tb_phase3_comparison_L64_T15 | PASS | 131.4571 |
| tb_phase3_comparison_L64_T20 | PASS | 131.4571 |
| tb_phase3_comparison_L64_T25 | PASS | 131.4571 |
| tb_phase3_comparison_L64_T30 | PASS | 131.4571 |
| tb_phase3_comparison_L128_T10 | PASS | 262.9131 |
| tb_phase3_comparison_L128_T15 | PASS | 262.9131 |
| tb_phase3_comparison_L128_T20 | PASS | 262.9131 |
| tb_phase3_comparison_L128_T25 | PASS | 262.9131 |
| tb_phase3_comparison_L128_T30 | PASS | 262.9131 |
| tb_phase3_comparison_L200_T10 | PASS | 410.8011 |
| tb_phase3_comparison_L200_T15 | PASS | 410.8011 |
| tb_phase3_comparison_L200_T20 | PASS | 410.8011 |
| tb_phase3_comparison_L200_T25 | PASS | 410.8011 |
| tb_phase3_comparison_L200_T30 | PASS | 410.8011 |
| regression_tb_lfsr_16 | PASS | 131.0812 |
| regression_tb_phase_shifter | PASS | 8.2647 |
| regression_tb_plpf_optimized | PASS | 393.2090 |
| regression_tb_plpf_dynamic | PASS | 8.1991 |
| regression_tb_phase2_integration | PASS | 131.4551 |
| regression_basic_unit_L64_B0 | PASS | 32.7971 |
| regression_basic_unit_L64_B8 | PASS | 32.8031 |
| regression_basic_unit_L64_B16 | PASS | 32.8031 |
| regression_basic_unit_L64_B20 | PASS | 32.8031 |
| regression_basic_unit_L64_B28 | PASS | 32.8031 |
| regression_basic_unit_L64_B36 | PASS | 32.8031 |
| regression_basic_unit_L28_B0 | PASS | 14.3651 |
| regression_basic_unit_L65_B21 | PASS | 33.3151 |
| regression_basic_unit_L64_B1 | PASS (reject) | 0 |
| regression_basic_unit_L64_B65 | PASS (reject) | 0 |
| regression_basic_unit_L1_B0 | PASS (reject) | 0 |
| regression_basic_unit_L64_B38 | PASS (reject) | 0 |
| regression_basic_integration_B0 | PASS | 131.4571 |
| regression_basic_integration_B8 | PASS | 131.4571 |
| regression_basic_integration_B16 | PASS | 131.4571 |
| regression_basic_integration_B20 | PASS | 131.4571 |
| regression_basic_integration_B28 | PASS | 131.4571 |
| regression_basic_integration_B36 | PASS | 131.4571 |
