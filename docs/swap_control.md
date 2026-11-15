# Phase 3: Swap Control

## Paper interpretation and ordering

Kato et al., DOI 10.1109/TETC.2017.2767070, Figure 7 and its accompanying text,
are the source. The published PDF in Downloads was inspected directly (printed
page 595). [Author manuscript record](https://kyutech.repo.nii.ac.jp/records/6935).

Figures 6--8 draw physical storage from IN to OUT: **alpha / beta / gamma**.
Physical FF index 0 is the scan-input stage. Earlier serial bits move toward
scan-out, so chronological order is **gamma / beta / alpha**. Head/tail wording
varies between paragraphs; explicit IN/OUT and chronological definitions avoid
ambiguity.

| Zero-based (pattern+chain) mod 2 | Physical alpha | beta | Physical gamma |
| --- | ---: | ---: | ---: |
| 0 | L/2-beta | beta | L/2 |
| 1 | L/2 | beta | L/2-beta |

(p,c)=(0,0) corresponds to the paper's odd vector / odd chain. The high mode is
selected at chronological positions gamma..gamma+beta-1. With L=64, beta=16,
chain 0 first stimulates physical FFs 16..31 unfiltered; chain 1 stimulates
32..47. The next pattern reverses those placements. This is positional swapping,
not simply alternating filter types without moving the middle region.

## RTL interface

swap_controller.vhd uses synchronous active-high reset and active-high scan
enable. Defaults: L=64, beta=16, NUM_CHAINS=4. Legal domain: even 28<=L<=4096,
0<=beta<=L/2-14, and 1<=NUM_CHAINS<=16. Odd lengths are explicitly rejected.
Both low regions stay >=14 bits. Beta=0 selects n=3 continuously while parity
still advances.

- mode_select(2*c+1 downto 2*c) is chain c: 00=n=3, 11=n=1.
- shift_count is the pre-edge position, 0..L-1.
- pattern_done asserts after the Lth enabled edge and clears on the next clock,
  including a disabled clock.
- pattern_index is a 32-bit debug counter modulo 2^32.
- alpha_debug(16*c+15 downto 16*c) and gamma_debug pack physical region lengths.

Only enabled shifts advance state. Rollover and pattern advance occur on the same
edge without an idle shift. Reset overrides enable and discards incomplete work.
Mode decoding uses the pre-edge position/index; a mode displayed after an edge
prepares the following shift. There are no gated clocks or combinational latches.

## Multi-chain source and feedback

multi_chain_phase_shifter.vhd derives exact sequence phases 0,257,514,771 using
constant GF(2) masks against the unchanged LFSR state. These are distinct,
correlated phases of ONE 16-bit LFSR, not statistically independent generators.
Next/next-next bits are combinational. The independent sequence reference checks
all phases, including across sequence-period rollover.

Every chain uses its own actual input-stage FF Q for PLPF feedback. Storage for
chain c occupies chain_flat((c+1)*L-1 downto c*L), with input-stage bit c*L.
The original LFSR, filters, phase shifter and Basic controller remain unchanged.

## Verification and reproduction

tb_swap_controller checks SC01..SC15 with an independent position/pattern model:
reset, region lengths, boundaries, completion, rollover, chain/pattern parity,
pauses, mid-pattern reset and length variants. Positive units use 256 patterns.
Invalid configurations are separate expected-rejection cases at time zero.

tb_swap_integration checks 1024 complete patterns at L=64/128/200 with four
chains: every FF, sequence/lookahead bit, feedback, pause and pattern boundary.
Chronological and loaded-pattern WTM must agree exactly. Actual distinct pattern
tuples and physical n=1 exposure are counted; neither is fault coverage.

~~~powershell
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_swap_controller.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source ./lbist/scripts/run_swap_integration.tcl
~~~

Actual status/durations are in Results/Phase3/Swap/reports. Captured boundaries,
pauses, rollover and per-chain variation appear in swap_beta16_*.svg under its
waveforms folder. Full WDB/VCD data are generated locally and Git-ignored.

This is functional counter/range-decoder RTL, not a gate-level copy or an area
equivalence claim. No processor scan insertion, capture, MISR, physical power,
timing result or fault coverage is claimed.
