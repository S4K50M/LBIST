# Phase 2: standalone scan-pattern generator

Four synthesizable VHDL-2002 modules are isolated from the cMIPS design. No scan
conversion, controller, MISR, capture logic, or processor integration is included.
The scan chains in `tb/` are verification models only.

## Interfaces and timing

`lfsr_16` has an asynchronous **active-high** `rst`, rising-edge `clk`, and
active-high `enable`. `SEED` defaults to `x"AAAA"`. A zero or nonbinary seed falls
back to AAAA; an enabled accidental zero state also recovers to that seed.
Reset is required before use. Disabling holds the entire state.

State bit `i` contains chronological sequence bit `T[j+i]`; `random_bit=state(0)`.
The register shifts right toward bit 0. Over GF(2), the polynomial
`x^16+x^15+x^13+x^4+1` gives

```
T[j+16] = T[j+15] xor T[j+13] xor T[j+4] xor T[j]
next_state = (state(15) xor state(13) xor state(4) xor state(0)) & state(15 downto 1)
```

The independent testbench sequence is initialized with the seed's 16 chronological
bits and uses `T[k]=T[k-1] xor T[k-3] xor T[k-12] xor T[k-16]`. It checks every
state in the 65535-state period, uniqueness, nonzero state and bit balance.

`phase_shifter` exposes `state(0)`, `state(1)`, `state(2)`. These are exact current,
next, and next-next outputs under this state convention. Wires suffice; no extra
clock or XOR network is needed for these particular phases. Other chain offsets
can later use linear lookahead equations.

Both filters use the following two-bit mode interface:

| Mode | n | Function when past=0 | Function when past=1 |
| --- | --- | --- | --- |
| 11 | 1 | current | current |
| 01 | 2 | current AND future1 | current OR future1 |
| 00 | 3 | current AND future1 AND future2 | current OR future1 OR future2 |
| 10 / nonbinary | invalid | past | past |

`mode_valid` deasserts for invalid modes. Holding the input-stage value avoids an
input transition but **does not disable the rest of the scan chain or LFSR**.
For a valid filtered mode, unknown feedback propagates X rather than hiding an
uninitialized scan stage. `plpf_dynamic` exposes `active_mode` without registering
it and shares the first two AND/OR reductions. It is functionally equivalent to
the specified optimized filters; no gate-count or physical equivalence to the
paper's Figure 5(b) is claimed. Change controller mode on the inactive clock edge,
or satisfy setup/hold; combinational mode changes are not glitch-free storage.

Wire `past_bit` to **Q of the first scan-input FF**. On a rising enabled shift,
that FF captures `scan_in`, the rest shift toward scan-out, and the LFSR advances
once. Disable both scan shifting and LFSR advancement together. No additional
shift cycle is consumed when mode changes.

## Verification and metrics

Five benches use deterministic references, `[PASS]`, `[FAIL]`, and `[TB_COMPLETE]`
markers. A 2 ms watchdog is canceled by `test_done`; stopped clocks and canceled
watchdogs allow normal quiescent completion in VHDL-2002 without `std.env.finish`
or a deliberate failure assertion. No test may exceed 2 ms (well below 100 ms).

- LFSR: full period, custom seed 0001, zero-seed fallback, hold/resume, reset.
- Phase shifter: 4096 sequence states, reset/disable, all 65536 combinational states.
- Optimized PLPF: all 16 current/future/history combinations for every mode,
  invalid/nonbinary modes, unknown history, actual 64-bit scan-stage feedback,
  and 65535 output bits per mode. Rate tolerance: **0.5 percentage points**.
- Dynamic PLPF: 4096 continuously enabled shifts, repeated mode changes, invalid
  modes, inactive-time alignment and no LFSR reset or extra cycle at transitions.
- Integration: configurable 2..1024-stage chain (default 64), three fixed-mode
  epochs and one changing-mode epoch, complete-chain scoreboarding, full patterns,
  initialization, bit order and pause/resume. Fixed epochs use approximately
  16384 bits each; rate tolerance: **1 percentage point**.

Rate = serial output transitions / eligible adjacent output-bit pairs. The first
bit of each measurement epoch is excluded from serial transition counting, with
`bits-1` opportunities. Mode-switch boundaries **inside** a dynamic epoch count;
there is no single stationary theoretical rate for that epoch. Tolerances cover
finite deterministic sampling, not exact equality or a claim of randomness.
`Patterns` in the requested toggle CSV means **sample bits**, not full scan loads.
`CompletePatterns` in the separate WTM CSV counts full chain loads.

WTM is recorded separately from serial toggling and actual chain activity. For
chronological input bits `b[0..L-1]` and the initial input-stage value `q0`:

```
WTMin = [ L*(b[0] xor q0)
          + sum(k=1..L-1, (L-k)*(b[k] xor b[k-1])) ] / [L*(L+1)/2]
```

This weights early scan-in transitions by their propagation distance. It is the
measured-transition form of the paper's normalized scan-in weighting (Section IV,
Eq. 3); the first transition includes the existing scan-stage value. There is no
capture response in this standalone test, so each pattern uses the preceding
pattern's input-stage state. `ActualChainToggleFraction` instead counts all FF
changes across all enabled shifts, including initialized chain contents. Neither
metric is an estimate of capture/combinational power or achieved fault coverage.

Paper: Kato et al., [author manuscript and bibliographic record](https://kyutech.repo.nii.ac.jp/records/6935),
DOI 10.1109/TETC.2017.2767070. The chosen state ordering, seed recovery, invalid-mode
policy, and controller interface are explicit implementation decisions. Automatic
power-target scheduling (Basic/Swap/Moving Control) is outside this phase.

## Run with Vivado 2025.1.1

From the repository root in PowerShell (adjust installation path if necessary):

```powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_all_phase2.tcl
```

A fresh, separate `Results/Phase2/work/project` project is created. Only Phase 2
sources enter that project; the existing processor project and baseline remain
untouched. The project part is `xc7a35tcpg236-1` (simulation only). Other installed
parts can be substituted in `common.tcl` if needed.

For one test, substitute `run_lfsr.tcl`, `run_phase_shifter.tcl`,
`run_plpf_optimized.tcl`, `run_plpf_dynamic.tcl`, or `run_phase2_integration.tcl`.
Each script is a **Vivado project-mode** script, not an XSim Tcl script. They
compile/elaborate each selected simulation top, run bounded increments, read
`test_done`, and require both a completion marker and absence of failure markers.
A caught simulator error or timeout causes a nonzero batch exit. Reports are
replaced on each invocation and cover that invocation's selected tests.

For GUI use, open a **fresh Vivado session**, then in its Tcl console:

```tcl
set ::env(PHASE2_GUI) 1
source {C:/Users/Saksham Setia/OneDrive/Desktop/VLSI/cmips/lbist/scripts/run_all_phase2.tcl}
```

The environment flag prevents a failed GUI run from exiting the application.
For manual waveform inspection, open the generated Phase 2 project, choose the
simulation top in Simulation Sources, and launch behavioral simulation. The
optional `xsim_control.tcl` is XSim-only (set `TOP` before sourcing it).

Actual logs, durations, rates, and verification status are in
[Results/Phase2](../Results/Phase2/README.md). Test success is never inferred solely
from the return of `run`.
