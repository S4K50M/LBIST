# Phase 3: Moving Control

## Figure 8 and length conservation

The original published Figure 8 was inspected directly (printed page 596 of the
paper in Downloads). It labels alpha=L-i-j, beta=i, gamma=j and increments gamma
between patterns while decrementing alpha. The surrounding prose instead has
L/2-i-j, which cannot satisfy alpha+beta+gamma=L. The RTL follows the figure.

Kato et al., DOI 10.1109/TETC.2017.2767070:
[author manuscript record](https://kyutech.repo.nii.ac.jp/records/6935).

Physical order is IN -> alpha -> beta -> gamma -> OUT, with physical index 0 at
IN. Chronological application reverses this order. Growing gamma moves the
unfiltered region toward IN (lower physical indices) while its chronological
start moves later.

## Explicit legal range and wrap

~~~text
period = L - beta - 27
position = (completed_patterns + INITIAL_POSITION) mod period
gamma = 14 + position
alpha = L - beta - gamma
~~~

After gamma reaches L-beta-14, the next complete pattern returns gamma to 14.
Every intermediate position is visited by increments of one. Figure 8 shows a
loop without fully specifying endpoints; these inclusive endpoints are the
documented implementation policy under the 14-bit minimum constraint.

L=64, beta=16 gives 21 states, (34,16,14) through (14,16,34), then wraps.
All chains share the moving placement but receive distinct PRNG phases and use
separate feedback. Cross-chain placement staggering is not invented as a paper
feature.

Legal domain: 28<=L<=4096, beta<=L-28, 1<=NUM_CHAINS<=16, and
0<=INITIAL_POSITION<period. Odd lengths are supported without truncation.
Subtractions are guarded for invalid generics. Beta=0 has no n=1 exposure despite
the debug movement counter cycling. Beta=L-28 has period 1 and cannot move beyond
its single legal placement. L=1 and unsupported configurations are rejected.

## Interface and timing

Defaults: L=64, beta=16, NUM_CHAINS=4, INITIAL_POSITION=0. Reset is synchronous,
active-high and overrides scan enable. Outputs:

- mode_select(2*c+1 downto 2*c): 00=n=3, 11=n=1.
- shift_count: pre-edge chronological position.
- pattern_done: registered one-clock completion pulse.
- pattern_index: completed patterns modulo 2^32.
- moving_position: constrained movement-range position.
- alpha_debug/gamma_debug: 16-bit physical region lengths per chain.

State advances only on enabled shifts. Movement advances only when a complete
pattern ends. Pauses preserve positions, regions and PRNG state; completion clears
on the next disabled clock. Rollover/movement updates prepare the next pattern
without inserting or skipping a shift. Movement is tracked independently of the
32-bit debug index, so debug overflow does not restart the moving schedule.

## Reachable physical exposure

For beta>0, a complete legal movement cycle can reach only physical FFs
14..L-15. At L=64 this is **36 of 64 positions**. The 14 cells at each end remain
in required low-toggle regions. The testbench proves all reachable positions
are visited and compares finite-run exposure against an independent schedule.

E[k] counts complete patterns where physical FF k receives n=1 data, divided by
patterns. It is neither toggle probability nor fault coverage. Counts can differ
near endpoints; incomplete schedule cycles also change finite-run exposure.

## Verification

tb_moving_controller checks MC01..MC15: initial region, exact motion, endpoints,
wrap, completion, pause/reset, physical order, cycle coverage, odd lengths,
nonzero initial offset and invalid generics. 256 positive patterns cover the
full movement cycles of tested configurations.

tb_moving_integration verifies 1024 complete four-chain patterns at L=64/128/200
against the unchanged independent sequence and software-style scan-register
reference. The same engine is reused in matched-target comparisons.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_moving_controller.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_moving_integration.tcl
~~~

Actual outcomes and durations are in Results/Phase3/Moving/reports.
moving_beta16_progression.svg comes from actual captured pre-edge modes.
moving_beta16_moving_wrap.svg shows the observed wrap event. Full WDBs are local
generated files. No capture, MISR, processor scan conversion, area, physical
power or fault coverage is inferred from these stimulus experiments.
