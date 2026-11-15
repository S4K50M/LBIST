# Phase 3 comparative verification

## Common experiment setup

tb_phase3_comparison runs five independently scored engines simultaneously:
direct LFSR, constant PLPF n=3, Basic, Swap and Moving. Each uses the unchanged
polynomial x^16+x^15+x^13+x^4+1, seed AAAA, same 2-ns clock, identical initialization,
pauses and enabled-shift counts. Four chains receive phases 0,257,514,771:
phase-distinct correlated streams, not statistically independent RNGs.

The reference reuses phase2_tb_pkg for the polynomial sequence and behavioral
filtering, but derives scheduling, positions and FF contents independently of
DUT outputs. Sequence indices wrap at the verified 65535-bit period, supporting
longer chains without changing Phase 2.

There are 15 comparison simulations: lengths 64,128,200 and targets 10,15,20,25,30%.
Each verifies 1024 patterns for all five approaches. Six dedicated Swap/Moving
integrations add measured records. There is no capture phase or CUT fault model.

## Exact offline schedule selection

phase3_wtm_optimizer.py enumerates legal integer beta values and averages every
regional weighted sum of Eq. 3 over the full control cycle and all chains using
Fraction arithmetic. Physical alpha/beta/gamma order reverses chronologically;
weights L,L-1,...,1 give the same estimate. An unweighted mixture is not the
primary reference. Asymmetric per-pattern examples are explicitly tested.

Basic preserves symmetry/parity; Swap requires even L and beta<=L/2-14; Moving
evaluates all L-beta-27 positions with both low regions >=14. The optimizer
reports full timing cycles, feasible bounds, validity, expected exposure and
theoretical target-quantization error.

~~~powershell
python ./lbist/scripts/phase3_wtm_optimizer.py --approach moving --chain-length 64 --chains 4 --target-percent 20
python ./lbist/scripts/phase3_wtm_optimizer.py --approach swap --chain-length 64 --chains 4 --target-percent 25 --nearest
~~~

Infeasible targets are rejected unless --nearest is explicit. The sweep includes
those nearest-feasible points with clear labels:

| L | Maximum Swap estimated WTM | Targets requiring nearest-feasible |
| ---: | ---: | --- |
| 64 | 19.196429% | 20%, 25%, 30% |
| 128 | 23.883929% | 25%, 30% |
| 200 | 25.571429% | 30% |

Graphs mark them with a black x. They are not equivalent matched-target operating
points. Requested targets are common; legal schedules and quantization differ.

## Measured definitions

1. Serial transitions: consecutive emitted input bits, first bit per chain
   excluded; later mode/pattern boundaries included.
2. Normalized scan-in WTM: weights L down to 1, including every pattern's initial
   first-stage value. A loaded-pattern calculation must match exactly per chain.
3. Actual FF switching: all scan-register changes / enabled-shift FF opportunities.
   Reset initialization is excluded; shifts from zero contents count.
4. Physical exposure: observed n=1 selection counts / complete patterns; finite
   counts must exactly match an independent schedule reference.
5. Diversity: actual distinct patterns per chain and actual distinct four-chain
   tuples, compared with all earlier observed patterns.

CSV retains integer numerators/denominators. A fixed 2 percentage-point bound
applies only to measured versus estimated stationary WTM; functional checks and
WTM identities are exact. Mode boundaries and partial control-cycle remainders
can bias the approximation. Both full-cycle and finite-schedule estimates appear.

TargetQuantizationErrorPP, TargetErrorPP and SimulationErrorPP distinguish
theoretical quantization, measured-versus-requested and measured-versus-estimated
errors. Direct/constant references have target NA. No metric establishes
processor power or stuck-at/transition fault coverage.

## Execution

~~~powershell
python ./lbist/scripts/test_phase3_wtm_optimizer.py
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase3.tcl
python ./lbist/scripts/test_phase3_waveforms.py
~~~

run_all_phase3.tcl executes all cases, collects real-log CSVs, makes matplotlib
figures and focused real-data SVGs, then checks native WDB/WCFG and VCD behavior.
Isolated projects live under Results/Phase3/Comparison/work. Old Phase 2/Basic
report writers are never called; regression outputs go into new Comparison logs.

PHASE3_PYTHON may override the Python executable. Matplotlib/numpy are used for
figures. In a fresh GUI, set ::env(PHASE3_GUI)=1 before sourcing a runner.
Vivado is 2025.1.1; simulation-only part is xc7a35tcpg236-1.

Cases include new controller/integration tests, 15 comparison tops, and five
Phase 2 plus 18 Basic regressions. Expected negatives require CONFIG_ERROR at
time zero without normal completion; successful normal tests do not terminate
through failure assertions. Every watchdog/Tcl bound is <=20 ms, below 100 ms.

Actual outcomes are in Results/Phase3/Comparison. The collector's --require-all
option rejects completion if any case is absent/failed; partial collections mark
unexecuted cases NOT RUN. See [waveforms.md](waveforms.md) for generation/viewing.
Old captures are preserved; focused Basic images are additional files.
WDB/VCD are local Git-ignored data, not claimed as committed histories.

No area savings, physical power reduction or processor fault coverage is claimed.
Positional distribution and diversity are reported even when a result does not
favor the more elaborate controller.

## Observed default sweep

All 69 planned cases passed in Vivado 2025.1.1: 55 normal completions and 14
expected configuration rejections. This includes five Phase 2 and 18 Basic
regressions. All positive cases completed between 8.1991 and 410.8011 us.
The 15 five-approach comparisons yielded 75 measured records; six dedicated
integrations yielded six additional records. No test exceeded its watchdog.

At the requested 20% target for L=64, measured normalized scan-in WTM was
20.123056% Basic (beta20), 18.890193% Swap (beta18, nearest feasible), and
19.501214% Moving (beta19). The maximum measured/estimated discrepancy across
the comparison sweep was 0.462038 percentage points. Absolute requested-target
errors, which include infeasible Swap requests, are reported separately.

The beta16 integration captures demonstrate Swap physical windows 16..31 and
32..47 exchanging by pattern/chain parity; Moving visits 21 legal placements,
reaching exactly 36 physical positions. These observations match both the
independent VHDL model and the captured-transition checker.

See the [result report](../Results/Phase3/Comparison/README.md) for actual case
statuses, durations, metrics, charts, waveform provenance and reproduction.
