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
entity reg_MM_WB_test is
  port(clk, rst, ld: in  std_logic;
       MM_a_c:     in  reg5;
       WB_a_c:     out reg5;
       MM_wreg:    in  std_logic;
       WB_wreg:    out std_logic;
       MM_muxC:    in  reg3;
       WB_muxC:    out reg3;
       MM_A:       in  reg32;
       WB_A:       out reg32;
       MM_result:  in  reg32;
       WB_result:  out reg32;
       MM_HI:      in  reg32;
       WB_HI:      out reg32;
       MM_LO:      in  reg32;
       WB_LO:      out reg32;
       rd_data:    in  reg32;
       WB_rd_data: out reg32;
       MM_B_data:  in  reg32;
       WB_B_data:  out reg32;
       MM_addr2:   in  reg2;
       WB_addr2:   out reg2;
       MM_oper:    in  reg2;
       WB_oper:    out reg2;
       MM_pc_p8:   in  reg32;
       WB_pc_p8:   out reg32; hold : in std_logic);
end reg_MM_WB_test;

architecture funcional of reg_MM_WB_test is
begin
  process(clk, rst)
  begin
    if rst = '0' then
      WB_wreg  <= '1';
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        WB_a_c     <= MM_a_c    ;
        WB_wreg    <= MM_wreg   ;
        WB_muxC    <= MM_muxC   ;
        WB_A       <= MM_A      ;
        WB_result  <= MM_result ;
        WB_HI      <= MM_HI     ;
        WB_LO      <= MM_LO     ;
        WB_rd_data <= rd_data   ;
        WB_B_data  <= MM_B_data ;
        WB_addr2   <= MM_addr2  ;
        WB_oper    <= MM_oper   ;
        WB_pc_p8   <= MM_pc_p8  ;
      end if;
    end if;
  end process;

end funcional;
