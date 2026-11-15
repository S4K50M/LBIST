# Phase 3A: Basic Control measured results

Executed on 15 November 2026 with Vivado/XSim **2025.1.1**, Windows.
**18 simulation cases passed:** eight positive controller configurations, four
expected configuration rejections, and six full integration experiments. The six
Python optimizer tests also passed (exact weighted sums, enumeration/optimality,
ties, illegal inputs, range handling, and CLI units).

## Controller verification

Every positive run checked BC01..BC12 with an independent position counter and
256 consecutive complete patterns. Pauses at switching boundaries, synchronous
reset timing, completion pulse clearing during pause and mid-pattern reset passed.

| L | Alpha | Beta | Gamma | Complete patterns | Duration (us) | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 64 | 32 | 0 | 32 | 256 | 32.797100 | PASS |
| 64 | 28 | 8 | 28 | 256 | 32.803100 | PASS |
| 64 | 24 | 16 | 24 | 256 | 32.803100 | PASS |
| 64 | 22 | 20 | 22 | 256 | 32.803100 | PASS |
| 64 | 18 | 28 | 18 | 256 | 32.803100 | PASS |
| 64 | 14 | 36 | 14 | 256 | 32.803100 | PASS |
| 28 | 14 | 0 | 14 | 256 | 14.365100 | PASS |
| 65 | 22 | 21 | 22 | 256 | 33.315100 | PASS |

Four separate negative simulations rejected (L,beta)=(64,1), (64,65), (1,0),
and (64,38), all at **0 ns**. Logs intentionally contain `[CONFIG_ERROR]` failure
assertions. They are classified as expected rejections, not normal successful
bench completion. The corrected negative runner was verified separately and
closes XSim immediately after the time-zero assertion; it never resumes a
rejected simulation. The status CSV combines those rechecked negative cases
with the already passing positive cases; all entries are backed by actual logs.

## Integration WTM experiments

Every row represents **1024 complete patterns / 65536 enabled shifts**, with
regular pause/resume tests and complete-chain comparison after every enabled
edge. All six beta configurations were actually compiled, elaborated and run.
Mode transitions, scan-input-stage feedback, every scan FF, pattern boundaries,
LFSR state order, reset and known initialized values passed. Pattern-domain WTM
matched chronological WTM exactly at every complete pattern.

| Beta | Alpha=Gamma | Estimated WTM (%) | Measured WTM (%) | Error (pp) | Serial toggle (%) | Actual FF switching (%) | Duration (us) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 32 | 7.142857 | 7.141442 | 0.001415 | 7.138170 | 7.135701 | 131.457100 |
| 8 | 28 | 12.500000 | 12.155060 | 0.344942 | 12.170600 | 12.165000 | 131.457100 |
| 16 | 24 | 17.857140 | 17.347130 | 0.510012 | 17.438010 | 17.429380 | 131.457100 |
| 20 | 22 | 20.535710 | 20.095640 | 0.440077 | 20.202940 | 20.193310 | 131.457100 |
| 28 | 18 | 25.892860 | 25.447810 | 0.445047 | 25.638210 | 25.623320 | 131.457100 |
| 36 | 14 | 31.250000 | 30.728850 | 0.521146 | 30.978870 | 30.961680 | 131.457100 |

All measured-versus-estimated errors are below the declared **2 percentage-point**
limit. Functional reference comparisons and independent WTM equality use exact
assertions, not that tolerance. The analytical estimate assumes stationary n=3
and n=1 rates in each region. Actual filter history at the switching boundaries
introduces finite-region transients, so repeating short 64-bit patterns does not
make this approximation exact. There is no assertion that these values establish
physical power or capture/combinational activity.

Serial counting excludes the very first input bit and includes all subsequent
pattern/mode boundaries: **65535 adjacent-pair opportunities**. WTM includes the
first transition against the existing first-stage value for each complete pattern,
with chronological weights L,L-1,...,1 and denominator L(L+1)/2. Actual FF activity
counts all FF changes over enabled shifts, including initialized chain contents.
These three metrics have different meanings and are reported separately.

The beta sweep supplies configurations, not requested targets, so `TargetWTM=NA`
in its CSV. Independently, the offline optimizer's 20% example selects beta=20
with estimated WTM=23/112 (20.535714286%). The matching integration run measured
20.09564%: **0.09564 pp from requested 20%**, and **0.440077 pp from the analytical
estimate**. Target quantization error and measured-estimate error are distinct.
No on-chip target computation is implemented.

## Reproduce

From the repository root:

```powershell
python ./lbist/scripts/test_basic_wtm_optimizer.py
python ./lbist/scripts/basic_wtm_optimizer.py --chain-length 64 --target-percent 20
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_basic.tcl
```

Individual project-mode Tcl runners are `run_basic_controller.tcl` and
`run_basic_integration.tcl`. Use a fresh Vivado GUI session and set
`::env(BASIC_GUI)=1` before sourcing a runner. Full interface, waveform timing,
legal generics, ordering, paper interpretation and GUI commands are in
[docs/basic_control.md](../../../docs/basic_control.md).

The Basic project is isolated under `work/project`; its simulation results never
write into Phase 1 or Phase 2 directories. Logs and CSVs are actual outputs; the
working project and compiled simulator data are ignored by Git. Summary CSVs are
replaced with the selected invocation's results; use the full runner for all rows.
The full runner returns a nonzero batch exit for unexpected failures, absent
completion markers, fatal simulator errors or timeouts.

Normal tests finish without failure assertions. Every watchdog and Tcl run is
bounded by **5 ms**, below the hard 100-ms maximum. All positive unit runs finish
below 34 us; every integration run finishes at 131.4571 us. Negative cases stop at
0 ns. Final normal-suite and negative-recheck Vivado batch processes exited 0.

## Artifacts and scope

- [Controller summary](reports/basic_controller_summary.csv)
- [Three-metric WTM summary](reports/basic_wtm_summary.csv)
- [All-case verification summary](reports/basic_verification_summary.csv)
- [Offline optimizer example](reports/optimizer_20percent.json)
- [New verified source hashes](reports/source_sha256.csv)
- [Pre-existing-file integrity](reports/protected_file_integrity.csv)
- [Actual simulation/build logs](logs/)

All **402 pre-existing repository files** outside generated work directories
match their before-implementation SHA-256 hashes, including cMIPS, Phase 2 RTL,
testbenches, scripts, documentation and committed verification results.

Added one RTL controller, two testbenches, an exact rational offline optimizer and
its six-test suite, Basic-only Tcl automation, documentation and measured results.
No prior tracked file was modified. No unexpected verification failures remain.
Runtime beta programming, unsupported short low regions, synthesis/area evaluation,
Swap/Moving controllers, MISR and processor scan integration remain outside scope.
