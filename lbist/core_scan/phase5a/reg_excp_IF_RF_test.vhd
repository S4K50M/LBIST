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
entity reg_excp_IF_RF_test is
  port(clk, rst, ld: in  std_logic;
       IF_excp_type: in  exception_type;
       RF_excp_type: out exception_type;
       PC_abort:     in  boolean;
       RF_PC_abort:  out boolean;
       IF_PC:        in  reg32;
       RF_PC:        out reg32; hold : in std_logic);
end reg_excp_IF_RF_test;

architecture funcional of reg_excp_IF_RF_test is
begin
  process(clk, rst, ld)
  begin
    if (rising_edge(clk) and hold='0') then
      if ld = '0' then
        RF_excp_type <= IF_excp_type ;
        RF_PC_abort  <= PC_abort     ;
        RF_PC        <= IF_PC        ;
      end if;
    end if;
  end process;
end funcional;
