library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_phase_shifter is  end entity;
architecture test of tb_phase_shifter is
  signal clk : std_logic := '0';
  signal test_done : boolean := false;
  signal rst : std_logic := '1';
  signal en : std_logic := '0';
  signal state, manual_state, selected : std_logic_vector(15 downto 0) := (others=>'0');
  signal manual : boolean := false;
  signal bit_out,c,f1,f2 : std_logic;
begin
  clocking : process
  begin
    while not test_done loop wait for 1 ns; clk <= not clk; end loop;
    wait;
  end process;
  watchdog : process
  begin
    wait until test_done for 2 ms;
    assert test_done report "[FAIL] Simulation watchdog timeout" severity failure;
    wait;
  end process;
  dut_lfsr: entity work.lfsr_16 port map(clk,rst,en,bit_out,state);
  selected <= manual_state when manual else state;
  dut: entity work.phase_shifter port map(selected,c,f1,f2);
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    variable prev1,prev2 : std_logic;
  begin
    wait for 100 ps; check(c=seq(0) and f1=seq(1) and f2=seq(2),"reset lookahead");
    rst<='0'; en<='1';
    for j in 0 to 4095 loop
      check(c=seq(j) and f1=seq(j+1) and f2=seq(j+2),"independent lookahead");
      prev1:=f1; prev2:=f2;
      wait until rising_edge(clk); wait for 100 ps;
      check(c=prev1 and f1=prev2,"future bits become actual outputs");
    end loop;
    report "[PASS] 4096 states, lookahead and consecutive-state relationship";
    en<='0';
    for j in 1 to 4 loop wait until rising_edge(clk); wait for 100 ps; check(c=seq(4096) and f1=seq(4097) and f2=seq(4098),"disabled lookahead hold"); end loop;
    rst<='1'; wait for 100 ps; check(c=seq(0) and f1=seq(1) and f2=seq(2),"reset during operation");
    manual<=true;
    for j in 0 to 65535 loop
      manual_state<=std_logic_vector(to_unsigned(j,16)); wait for 1 ps;
      check(c=manual_state(0) and f1=manual_state(1) and f2=manual_state(2),"combinational exhaustive state check");
    end loop;
    report "[PASS] reset, hold, all 65536 combinational inputs without a clock dependency";
    report "[TB_COMPLETE] tb_phase_shifter at " & time'image(now); test_done<=true; wait;
  end process;
end architecture;
