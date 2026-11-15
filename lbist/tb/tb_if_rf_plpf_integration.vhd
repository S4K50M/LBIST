library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
use work.phase2_tb_pkg.all;
entity tb_if_rf_plpf_integration is
  generic(PATTERNS : positive:=1024; BETA : natural:=20);
end entity;
architecture test of tb_if_rf_plpf_integration is
  signal clk : std_logic:='0';
  signal rst : std_logic:='0';
  signal generator_rst : std_logic;
  signal ld : std_logic:='1';
  signal scan_enable : std_logic:='0';
  signal scan_in,scan_out,scan_feedback,raw_bit,c,f1,f2,mode_valid,pattern_done : std_logic;
  signal mode_select,active_mode : std_logic_vector(1 downto 0);
  signal state : std_logic_vector(15 downto 0);
  signal pc_d,instr,pc_q,rf_instr : reg32:=(others=>'0');
  signal q : std_logic_vector(63 downto 0);
  signal shift_count : natural;
  signal shift_count_v : std_logic_vector(15 downto 0);
  signal event_id : std_logic_vector(7 downto 0):=(others=>'0');
  signal test_done : boolean:=false;
begin
  assert PATTERNS>=256 report "[CONFIG_ERROR] PATTERNS must be >=256" severity failure;
  generator_rst<=not rst; q<=pc_q&rf_instr;
  shift_count_v<=std_logic_vector(to_unsigned(shift_count,16));
  dut: entity work.reg_IF_RF_scan port map(clk,rst,ld,pc_d,pc_q,instr,rf_instr,scan_enable,scan_in,scan_out,scan_feedback);
  lfsr: entity work.lfsr_16 port map(clk,generator_rst,scan_enable,raw_bit,state);
  phases: entity work.phase_shifter port map(state,c,f1,f2);
  controller: entity work.basic_controller generic map(64,BETA)
    port map(clk,generator_rst,scan_enable,mode_select,shift_count,pattern_done);
  plpf: entity work.plpf_dynamic port map(c,f1,f2,scan_feedback,mode_select,scan_in,active_mode,mode_valid);
  clocking: process begin
    while not test_done loop wait for 1 ns;exit when test_done;clk<=not clk;end loop;wait;
  end process;
  watchdog: process begin wait until test_done for 20 ms;check(test_done,"PLPF integration watchdog");wait;end process;
  stimulus: process
    constant seq : bit_sequence:=sequence_model(x"AAAA");
    variable model,before : std_logic_vector(63 downto 0):=(others=>'0');
    variable j,serial,weighted,ff_changes,pattern_weight,temporal_weight : natural:=0;
    variable initial_bit,previous,expected_bit : std_logic:='0';
    variable expected_mode : std_logic_vector(1 downto 0);
    variable expected_rate,measured : real;
    procedure inspect is begin
      check(q=model,"real IF/RF all 64 bits match reference");
      check(scan_out=model(63) and scan_feedback=model(0),"real scan output/feedback ordering");
      check(state=window(seq,j mod 65535),"one LFSR advance per enabled shift");
      check(shift_count=j mod 64,"one controller advance per enabled shift");
      if j mod 64>=(64-BETA)/2 and j mod 64<64-(64-BETA)/2 then expected_mode:="11";else expected_mode:="00";end if;
      check(mode_select=expected_mode and active_mode=expected_mode and mode_valid='1',"Basic schedule and filter modes");
      expected_bit:=filtered(seq(j mod 65535),seq((j+1) mod 65535),seq((j+2) mod 65535),model(0),expected_mode);
      check(c=seq(j mod 65535) and f1=seq((j+1) mod 65535) and f2=seq((j+2) mod 65535),"exact phase lookahead");
      check(scan_in=expected_bit,"independent PLPF input with actual scan FF feedback");
    end;
    procedure shift is begin
      inspect;before:=model;model:=model(62 downto 0)&expected_bit;j:=j+1;
      wait until rising_edge(clk);wait for 100 ps;inspect;
      if j mod 64=0 then check(pattern_done='1',"exact 64-shift completion");
      else check(pattern_done='0',"no early pattern completion");end if;
      wait until falling_edge(clk);wait for 100 ps;
      check(q=model,"no falling-edge state update");
    end;
  begin
    wait until rising_edge(clk);wait for 100 ps;inspect;
    check(pattern_done='0',"deterministic reset");rst<='1';scan_enable<='1';event_id<=x"01";
    wait for 100 ps;
    for p in 0 to PATTERNS-1 loop
      initial_bit:=model(0);temporal_weight:=0;
      for s in 0 to 63 loop
        if p=8 and s=22 then
          scan_enable<='0';event_id<=x"02";wait for 100 ps;
          for pause in 1 to 3 loop wait until rising_edge(clk);wait for 100 ps;inspect;check(pattern_done='0',"pause completion remains clear");end loop;
          wait until falling_edge(clk);wait for 100 ps;scan_enable<='1';event_id<=x"03";wait for 100 ps;
        end if;
        inspect;
        if j>0 and expected_bit/=previous then serial:=serial+1;end if;
        previous:=expected_bit;
        if expected_bit/=model(0) then temporal_weight:=temporal_weight+64-s;end if;
        before:=model;shift;
        for k in 0 to 63 loop if before(k)/=model(k) then ff_changes:=ff_changes+1;end if;end loop;
      end loop;
      pattern_weight:=0;
      if initial_bit/=model(63) then pattern_weight:=64;end if;
      for k in 1 to 63 loop if model(k)/=model(k-1) then pattern_weight:=pattern_weight+k;end if;end loop;
      check(pattern_weight=temporal_weight,"independent loaded-pattern and temporal WTM identity");
      weighted:=weighted+temporal_weight;
    end loop;
    expected_rate:=1.0/14.0+real(BETA)/64.0*(0.5-1.0/14.0);
    measured:=real(weighted)/real(PATTERNS*2080);
    check(abs(measured-expected_rate)<0.02,"measured versus estimated WTM within fixed 2 pp");
    report "[SCAN_METRIC] PLPF,"&integer'image(PATTERNS)&","&integer'image(j)&","&
      integer'image(serial)&","&integer'image(weighted)&","&integer'image(ff_changes)&","&real'image(expected_rate)&","&real'image(measured);
    report "[PASS] "&integer'image(PATTERNS)&"-pattern reference, every real scan FF, exact phase/controller alignment, WTM identity and pause/resume";
    -- Unload is another 64 enabled shifts: it simultaneously loads the next pattern.
    event_id<=x"04";scan_enable<='0';ld<='0';pc_d<=x"1234ABCD";instr<=x"89EF5670";
    wait for 100 ps;model:=x"1234ABCD89EF5670";
    wait until rising_edge(clk);wait for 100 ps;inspect;
    check(pattern_done='0',"capture does not complete/advance scan pattern");
    wait until falling_edge(clk);wait for 100 ps;event_id<=x"05";scan_enable<='1';ld<='1';wait for 100 ps;
    for k in 63 downto 0 loop
      check(scan_out=model(63),"captured-response serial unload before shift");shift;
    end loop;
    check(j=(PATTERNS+1)*64,"unload source/controller accounting");
    report "[PASS] one-edge functional capture and exact 64-bit unload while loading next PLPF pattern";
    report "[TB_COMPLETE] tb_if_rf_plpf_integration at "&time'image(now);
    test_done<=true;wait;
  end process;
end architecture;
