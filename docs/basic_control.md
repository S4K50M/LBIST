# Phase 3A: Basic PLPF controller

## Scope and paper interpretation

This phase adds a standalone controller and reuses the Phase 2 LFSR, phase shifter,
and dynamic filter unchanged. No processor scan insertion, capture engine, MISR,
Swap Control, or Moving Control is implemented.

Kato et al., Section IV Basic Control and Figures 6/9, specify symmetric low-toggle
regions around a fixed unfiltered middle. [Author manuscript and record](https://kyutech.repo.nii.ac.jp/records/6935),
DOI 10.1109/TETC.2017.2767070. The implemented counter plus combinational range
decoder follows the requested functional schedule. It is not a gate-level copy
of Figure 9's boundary decoding and T-FF circuit. No equivalent area is claimed.

## Controller API

`lbist/rtl/basic_controller.vhd` has generics `CHAIN_LENGTH` (positive, default 64)
and `BETA` (natural, default 20). Both low lengths are `(CHAIN_LENGTH-BETA)/2`;
the default is **22 / 20 / 22**. All supported configurations are paper-compliant:
`L>=28`, `BETA<=L`, even `L-BETA`, and both low lengths >=14. Invalid configurations,
including L=1, are rejected by named `[CONFIG_ERROR]` assertions; subtraction is
guarded before constant evaluation. No exploratory short-region mode is provided.
Odd L is supported if beta has the same parity (e.g. 65/21 gives 22/21/22).

Inputs are `clk`, synchronous active-high `rst`, and active-high `scan_enable`.
Reset only acts on a rising edge and overrides enable. It sets position zero and
clears `pattern_done`. Reset may discard an incomplete pattern. Drive reset across
a clock edge before enabling scan. The reused LFSR has an asynchronous reset;
the integration bench holds the common reset through an edge to align all state.

Outputs:

- `shift_count`: current position, constrained internally to 0..L-1.
- `mode_select`: combinational mode for the **next rising enabled shift**, using
  the pre-edge position. Positions 0..alpha-1 use 00 (n=3), alpha..alpha+beta-1
  use 11 (n=1), and the rest use 00. Beta=0 stays in mode 00 continuously.
- `pattern_done`: registered pulse asserted just after the Lth enabled edge.
  It clears at the next clock edge, even if scanning pauses. It is a completion
  strobe, not a level held until another enabled shift.

Counter rollover and completion occur on the same last edge. No idle edge is
inserted between patterns. While paused, counter and mode hold; completion clears.
There are no derived clocks or combinational feedback paths.

## Chronological and physical bit order

First-applied bits propagate toward `chain(L-1)` (scan-out). Latest-applied bits
remain toward `chain(0)` (scan-in). Thus the first chronological region becomes
the physical far-end region after loading; it must not be confused with physical
head/tail terminology. Since alpha=gamma, reversal leaves the Basic schedule
symmetric. The testbench checks actual chain contents against a chronological
reference and checks WTM both temporally and from the loaded pattern.

`past_bit` is always wired to actual `chain(0)`. Controller, LFSR, and modeled scan
FFs share the clock and enable. Mode changes after a shift describe the following
shift, not the just-captured bit. This is why no extra mode register is used.

## Offline WTM configuration

```powershell
python ./lbist/scripts/basic_wtm_optimizer.py --chain-length 64 --target-percent 20
python ./lbist/scripts/basic_wtm_optimizer.py --chain-length 64 --target-fraction 1/5
```

The optimizer enumerates legal integer beta values and minimizes absolute error
using exact `fractions.Fraction` arithmetic. The primary reference is the three
weighted region sums of Eq. 3; the simplified expression `1/14+(1/2-1/14)*beta/L`
is an exact cross-check. Ties select smaller beta. The feasible 64-stage range is
1/14 through 5/16 (7.142857%..31.25%). Out-of-range targets fail unless `--nearest`
is explicitly supplied. Percent and fraction CLI options are mutually exclusive.
The output reports exact rational values, feasible endpoints, classification and
out-of-range status. This is an **offline utility**, not an on-chip optimizer.

For target 20%, the calculated optimum is alpha=gamma=22, beta=20; estimated WTM
is 23/112 (20.535714286%), with target quantization error 0.535714286 percentage
points. Optimizing theoretical WTM does not guarantee measured WTM equals target.

## Verification

`tb_basic_controller` uses an independent reference position, not the DUT count,
to check BC01..BC12. It verifies 256 complete patterns per legal run, exact region
lengths, both switch boundaries, reset timing, mid-pattern reset, consecutive
patterns, pauses at boundaries, pulse clearing while disabled and no extra cycles.
Eight positive configurations and four negative generic combinations are run.

`tb_basic_integration` uses the unchanged Phase 2 independent sequence and filter
reference package. For each beta in 0,8,16,20,28,36 it checks **1024 complete 64-bit
patterns** (65536 enabled shifts). Every shift checks mode, LFSR state, scan-in,
all scan FFs, pulse timing and rollover; regular three-cycle pauses check joint
state hold. It asserts known initialized scan bits and independently cross-checks
WTM at every pattern boundary.

Three metrics are kept separate:

1. Serial transitions / adjacent-bit opportunities. The initial bit is excluded;
   all later pattern/mode boundaries count. With 65536 bits there are 65535 pairs.
2. WTM: weight L on the first transition against initial `chain(0)`, then L-1 down
   to 1. Normalize by complete patterns times L(L+1)/2. Pattern-domain weighting
   must agree exactly with the chronological sum. Eq. 3 uses ascending physical
   position weights; reversing to chronological order gives the weights used here.
3. Actual FF changes / enabled shifts / chain length. Initial chain contents count.

The fixed **2 percentage-point WTM limit** covers finite deterministic sampling
and the stationary r3/r1 approximation at two mode boundaries. Region length is
only 64 and boundary transients do not vanish simply by repeating patterns. All
functional scoreboards and the two WTM calculations must still match exactly;
the tolerance applies only to measured versus estimated WTM. Results explicitly
quantify that discrepancy rather than treating the theoretical estimate as exact.

## Run in Vivado 2025.1.1

From the repository root in PowerShell:

```powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_basic.tcl
```

Change the executable path if Vivado is installed elsewhere. Separate runners
`run_basic_controller.tcl` and `run_basic_integration.tcl` select subsets. In a
**fresh** Vivado GUI Tcl console:

```tcl
set ::env(BASIC_GUI) 1
source {C:/Users/Saksham Setia/OneDrive/Desktop/VLSI/cmips/lbist/scripts/run_all_basic.tcl}
```

The GUI flag prevents failure handling from exiting the application. These are
Vivado project-mode scripts, not XSim scripts. An isolated project is created in
`Results/Phase3/Basic/work/project`; Phase 2's project and reports are not opened
or overwritten. Each run compiles/elaborates the top with explicit generics and
runs bounded 1-us increments until `test_done`. Watchdogs and Tcl limits are 5 ms;
normal completion stops clocks and cancels the watchdog without assertion failure.

Expected negative runs pass only if their logs contain `[CONFIG_ERROR]` and no
normal completion marker. A generic compile error cannot masquerade as expected
rejection. Normal runs require a completion marker and no failure/fatal/error.
Reports and build/simulation logs are generated directly from each actual run.
A failed case gives nonzero batch status. Summary CSVs cover the selected subset
and are replaced only within the new Basic results directory.

Offline verification: `python ./lbist/scripts/test_basic_wtm_optimizer.py`.
Measured results, durations and integrity evidence are in
[Results/Phase3/Basic](../Results/Phase3/Basic/README.md).
