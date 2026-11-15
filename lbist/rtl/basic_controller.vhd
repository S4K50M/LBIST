library ieee;
use ieee.std_logic_1164.all;

-- Basic Control only. Output mode describes the PRE-EDGE shift position.
-- Synchronous active-high reset takes priority over scan_enable.
entity basic_controller is
  generic (CHAIN_LENGTH : positive := 64; BETA : natural := 20);
  port (clk, rst, scan_enable : in std_logic;
        mode_select : out std_logic_vector(1 downto 0);
        shift_count : out natural;
        pattern_done : out std_logic);
end entity;
architecture rtl of basic_controller is
  -- Guard subtraction before deriving constants, even for illegal generics.
  function low_length return natural is
  begin
    if BETA>CHAIN_LENGTH then return 0; end if;
    return (CHAIN_LENGTH-BETA)/2;
  end;
  function legal_parity return boolean is
  begin
    if BETA>CHAIN_LENGTH then return false; end if;
    return (CHAIN_LENGTH-BETA) mod 2=0;
  end;
  constant ALPHA : natural := low_length;
  -- ALPHA+BETA is only evaluated for valid configurations. This form avoids
  -- overflow for invalid BETA and CHAIN_LENGTH near integer'high.
  constant HIGH_END : natural := CHAIN_LENGTH-ALPHA;
  signal position : natural range 0 to CHAIN_LENGTH-1 := 0;
begin
  assert CHAIN_LENGTH>=28 report "[CONFIG_ERROR] CHAIN_LENGTH must be >=28 (two 14-bit low regions)" severity failure;
  assert BETA<=CHAIN_LENGTH report "[CONFIG_ERROR] BETA exceeds CHAIN_LENGTH" severity failure;
  assert legal_parity report "[CONFIG_ERROR] L-BETA must be even" severity failure;
  assert ALPHA>=14 report "[CONFIG_ERROR] low regions must be >=14 bits" severity failure;
  shift_count <= position;
  mode_select <= "11" when position>=ALPHA and position<HIGH_END else "00";
  process(clk)
  begin
    if rising_edge(clk) then
      pattern_done<='0';
      if rst='1' then position<=0;
      elsif scan_enable='1' then
        if position=CHAIN_LENGTH-1 then position<=0; pattern_done<='1';
        else position<=position+1; end if;
      end if;
    end if;
  end process;
end architecture;
