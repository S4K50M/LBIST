library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
-- Distinct phases of ONE 16-bit LFSR, not statistically independent RNGs.
-- Chain c receives T[j+c*PHASE_STEP], and the next two exact future bits.
entity multi_chain_phase_shifter is
  generic (NUM_CHAINS : positive := 4; PHASE_STEP : positive := 257);
  port (state_in : in std_logic_vector(15 downto 0);
        current_bits, future1_bits, future2_bits : out std_logic_vector(NUM_CHAINS-1 downto 0));
end entity;
architecture rtl of multi_chain_phase_shifter is
  subtype mask_t is std_logic_vector(15 downto 0);
  function mask_for(offset : natural) return mask_t is
    type basis_array is array(natural range <>) of mask_t;
    variable basis : basis_array(0 to offset+16) := (others=>(others=>'0'));
  begin
    for i in 0 to 15 loop basis(i)(i):='1'; end loop;
    for i in 16 to offset loop
      basis(i):=basis(i-1) xor basis(i-3) xor basis(i-12) xor basis(i-16);
    end loop;
    return basis(offset);
  end;
  function parity(v : mask_t) return std_logic is
    variable bit_value : std_logic := '0';
  begin
    for i in v'range loop bit_value:=bit_value xor v(i); end loop;
    return bit_value;
  end;
begin
  assert NUM_CHAINS<=16 and PHASE_STEP<=4095 report "[CONFIG_ERROR] phase-shifter bounds exceeded" severity failure;
  assert (NUM_CHAINS-1)*PHASE_STEP+2<65535 report "[CONFIG_ERROR] duplicate/unsupported phase offsets" severity failure;
  phases: for c in 0 to NUM_CHAINS-1 generate
    constant M0 : mask_t := mask_for(c*PHASE_STEP);
    constant M1 : mask_t := mask_for(c*PHASE_STEP+1);
    constant M2 : mask_t := mask_for(c*PHASE_STEP+2);
  begin
    current_bits(c)<=parity(state_in and M0);
    future1_bits(c)<=parity(state_in and M1);
    future2_bits(c)<=parity(state_in and M2);
  end generate;
end architecture;
