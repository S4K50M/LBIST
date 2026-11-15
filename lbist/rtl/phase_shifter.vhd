library ieee;
use ieee.std_logic_1164.all;
-- With lfsr_16's chronological state convention, adjacent bits are the
-- exact next two output bits. No clock, state update, or latency is needed.
-- Additional scan chains can later use GF(2) linear combinations of state.
entity phase_shifter is
  port (state_in : in std_logic_vector(15 downto 0);
        current_bit, future1, future2 : out std_logic);
end entity;
architecture rtl of phase_shifter is
begin
  current_bit <= state_in(0);
  future1 <= state_in(1);
  future2 <= state_in(2);
end architecture;
