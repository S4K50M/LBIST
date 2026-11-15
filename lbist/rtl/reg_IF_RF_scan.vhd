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


-- Phase 4: one 64-bit state bank, shared by functional and scan operation.
library ieee;
use ieee.std_logic_1164.all;
use work.p_WIRES.all;
entity reg_IF_RF_scan is
  port(clk,rst,ld : in std_logic;
       PCincd_d : in reg32; PCincd_q : out reg32;
       instr : in reg32; RF_instr : out reg32;
       scan_enable,scan_in : in std_logic;
       scan_out,scan_feedback : out std_logic);
end entity;
architecture rtl of reg_IF_RF_scan is
  signal q : std_logic_vector(63 downto 0);
begin
  PCincd_q<=q(63 downto 32); RF_instr<=q(31 downto 0);
  scan_out<=q(63); scan_feedback<=q(0);
  process(clk,rst)
  begin
    if rst='0' then q<=(others=>'0');
    elsif rising_edge(clk) then
      if scan_enable='1' then q<=q(62 downto 0)&scan_in;
      elsif ld='0' then q<=PCincd_d&instr;
      end if;
    end if;
  end process;
end architecture;
