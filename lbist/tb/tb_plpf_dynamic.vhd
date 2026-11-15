library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_plpf_dynamic is  end entity;
architecture test of tb_plpf_dynamic is
  signal clk : std_logic := '0';
  signal test_done : boolean := false;
  signal rst : std_logic := '1';
  signal en : std_logic := '0';
  signal state : std_logic_vector(15 downto 0);
  signal c,f1,f2,y,valid,raw : std_logic;
  signal mode,active : std_logic_vector(1 downto 0) := "11";
  signal chain : std_logic_vector(63 downto 0) := (others=>'0');
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
  lfsr: entity work.lfsr_16 port map(clk,rst,en,raw,state);
  phase_unit: entity work.phase_shifter port map(state,c,f1,f2);
  dut: entity work.plpf_dynamic port map(c,f1,f2,chain(0),mode,y,active,valid);
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    variable chosen : std_logic_vector(1 downto 0);
    variable expected,previous : std_logic;
  begin
    wait for 100 ps; rst<='0'; en<='1';
    for j in 0 to 4095 loop
      -- Includes 1->2->3->1, every-cycle changes, reserved and unknown.
      case j mod 5 is
        when 0=>chosen:="11"; when 1=>chosen:="01"; when 2=>chosen:="00";
        when 3=>chosen:="10"; when others=>chosen:="UX";
      end case;
      mode<=chosen; wait for 100 ps;
      check(state=window(seq,j),"mode switching must not advance or reset LFSR");
      expected:=filtered(seq(j),seq(j+1),seq(j+2),chain(0),chosen);
      check(y=expected and active=chosen,"mode alignment without a clock");
      if chosen="10" or chosen="UX" then check(valid='0' and y=chain(0),"invalid mode feedback hold");
      else check(valid='1',"valid mode flag"); end if;
      wait until rising_edge(clk); chain<=chain(62 downto 0)&y;
      wait for 100 ps;
      check(chain(0)=expected and state=window(seq,j+1),"exactly one LFSR and scan shift per edge");
    end loop;
    report "[PASS] continuous shifting, repeated transitions, invalid and unknown modes, no extra cycles";
    -- Explicit 3->1 boundary as well as 1->2 and 2->3 above.
    mode<="00"; wait for 100 ps; previous:=chain(0);
    mode<="11"; wait for 100 ps; check(y=c and state=window(seq,4096) and chain(0)=previous,"3 to 1 combinational boundary");
    en<='0';
    for j in 1 to 4 loop wait until rising_edge(clk); wait for 100 ps; check(state=window(seq,4096),"pause preserves state"); end loop;
    report "[PASS] explicit 3->1 boundary and LFSR pause";
    report "[TB_COMPLETE] tb_plpf_dynamic at " & time'image(now); test_done<=true; wait;
  end process;
end architecture;
