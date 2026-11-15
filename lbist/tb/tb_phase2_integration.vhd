library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_phase2_integration is generic (CHAIN_LENGTH : positive := 64); end entity;
architecture test of tb_phase2_integration is
  signal clk : std_logic := '0';
  signal test_done : boolean := false;
  signal rst : std_logic := '1';
  signal scan_enable : std_logic := '0';
  signal state : std_logic_vector(15 downto 0);
  signal c,f1,f2,y,valid,raw : std_logic;
  signal mode,active : std_logic_vector(1 downto 0) := "11";
  signal chain : std_logic_vector(CHAIN_LENGTH-1 downto 0) := (others=>'0');
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
  check_length: assert CHAIN_LENGTH>=2 and CHAIN_LENGTH<=1024 report "[FAIL] chain length must be 2..1024" severity failure;
  lfsr: entity work.lfsr_16 port map(clk,rst,scan_enable,raw,state);
  phase_unit: entity work.phase_shifter port map(state,c,f1,f2);
  filter_dut: entity work.plpf_dynamic port map(c,f1,f2,chain(0),mode,y,active,valid);
  scan_model: process(clk,rst)
  begin
    if rst='1' then chain<=(others=>'0');
    elsif rising_edge(clk) then
      if scan_enable='1' then chain<=chain(CHAIN_LENGTH-2 downto 0)&y; end if;
    end if;
  end process;
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    constant SAMPLES : positive := (16384/CHAIN_LENGTH)*CHAIN_LENGTH;
    variable reference_chain, before_chain : std_logic_vector(CHAIN_LENGTH-1 downto 0) := (others=>'0');
    variable pattern_initial : std_logic := '0';
    variable pattern_weight,pattern_total : natural := 0;
    variable expected,previous : std_logic := '0';
    variable transitions,wtm_weight,changes,steps,weight,pattern_count : natural;
    variable measured,err,wtm : real;
    variable selected_mode : std_logic_vector(1 downto 0);
  begin
    for n in 1 to 4 loop
      rst<='1'; scan_enable<='0'; reference_chain:=(others=>'0');
      wait for 100 ps; check(chain=reference_chain and state=x"AAAA","deterministic chain/LFSR reset");
      rst<='0'; scan_enable<='1'; transitions:=0; wtm_weight:=0; changes:=0; steps:=0; pattern_total:=0;
      for j in 0 to SAMPLES-1 loop
        if n<=3 then selected_mode:=mode_code(n);
        else selected_mode:=mode_code((j/17) mod 3+1); end if;
        if j mod CHAIN_LENGTH=0 then pattern_initial:=reference_chain(0); end if;
        mode<=selected_mode; wait for 100 ps;
        check(state=window(seq,j),"LFSR state before scan edge");
        expected:=filtered(seq(j),seq(j+1),seq(j+2),reference_chain(0),selected_mode);
        check(y=expected and valid='1' and active=selected_mode,"feedback from input-stage FF Q");
        if j>0 and y/=previous then transitions:=transitions+1; end if;
        -- Paper WTMin: first-applied transition has weight L; last weight 1.
        -- Includes initialized/history boundary at each pattern, unlike serial rate.
        weight:=CHAIN_LENGTH-(j mod CHAIN_LENGTH);
        if y/=reference_chain(0) then wtm_weight:=wtm_weight+weight; end if;
        previous:=y; before_chain:=reference_chain;
        reference_chain:=reference_chain(CHAIN_LENGTH-2 downto 0)&expected;
        wait until rising_edge(clk); wait for 100 ps;
        check(chain=reference_chain and state=window(seq,j+1),"full scan ordering, single shift, deterministic pattern");
        for k in 0 to CHAIN_LENGTH-1 loop if chain(k)/=before_chain(k) then changes:=changes+1; end if; end loop;
        steps:=steps+1;
        if (j+1) mod CHAIN_LENGTH=0 then
          -- Independent pattern-domain WTM check against time-domain weights.
          pattern_weight:=0;
          if chain(CHAIN_LENGTH-1)/=pattern_initial then pattern_weight:=CHAIN_LENGTH; end if;
          for i in 1 to CHAIN_LENGTH-1 loop
            if chain(i-1)/=chain(i) then pattern_weight:=pattern_weight+i; end if;
          end loop;
          pattern_total:=pattern_total+pattern_weight;
          check(pattern_total=wtm_weight,"pattern-domain and chronological WTM must agree");
        end if;
        if j mod 1024=511 then
          scan_enable<='0';
          for pause in 1 to 3 loop
            wait until rising_edge(clk); wait for 100 ps;
            check(chain=reference_chain and state=window(seq,j+1),"scan and LFSR pause");
          end loop;
          scan_enable<='1';
        end if;
      end loop;
      scan_enable<='0';
      measured:=real(transitions)/real(SAMPLES-1);
      pattern_count:=SAMPLES/CHAIN_LENGTH;
      wtm:=real(wtm_weight)/real(pattern_count*CHAIN_LENGTH*(CHAIN_LENGTH+1)/2);
      if n<=3 then
        err:=abs(measured-expected_rate(n))*100.0;
        report "[METRIC] tb_phase2_integration," & integer'image(n) & "," & real'image(expected_rate(n)) & "," & real'image(measured) & "," & real'image(err) & "," & integer'image(SAMPLES) & "," & integer'image(transitions);
        check(err<=1.0,"integration toggle tolerance exceeds 1 percentage point");
      else
        report "[METRIC] tb_phase2_integration,dynamic,NA," & real'image(measured) & ",NA," & integer'image(SAMPLES) & "," & integer'image(transitions);
      end if;
      report "[WTM] " & integer'image(n) & "," & integer'image(CHAIN_LENGTH) & "," & integer'image(pattern_count) & "," & real'image(wtm) & "," & real'image(real(changes)/real(steps*CHAIN_LENGTH)) & "," & integer'image(wtm_weight);
      report "[PASS] integration epoch " & integer'image(n) & ": serial metrics, WTM, full-chain scoreboarding, pause/resume";
    end loop;
    report "[TB_COMPLETE] tb_phase2_integration at " & time'image(now); test_done<=true; wait;
  end process;
end architecture;
