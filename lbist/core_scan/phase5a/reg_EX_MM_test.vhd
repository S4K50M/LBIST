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
entity reg_EX_MM_test is
  port(clk, rst, ld: in  std_logic;
       EX_a_rt:    in  reg5;
       MM_a_rt:    out reg5;
       EX_a_c:     in  reg5;
       MM_a_c:     out reg5;
       EX_wreg:    in  std_logic;
       MM_wreg:    out std_logic;
       EX_muxC:    in  reg3;
       MM_muxC:    out reg3;
       EX_aVal:    in  std_logic;
       MM_aVal:    out std_logic;
       EX_wrmem:   in  std_logic;
       MM_wrmem:   out std_logic;
       EX_mem_t:   in  reg4;
       MM_mem_t:   out reg4;
       EX_is_load: in  boolean;
       MM_is_load: out boolean;
       EX_A:       in  reg32;
       MM_A:       out reg32;
       EX_B:       in  reg32;
       MM_B:       out reg32;
       EX_result:  in  reg32;
       MM_result:  out reg32;
       EX_addr:    in  reg32;
       MM_addr:    out reg32;
       HI:         in  reg32;
       MM_HI:      out reg32;
       LO:         in  reg32;
       MM_LO:      out reg32;
       EX_alu_move_ok: in  std_logic;
       MM_alu_move_ok: out std_logic;
       EX_move:    in  std_logic;
       MM_move:    out std_logic;
       EX_pc_p8:   in  reg32;
       MM_pc_p8:   out reg32; hold : in std_logic);
end reg_EX_MM_test;

architecture funcional of reg_EX_MM_test is
begin
  process(clk, rst)
  begin
    if rst = '0' then
      MM_wreg  <= '1';
      MM_wrmem <= '1';
      MM_aVal  <= '1';
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        MM_a_rt     <= EX_a_rt    ;
        MM_a_c      <= EX_a_c     ;
        MM_wreg     <= EX_wreg    ;
        MM_muxC     <= EX_muxC    ;
        MM_aVal     <= EX_aVal    ;
        MM_wrmem    <= EX_wrmem   ;
        MM_mem_t    <= EX_mem_t   ;
        MM_is_load  <= EX_is_load ;
        MM_A        <= EX_A       ;
        MM_B        <= EX_B       ;
        MM_result   <= EX_result  ;
        MM_addr     <= EX_addr    ;
        MM_HI       <= HI         ;
        MM_LO       <= LO         ;
        MM_alu_move_ok <= EX_alu_move_ok ;
        MM_move     <= EX_move    ;
        MM_pc_p8    <= EX_pc_p8   ;
      end if;
    end if;
  end process;
end funcional;
