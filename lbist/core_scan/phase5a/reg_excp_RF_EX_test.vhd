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
entity reg_excp_RF_EX_test is
  port(clk, rst, ld: in  std_logic;
       RF_cop0_reg:     in  reg5;
       EX_cop0_reg:     out reg5;
       RF_cop0_sel:     in  reg3;
       EX_cop0_sel:     out reg3;
       RF_can_trap:     in  reg2;
       EX_can_trap:     out reg2;
       RF_exception:    in  exception_type;
       EX_exception:    out exception_type;
       RF_is_delayslot: in  std_logic;
       EX_is_delayslot: out std_logic;
       RF_PC_abort:     in  boolean;
       EX_PC_abort:     out boolean;
       RF_PC:           in  reg32;
       EX_PC:           out reg32;
       RF_trap_taken:   in  boolean;
       EX_trapped:      out boolean; hold : in std_logic);
end reg_excp_RF_EX_test;

architecture funcional of reg_excp_RF_EX_test is
begin
  process(clk, rst, ld)
  begin
    if rst = '0' then
      EX_can_trap     <= b"00";
      EX_is_delayslot <= '0';
      EX_trapped      <= FALSE;
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        EX_cop0_reg     <= RF_cop0_reg     ;
        EX_cop0_sel     <= RF_cop0_sel     ;
        EX_can_trap     <= RF_can_trap     ;
        EX_exception    <= RF_exception    ;
        EX_is_delayslot <= RF_is_delayslot ;
        EX_PC_abort     <= RF_PC_abort     ;
        EX_PC           <= RF_PC           ;
        EX_trapped      <= RF_trap_taken   ;
      end if;
    end if;
  end process;
end funcional;
