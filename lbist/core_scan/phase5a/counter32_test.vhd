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
use IEEE.numeric_std.all;
use work.p_WIRES.all;
entity counter32_test is
  generic (INITIAL_VALUE: reg32 := x"00000000");
  port(clk, rst, ld, en: in  std_logic;
        D:               in  reg32;
        Q:               out reg32; hold : in std_logic);
end counter32_test;

architecture functional of counter32_test is
  signal count: reg32;
begin

  process(clk, rst)
  begin
    if rst = '0' then
      count <= INITIAL_VALUE;
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        count <= D;
      elsif en = '0' then
        count <= std_logic_vector(unsigned(count) + 1);
      end if;
    end if;
  end process;

  Q <= count;

end functional;
