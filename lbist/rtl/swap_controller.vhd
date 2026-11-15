library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
entity swap_controller is
  generic (CHAIN_LENGTH : positive := 64; BETA : natural := 16; NUM_CHAINS : positive := 4);
  port (clk, rst, scan_enable : in std_logic;
        mode_select : out std_logic_vector(2*NUM_CHAINS-1 downto 0);
        shift_count : out natural;
        pattern_done : out std_logic;
        pattern_index : out std_logic_vector(31 downto 0);
        alpha_debug, gamma_debug : out std_logic_vector(16*NUM_CHAINS-1 downto 0));
end entity;
architecture rtl of swap_controller is
  function short_low return natural is
  begin
    if BETA>CHAIN_LENGTH/2 then return 0; end if;
    return CHAIN_LENGTH/2-BETA;
  end;
  signal position : natural range 0 to CHAIN_LENGTH-1 := 0;
  signal pattern : unsigned(31 downto 0) := (others=>'0');
begin
  assert CHAIN_LENGTH>=28 and CHAIN_LENGTH<=4096 and CHAIN_LENGTH mod 2=0
    report "[CONFIG_ERROR] Swap requires even CHAIN_LENGTH in 28..4096" severity failure;
  assert short_low>=14 report "[CONFIG_ERROR] Swap requires L/2-BETA>=14" severity failure;
  assert NUM_CHAINS<=16 report "[CONFIG_ERROR] NUM_CHAINS must be 1..16" severity failure;
  shift_count<=position;
  pattern_index<=std_logic_vector(pattern);
  chains: for c in 0 to NUM_CHAINS-1 generate
    process(position,pattern)
      variable a,g : natural;
    begin
      -- Figure 7 physical order is IN -> alpha -> beta -> gamma -> OUT.
      -- Bits are applied chronologically in reverse: gamma, beta, alpha.
      if (pattern(0)='0' and c mod 2=0) or (pattern(0)='1' and c mod 2=1) then
        a:=short_low; g:=CHAIN_LENGTH/2;
      else a:=CHAIN_LENGTH/2; g:=short_low; end if;
      alpha_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned(a,16));
      gamma_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned(g,16));
      mode_select(2*c+1 downto 2*c)<="00";
      if position>=g and position<CHAIN_LENGTH-a then
        mode_select(2*c+1 downto 2*c)<="11";
      end if;
    end process;
  end generate;
  process(clk)
  begin
    if rising_edge(clk) then
      pattern_done<='0';
      if rst='1' then position<=0; pattern<=(others=>'0');
      elsif scan_enable='1' then
        if position=CHAIN_LENGTH-1 then
          position<=0; pattern<=pattern+1; pattern_done<='1';
        else position<=position+1; end if;
      end if;
    end if;
  end process;
end architecture;
