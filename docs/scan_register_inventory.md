# Pipeline scan-register inventory

The [CSV inventory](scan_register_inventory.csv) covers every output assigned in
the four rising-edge processes in
[pipestages.vhd](../cMIPS/vhdl/pipestages.vhd). Register names are the module's
output port names. It includes data, addresses, instruction fields, and controls.
It does not cover other sequential storage in the processor.

| Module | Stage boundary | Registers | Logic/vector bits | Conditional encoded bits | Planned total bits | Registers with explicit reset | Bits with explicit reset |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| reg_IF_RF | Instruction Fetch -> Register Fetch | 2 | 64 | 0 | 64 | 2 | 64 |
| reg_RF_EX | Register Fetch -> Execute | 18 | 165 | 7 | 172 | 3 | 3 |
| reg_EX_MM | Execute -> Memory | 17 | 246 | 1 | 247 | 3 | 3 |
| reg_MM_WB | Memory -> Writeback | 12 | 237 | 0 | 237 | 1 | 1 |
| **Total** | | **49** | **712** | **8** | **720** | **9** | **71** |

## Clock, load, and reset behavior

All four modules load on the rising edge of `clk` when `rst='1'` and `ld='0'`.
They hold their values when `ld='1'`.

The reset branch is asynchronous and active-low, but only these registers have
an explicit reset assignment:

- `reg_IF_RF.PCincd_q` and `reg_IF_RF.RF_instr`: `x"00000000"`.
- `reg_RF_EX.EX_wreg`, `EX_wrmem`, and `EX_aVal`: `'1'`.
- `reg_EX_MM.MM_wreg`, `MM_wrmem`, and `MM_aVal`: `'1'`.
- `reg_MM_WB.WB_wreg`: `'1'`.

The other **40 registers / 649 planned bits** are unassigned in the reset branch.
They retain a previously loaded value while `rst='0'`, and reset does not establish
a known initial value for them. Their functional load is still inhibited during
reset. The CSV records this separately from an asynchronous reset assignment.
VHDL default values for Boolean and enumeration signals are not explicit hardware
reset values.

## Types and scan decisions

The `reg2`, `reg3`, `reg4`, `reg5`, and `reg32` subtypes resolve to
`std_logic_vector` ranges in
[packageWires.vhd](../cMIPS/vhdl/packageWires.vhd). These vectors and the scalar
`std_logic` registers account for **46 registers / 712 bits** that are direct
candidates for bit-based scan storage. Preserve their functional load and reset
behavior when adding scan selection.

The remaining three registers require explicit treatment before a raw vector scan
chain can include them:

| Register | RTL type | Planned width | Encoding decision |
| --- | --- | ---: | --- |
| reg_RF_EX.EX_oper | t_alu_fun enumeration | 6 | Use the existing `ENUM_ENCODING` mapping: 43 literals, declaration-order codes 0 through 42 (`000000` through `101010`). Use explicit encoding/decoding at the scan boundary, or verify and use the synthesis tool's actual storage mapping. For an explicit scan wrapper, decode unused codes 43 through 63 as `invalid_op` (code 42). |
| reg_RF_EX.EX_is_load | boolean | 1 | Convert explicitly using `false=0`, `true=1` at the scan-storage boundary. |
| reg_EX_MM.MM_is_load | boolean | 1 | Convert explicitly using `false=0`, `true=1` at the scan-storage boundary. |

These **8 bits are conditional**. Their CSV widths describe the declared enum
encoding and proposed Boolean encodings. Keep these three registers excluded from
a raw vector chain until conversions are implemented or their synthesized storage
mapping is verified. No encoding wrapper or RTL change is implemented by this
inventory.

The **720-bit total is an RTL planning count**, not a measured synthesized
scan-chain length. Synthesis may change storage through optimization or encoding.
Each CSV row includes its clocked-assignment location, reset location when
applicable, and type source so the inventory can be checked against the RTL.
