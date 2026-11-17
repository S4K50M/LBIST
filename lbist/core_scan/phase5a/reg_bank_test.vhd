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
use IEEE.std_Logic_1164.all;
use IEEE.numeric_std.all;
use work.p_wires.all;

entity reg_bank_test is
  port(wrclk, rdclk, wren : in  std_logic;
       a_rs, a_rt, a_rd   : in  reg5;
       C                  : in  reg32;
       A, B               : out reg32; hold,read_hold : in std_logic;
       state_debug : out std_logic_vector(2111 downto 0));
end reg_bank_test;


-- -----------------------------------------------------------------------
-- RTL with implicit memory
-- -----------------------------------------------------------------------
architecture rtl of reg_bank_test is

  type reg_file is array(0 to 31) of reg32;
  signal reg_file_A : reg_file;
  signal reg_file_B : reg_file;
  signal int_rs, int_rt, int_rd : integer range 0 to 31;
  signal pre_A, pre_B : reg32;
begin
  state_debug(2111 downto 2048)<=pre_A&pre_B;
  probe: for k in 0 to 31 generate
    state_debug(32*k+31 downto 32*k)<=reg_file_A(k);
    state_debug(1024+32*k+31 downto 1024+32*k)<=reg_file_B(k);
  end generate;


  int_rs <= to_integer(unsigned(a_rs));
  int_rt <= to_integer(unsigned(a_rt));
  int_rd <= to_integer(unsigned(a_rd));

  -- forwarding WB -> RF, external to RAM
  A <= C  when (a_rd = a_rs) and (wren = '0') and (a_rs /= b"00000")
       else pre_A when a_rs /= b"00000"
       else x"00000000";                        -- reg0 always zero
  B <= C  when (a_rd = a_rt) and (wren = '0') and (a_rt /= b"00000")
       else pre_B when a_rt /= b"00000"
       else x"00000000";

  WRITE_REG_BANKS: process(wrclk, rdclk)
  begin
    if (rising_edge(rdclk) and read_hold='0') then          -- read early
      pre_A <= reg_file_A( int_rs );
      pre_B <= reg_file_B( int_rt );
    end if;

    -- write to enforce setup (forwarding is external to RAM)
    if (rising_edge(wrclk) and hold='0') then
      if wren = '0' and int_rd /= 0 then
        reg_file_A( int_rd ) <= C;
        reg_file_B( int_rd ) <= C;
      end if;
    end if;
  end process WRITE_REG_BANKS;

end rtl;
-- -----------------------------------------------------------------------


-- -----------------------------------------------------------------------
-- RTL with explicitly declared dual-port RAMs (FPGA friendly)
-- -----------------------------------------------------------------------
architecture dual_port_ram of reg_bank_test is

  component ram_dual is
    generic (N_WORDS : integer;
             WIDTH : integer);
    port (data  : in std_logic_vector;
          raddr : in natural range 0 to N_WORDS-1;
          waddr : in natural range 0 to N_WORDS-1;
          we    : in std_logic;
          rclk  : in std_logic;
          wclk  : in std_logic;
          q     : out std_logic_vector);
  end component ram_dual;

  signal int_rs, int_rt, int_rd : integer range 0 to 31;
  signal pre_A, pre_B : reg32;
  signal update : std_logic;
signal debug_a,debug_b : std_logic_vector(1055 downto 0);
begin
 state_debug<=debug_a&debug_b;


  int_rs <= to_integer(unsigned(a_rs));
  int_rt <= to_integer(unsigned(a_rt));
  int_rd <= to_integer(unsigned(a_rd));

  update <= '1' when wren = '0' and int_rd /= 0 else '0';

  PORT_A: entity work.ram_dual_test generic map (32, 32) port map (C, int_rs, int_rd, update, rdclk, wrclk, pre_A,hold,read_hold,debug_a);

  PORT_B: entity work.ram_dual_test generic map (32, 32) port map (C, int_rt, int_rd, update, rdclk, wrclk, pre_B,hold,read_hold,debug_b);

  -- internal forwarding WB -> RF
  A <= C  when (a_rd = a_rs) and (wren = '0') and (a_rs /= b"00000") else
       pre_A when a_rs /= b"00000"
       else x"00000000";                        -- reg0 always zero
  B <= C  when (a_rd = a_rt) and (wren = '0') and (a_rt /= b"00000") else
       pre_B when a_rt /= b"00000"
       else x"00000000";

end architecture dual_port_ram;
