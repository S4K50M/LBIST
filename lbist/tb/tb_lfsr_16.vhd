library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_lfsr_16 is  end entity;
architecture test of tb_lfsr_16 is
  signal clk : std_logic := '0';
  signal test_done : boolean := false;
  signal rst : std_logic := '1';
  signal en, bit_out, zero_bit, custom_bit : std_logic := '0';
  signal state, zero_state, custom_state : std_logic_vector(15 downto 0);
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
  dut: entity work.lfsr_16 port map(clk,rst,en,bit_out,state);
  zero_seed: entity work.lfsr_16 generic map(x"0000") port map(clk,rst,en,zero_bit,zero_state);
  custom_seed: entity work.lfsr_16 generic map(x"0001") port map(clk,rst,en,custom_bit,custom_state);
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    constant custom : bit_sequence := sequence_model(x"0001");
    type seen_array is array(0 to 65535) of boolean;
    variable seen : seen_array := (others=>false);
    variable ones, value : natural := 0;
  begin
    wait for 100 ps;
    check(state=x"AAAA" and zero_state=x"AAAA" and custom_state=x"0001", "seed/default/zero-seed fallback");
    report "[PASS] reset, configurable seed, zero seed fallback";
    rst<='0'; en<='1';
    for j in 0 to 65534 loop
      check(state=window(seq,j) and custom_state=window(custom,j), "polynomial sequence/state " & integer'image(j));
      check(bit_out=seq(j) and state/=x"0000" and zero_state=state,"output and no zero state");
      value:=to_integer(unsigned(state)); check(not seen(value),"premature period repetition"); seen(value):=true;
      if bit_out='1' then ones:=ones+1; end if;
      wait until rising_edge(clk); wait for 100 ps;
    end loop;
    check(state=x"AAAA" and ones=32768,"full period 65535 and balanced distribution");
    report "[PASS] 65535 unique nonzero states, independent recurrence, output distribution 32768/65535";
    en<='0';
    for j in 1 to 5 loop wait until rising_edge(clk); wait for 100 ps; check(state=x"AAAA","disabled hold"); end loop;
    en<='1'; wait until rising_edge(clk); wait for 100 ps; check(state=window(seq,1),"resume");
    rst<='1'; wait for 100 ps; check(state=x"AAAA","asynchronous reset during operation");
    report "[PASS] hold, resume, mid-sequence reset";
    report "[TB_COMPLETE] tb_lfsr_16 at " & time'image(now); test_done<=true; wait;
  end process;
end architecture;
