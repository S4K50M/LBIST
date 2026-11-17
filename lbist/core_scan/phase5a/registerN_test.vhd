-- ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
--  cMIPS, a VHDL model of the classical five stage MIPS pipeline.
--  Copyright (C) 2013  Roberto Andre Hexsel
--
--  This program is free software: you can redistribute it and/or modify
--  it under the terms of the GNU General Public License as published by
--  the Free Software Foundation, version 3.
--
--  This program is distributed in the hope that it will be useful,
--  but WITHOUT ANY WARRANTY; without even the implied warranty of
--  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
--  GNU General Public License for more details.
--
--  You should have received a copy of the GNU General Public License
--  along with this program.  If not, see <http://www.gnu.org/licenses/>.
-- ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


-- ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
library IEEE;
use IEEE.std_logic_1164.all;
use work.p_WIRES.all;
entity registerN_test is
  generic (NUM_BITS: integer := 16;
           INIT_VAL: std_logic_vector);
  port(clk, rst, ld: in  std_logic;
       D:            in  std_logic_vector(NUM_BITS-1 downto 0);
       Q:            out std_logic_vector(NUM_BITS-1 downto 0); hold : in std_logic);
end registerN_test;

architecture functional of registerN_test is
begin
  process(clk, rst)
    variable state: std_logic_vector(NUM_BITS-1 downto 0);
  begin
    if rst = '0' then
      state := INIT_VAL;
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        state := D;
      end if;
    end if;
    Q <= state;
  end process;

end functional;
