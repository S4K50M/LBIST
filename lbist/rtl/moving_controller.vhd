library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
entity moving_controller is
  generic (CHAIN_LENGTH : positive := 64; BETA : natural := 16;
           NUM_CHAINS : positive := 4; INITIAL_POSITION : natural := 0);
  port (clk, rst, scan_enable : in std_logic;
        mode_select : out std_logic_vector(2*NUM_CHAINS-1 downto 0);
        shift_count : out natural;
        pattern_done : out std_logic;
        pattern_index : out std_logic_vector(31 downto 0);
        moving_position : out natural;
        alpha_debug, gamma_debug : out std_logic_vector(16*NUM_CHAINS-1 downto 0));
end entity;
architecture rtl of moving_controller is
  function span return positive is
  begin
    if BETA>CHAIN_LENGTH then return 1; end if;
    if CHAIN_LENGTH-BETA<28 then return 1; end if;
    return CHAIN_LENGTH-BETA-27;
  end;
  function valid_lengths return boolean is
  begin
    if BETA>CHAIN_LENGTH then return false; end if;
    return CHAIN_LENGTH-BETA>=28 and CHAIN_LENGTH<=4096;
  end;
  function safe_initial return natural is
  begin
    if INITIAL_POSITION>=span then return 0; end if;
    return INITIAL_POSITION;
  end;
  signal position : natural range 0 to CHAIN_LENGTH-1 := 0;
  signal movement : natural range 0 to span-1 := safe_initial;
  signal pattern : unsigned(31 downto 0) := (others=>'0');
begin
  assert valid_lengths report "[CONFIG_ERROR] Moving requires 28<=L<=4096 and BETA<=L-28" severity failure;
  assert INITIAL_POSITION<span report "[CONFIG_ERROR] INITIAL_POSITION outside legal movement range" severity failure;
  assert NUM_CHAINS<=16 report "[CONFIG_ERROR] NUM_CHAINS must be 1..16" severity failure;
  shift_count<=position; moving_position<=movement;
  pattern_index<=std_logic_vector(pattern);
  process(position,movement)
    variable a,g : natural;
  begin
    g:=14+movement;
    a:=0;
    if BETA<=CHAIN_LENGTH then
      if g<=CHAIN_LENGTH-BETA then a:=CHAIN_LENGTH-BETA-g; end if;
    end if;
    for c in 0 to NUM_CHAINS-1 loop
      alpha_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned(a,16));
      gamma_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned(g,16));
      mode_select(2*c+1 downto 2*c)<="00";
      if position>=g and position<CHAIN_LENGTH-a then
        mode_select(2*c+1 downto 2*c)<="11";
      end if;
    end loop;
  end process;
  process(clk)
  begin
    if rising_edge(clk) then
      pattern_done<='0';
      if rst='1' then position<=0; movement<=safe_initial; pattern<=(others=>'0');
      elsif scan_enable='1' then
        if position=CHAIN_LENGTH-1 then
          position<=0; pattern<=pattern+1; pattern_done<='1';
          if movement=span-1 then movement<=0; else movement<=movement+1; end if;
        else position<=position+1; end if;
      end if;
    end if;
  end process;
end architecture;
