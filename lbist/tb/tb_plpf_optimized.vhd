library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_plpf_optimized is  end entity;
architecture test of tb_plpf_optimized is
  signal clk : std_logic := '0';
  signal test_done : boolean := false;
  signal c,f1,f2,past,y,valid : std_logic := '0';
  signal mode : std_logic_vector(1 downto 0) := "11";
  signal chain : std_logic_vector(63 downto 0) := (others=>'0');
  signal manual : boolean := true;
  signal manual_past : std_logic := '0';
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
  past <= manual_past when manual else chain(0);
  dut: entity work.plpf_optimized port map(c,f1,f2,past,mode,y,valid);
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    variable bits : std_logic_vector(3 downto 0);
    variable previous : std_logic;
    variable transitions : natural;
    variable measured,err : real;
  begin
    for n in 1 to 3 loop
      mode<=mode_code(n);
      for k in 0 to 15 loop
        bits:=std_logic_vector(to_unsigned(k,4));
        c<=bits(0); f1<=bits(1); f2<=bits(2); manual_past<=bits(3);
        wait for 10 ps;
        check(valid='1' and y=filtered(bits(0),bits(1),bits(2),bits(3),mode_code(n)),"exhaustive truth table n=" & integer'image(n));
      end loop;
      report "[PASS] exhaustive truth table n=" & integer'image(n);
    end loop;
    mode<="10"; manual_past<='1'; wait for 10 ps; check(valid='0' and y='1',"reserved mode hold");
    mode<="UX"; wait for 10 ps; check(valid='0' and y='1',"unknown mode hold");
    mode<="00"; manual_past<='X'; wait for 10 ps; check(y='X',"unknown feedback is visible");
    report "[PASS] invalid modes and unknown feedback negative cases";
    manual<=false;
    for n in 1 to 3 loop
      chain<=(others=>'0'); mode<=mode_code(n); transitions:=0;
      wait for 10 ps; check(chain=x"0000000000000000","scan initialization");
      for j in 0 to 65534 loop
        c<=seq(j); f1<=seq(j+1); f2<=seq(j+2); wait for 10 ps;
        check((y='0' or y='1') and y=filtered(seq(j),seq(j+1),seq(j+2),chain(0),mode_code(n)),"scan-stage feedback and known output");
        if j>0 and y/=previous then transitions:=transitions+1; end if;
        previous:=y;
        wait until rising_edge(clk); chain<=chain(62 downto 0)&y;
        wait for 10 ps; check(chain(0)=previous,"input-stage FF capture");
      end loop;
      measured:=real(transitions)/65534.0; err:=abs(measured-expected_rate(n))*100.0;
      report "[METRIC] tb_plpf_optimized," & integer'image(n) & "," & real'image(expected_rate(n)) & "," & real'image(measured) & "," & real'image(err) & ",65535," & integer'image(transitions);
      check(err<=0.5,"toggle-rate error exceeds 0.5 percentage points");
      report "[PASS] measured toggle-rate tolerance n=" & integer'image(n);
    end loop;
    report "[TB_COMPLETE] tb_plpf_optimized at " & time'image(now); test_done<=true; wait;
  end process;
end architecture;
