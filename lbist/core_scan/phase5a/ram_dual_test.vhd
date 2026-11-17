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
library ieee;
use ieee.std_logic_1164.all;

entity ram_dual_test is
  generic (N_WORDS : integer := 64;
           WIDTH : integer := 8);
  port (data  : in std_logic_vector(WIDTH - 1 downto 0);
    raddr : in natural range 0 to N_WORDS - 1;
    waddr : in natural range 0 to N_WORDS - 1;
    we    : in std_logic;
    rclk  : in std_logic;
    wclk  : in std_logic;
    q     : out std_logic_vector(WIDTH - 1 downto 0); hold,read_hold : in std_logic;
       state_debug : out std_logic_vector(N_WORDS*WIDTH+WIDTH-1 downto 0));
end ram_dual_test;

architecture rtl of ram_dual_test is

  -- Build a 2-D array type for the RAM
  subtype word_t is std_logic_vector(WIDTH - 1 downto 0);
  type memory_t is array(N_WORDS - 1 downto 0) of word_t;

  -- Declare the RAM signal.
  signal ram : memory_t; --  := (others => (others => '0'));

begin
  state_debug(N_WORDS*WIDTH+WIDTH-1 downto N_WORDS*WIDTH)<=q;
  probe: for k in 0 to N_WORDS-1 generate
    state_debug((k+1)*WIDTH-1 downto k*WIDTH)<=ram(k);
  end generate;


  process(wclk)
  begin
    if((rising_edge(wclk) and hold='0')) then
      if(we = '1') then
        ram(waddr) <= data;
      end if;
    end if;
  end process;

  process(rclk)
  begin
    if((rising_edge(rclk) and read_hold='0')) then
      q <= ram(raddr);
    end if;
  end process;

end rtl;
