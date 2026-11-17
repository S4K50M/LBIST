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
use work.p_EXCEPTION.all;
entity reg_excp_MM_WB_test is
  port(clk, rst, ld:  in  std_logic;
       MM_PC:         in  reg32;
       WB_PC:         out reg32;
       MM_cop0_LLbit: in  std_logic;
       WB_cop0_LLbit: out std_logic;
       MM_is_delayslot: in  std_logic;
       WB_is_delayslot: out std_logic;
       MM_cop0_val:   in  reg32;
       WB_cop0_val:   out reg32; hold : in std_logic);
end reg_excp_MM_WB_test;

architecture funcional of reg_excp_MM_WB_test is
begin
  process(clk, rst, ld)
  begin
    if rst = '0' then
      WB_cop0_LLbit <= '0';
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        WB_PC           <= MM_PC         ;
        WB_cop0_LLbit   <= MM_cop0_LLbit ;
        WB_is_delayslot <= MM_is_delayslot;
        WB_cop0_val     <= MM_cop0_val   ;
      end if;
    end if;
  end process;

end funcional;
