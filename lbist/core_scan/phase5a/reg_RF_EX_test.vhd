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
entity reg_RF_EX_test is
  port(clk, rst, ld: in  std_logic;
       selB:       in  std_logic;
       EX_selB:    out std_logic;
       oper:       in  t_alu_fun;
       EX_oper:    out t_alu_fun;
       a_rs:       in  reg5;
       EX_a_rs:    out reg5;
       a_rt:       in  reg5;
       EX_a_rt:    out reg5;
       a_c:        in  reg5;
       EX_a_c:     out reg5;
       wreg:       in  std_logic;
       EX_wreg:    out std_logic;
       muxC:       in  reg3;
       EX_muxC:    out reg3;
       move:       in  std_logic;
       EX_move:    out std_logic;
       postn:      in  reg5;
       EX_postn:   out reg5;
       shamt:      in  reg5;
       EX_shamt:   out reg5;
       aVal:       in  std_logic;
       EX_aVal:    out std_logic;
       wrmem:      in  std_logic;
       EX_wrmem:   out std_logic;
       mem_t:      in  reg4;
       EX_mem_t:   out reg4;
       is_load:    in  boolean;
       EX_is_load: out boolean;
       A:          in  reg32;
       EX_A:       out reg32;
       B:          in  reg32;
       EX_B:       out reg32;
       displ32:    in  reg32;
       EX_displ32: out reg32;
       pc_p8:      in  reg32;
       EX_pc_p8:   out reg32; hold : in std_logic);
end reg_RF_EX_test;

architecture funcional of reg_RF_EX_test is
begin
  process(clk, rst)
  begin
    if rst = '0' then
      EX_wreg  <= '1';
      EX_wrmem <= '1';
      EX_aVal  <= '1';
    elsif (rising_edge(clk) and hold='0') then
      if ld = '0' then
        EX_selB    <= selB    ;
        EX_oper    <= oper    ;
        EX_a_rs    <= a_rs    ;
        EX_a_rt    <= a_rt    ;
        EX_a_c     <= a_c     ;
        EX_wreg    <= wreg    ;
        EX_muxC    <= muxC    ;
        EX_move    <= move    ;
        EX_postn   <= postn   ;
        EX_shamt   <= shamt   ;
        EX_aVal    <= aVal    ;
        EX_wrmem   <= wrmem   ;
        EX_mem_t   <= mem_t   ;
        EX_is_load <= is_load ;
        EX_A       <= A       ;
        EX_B       <= B       ;
        EX_displ32 <= displ32 ;
        EX_pc_p8   <= pc_p8   ;
      end if;
    end if;
    end process;
end funcional;
