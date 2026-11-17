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
library IEEE; use IEEE.std_logic_1164.all;

entity FFD_test is
  port(clk, rst, set : in std_logic;
        D : in  std_logic;
        Q : out std_logic; hold : in std_logic);
end FFD_test;

architecture functional of FFD_test is
begin

  process(clk, rst, set)
    variable state: std_logic;
  begin
    if rst = '0' then
      state := '0';
    elsif set = '0' then
      state := '1';
    elsif (rising_edge(clk) and hold='0') then
      state := D;
    end if;
    Q <= state;
  end process;

end functional;
