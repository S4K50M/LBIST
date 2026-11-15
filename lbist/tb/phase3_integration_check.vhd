library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
use work.phase3_tb_pkg.all;
entity phase3_integration_check is
  generic (APP : natural := 3; CHAIN_LENGTH : positive := 64; BETA : natural := 16;
           NUM_CHAINS : positive := 4; PATTERNS : positive := 1024);
  port(test_done : out boolean);
end entity;
architecture test of phase3_integration_check is
  signal clk : std_logic := '0';
  signal rst : std_logic := '1';
  signal scan_enable : std_logic := '0';
  signal finished : boolean := false;
  signal mode_select : std_logic_vector(2*NUM_CHAINS-1 downto 0);
  signal pattern_done : std_logic;
  signal shift_count,moving_position : natural := 0;
  signal pattern_index : std_logic_vector(31 downto 0);
  signal local_pattern : unsigned(31 downto 0) := (others=>'0');
  signal alpha_debug,gamma_debug : std_logic_vector(16*NUM_CHAINS-1 downto 0);
  signal state : std_logic_vector(15 downto 0);
  signal raw_bit : std_logic;
  signal current_bits,future1_bits,future2_bits,scan_in,past_bits,mode_valid : std_logic_vector(NUM_CHAINS-1 downto 0);
  signal active_mode : std_logic_vector(2*NUM_CHAINS-1 downto 0);
  signal chain_flat : std_logic_vector(NUM_CHAINS*CHAIN_LENGTH-1 downto 0) := (others=>'0');
  signal shift_count_v,moving_position_v,beta_v,alpha_0,gamma_0 : std_logic_vector(15 downto 0);
  signal mode_0,mode_1,mode_2,mode_3 : std_logic_vector(1 downto 0);
begin
  test_done<=finished;
  shift_count_v<=std_logic_vector(to_unsigned(shift_count,16));
  moving_position_v<=std_logic_vector(to_unsigned(moving_position,16));
  beta_v<=std_logic_vector(to_unsigned(BETA,16));
  alpha_0<=alpha_debug(15 downto 0); gamma_0<=gamma_debug(15 downto 0);
  mode_0<=mode_select(1 downto 0);
  c1: if NUM_CHAINS>1 generate mode_1<=mode_select(3 downto 2); end generate;
  c2: if NUM_CHAINS>2 generate mode_2<=mode_select(5 downto 4); end generate;
  c3: if NUM_CHAINS>3 generate mode_3<=mode_select(7 downto 6); end generate;
  clocking: process
  begin
    while not finished loop wait for 1 ns; exit when finished; clk<=not clk; end loop; wait;
  end process;
  watchdog: process
  begin
    wait until finished for 20 ms;
    assert finished report "[FAIL] integration watchdog" severity failure; wait;
  end process;
  basic_dut: if APP=2 generate
    signal basic_mode : std_logic_vector(1 downto 0);
  begin
    dut: entity work.basic_controller generic map(CHAIN_LENGTH,BETA)
      port map(clk,rst,scan_enable,basic_mode,shift_count,pattern_done);
    copies: for c in 0 to NUM_CHAINS-1 generate
      mode_select(2*c+1 downto 2*c)<=basic_mode;
      alpha_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned((CHAIN_LENGTH-BETA)/2,16));
      gamma_debug(16*c+15 downto 16*c)<=std_logic_vector(to_unsigned((CHAIN_LENGTH-BETA)/2,16));
    end generate;
    pattern_index<=std_logic_vector(local_pattern);
  end generate;
  swap_dut: if APP=3 generate
    dut: entity work.swap_controller generic map(CHAIN_LENGTH,BETA,NUM_CHAINS)
      port map(clk,rst,scan_enable,mode_select,shift_count,pattern_done,pattern_index,alpha_debug,gamma_debug);
  end generate;
  moving_dut: if APP=4 generate
    dut: entity work.moving_controller generic map(CHAIN_LENGTH,BETA,NUM_CHAINS,0)
      port map(clk,rst,scan_enable,mode_select,shift_count,pattern_done,pattern_index,moving_position,alpha_debug,gamma_debug);
  end generate;
  reference_sources: if APP<2 generate
    mode_select<=(others=>'1') when APP=0 else (others=>'0');
    alpha_debug<=(others=>'0'); gamma_debug<=(others=>'0');
    pattern_index<=std_logic_vector(local_pattern);
    process(clk)
    begin
      if rising_edge(clk) then
        pattern_done<='0';
        if rst='1' then shift_count<=0;
        elsif scan_enable='1' then
          if shift_count=CHAIN_LENGTH-1 then shift_count<=0; pattern_done<='1';
          else shift_count<=shift_count+1; end if;
        end if;
      end if;
    end process;
  end generate;
  local_index: if APP<=2 generate
    process(clk)
    begin
      if rising_edge(clk) then
        if rst='1' then local_pattern<=(others=>'0');
        elsif scan_enable='1' and shift_count=CHAIN_LENGTH-1 then local_pattern<=local_pattern+1; end if;
      end if;
    end process;
  end generate;
  lfsr: entity work.lfsr_16 port map(clk,rst,scan_enable,raw_bit,state);
  phases: entity work.multi_chain_phase_shifter generic map(NUM_CHAINS,257)
    port map(state,current_bits,future1_bits,future2_bits);
  chains: for c in 0 to NUM_CHAINS-1 generate
    past_bits(c)<=chain_flat(c*CHAIN_LENGTH);
    filter_unit: entity work.plpf_dynamic
      port map(current_bits(c),future1_bits(c),future2_bits(c),past_bits(c),
               mode_select(2*c+1 downto 2*c),scan_in(c),active_mode(2*c+1 downto 2*c),mode_valid(c));
  end generate;
  scan_model: process(clk)
  begin
    if rising_edge(clk) then
      if rst='1' then chain_flat<=(others=>'0');
      elsif scan_enable='1' then
        for c in 0 to NUM_CHAINS-1 loop
          chain_flat((c+1)*CHAIN_LENGTH-1 downto c*CHAIN_LENGTH)<=
            chain_flat((c+1)*CHAIN_LENGTH-2 downto c*CHAIN_LENGTH)&scan_in(c);
        end loop;
      end if;
    end if;
  end process;
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    subtype full_pattern is std_logic_vector(NUM_CHAINS*CHAIN_LENGTH-1 downto 0);
    type store_t is array(0 to PATTERNS-1) of full_pattern;
    variable stored : store_t;
    variable ref_chain,before_chain : full_pattern := (others=>'0');
    variable previous,initial_q,expected_bits : std_logic_vector(NUM_CHAINS-1 downto 0) := (others=>'0');
    variable exposure : nat_array(0 to NUM_CHAINS*CHAIN_LENGTH-1) := (others=>0);
    variable distinct : nat_array(0 to NUM_CHAINS-1) := (others=>0);
    variable pattern_weight,temporal_weight : nat_array(0 to NUM_CHAINS-1) := (others=>0);
    variable duplicate : boolean;
    variable serial_transitions,ff_changes,distinct_tuples,distinct_total,weighted_total : natural := 0;
    variable position,p,expected_count,offset : natural;
    variable t : timing_t;
    variable expected_mode : std_logic_vector(1 downto 0);
    procedure inspect(j : natural) is
      variable ti : timing_t;
      variable m : std_logic_vector(1 downto 0);
    begin
      check(shift_count=j mod CHAIN_LENGTH and to_integer(unsigned(pattern_index))=j/CHAIN_LENGTH,"controller pre/post-edge position and pattern index");
      check(state=window(seq,j mod 65535),"LFSR polynomial sequence and one advancement per enabled shift");
      if APP=4 then check(moving_position=(j/CHAIN_LENGTH) mod schedule_period(APP,CHAIN_LENGTH,BETA),"moving progression and wrap"); end if;
      for c in 0 to NUM_CHAINS-1 loop
        ti:=reference_timing(APP,CHAIN_LENGTH,BETA,j/CHAIN_LENGTH,c);
        if APP=0 then m:="11"; elsif APP=1 then m:="00";
        else m:=reference_mode(ti,j mod CHAIN_LENGTH); end if;
        check(mode_select(2*c+1 downto 2*c)=m,"independent per-chain mode schedule");
        check(current_bits(c)=seq((j+c*257) mod 65535) and
              future1_bits(c)=seq((j+c*257+1) mod 65535) and
              future2_bits(c)=seq((j+c*257+2) mod 65535),"independent exact chain phase/lookahead model");
        if APP>=2 then
          check(to_integer(unsigned(alpha_debug(16*c+15 downto 16*c)))=ti.a and
                to_integer(unsigned(gamma_debug(16*c+15 downto 16*c)))=ti.g,"debug region lengths");
        end if;
      end loop;
    end;
  begin
    check(NUM_CHAINS<=16 and PATTERNS>=256 and PATTERNS>=schedule_period(APP,CHAIN_LENGTH,BETA),"sufficient complete patterns and full schedule cycle");
    wait until rising_edge(clk); wait for 100 ps;
    inspect(0); check(chain_flat=ref_chain and pattern_done='0',"reset all simulated scan FFs");
    rst<='0'; scan_enable<='1';
    for j in 0 to PATTERNS*CHAIN_LENGTH-1 loop
      position:=j mod CHAIN_LENGTH; p:=j/CHAIN_LENGTH;
      inspect(j);
      if position=0 then
        for c in 0 to NUM_CHAINS-1 loop initial_q(c):=ref_chain(c*CHAIN_LENGTH); end loop;
      end if;
      before_chain:=ref_chain;
      for c in 0 to NUM_CHAINS-1 loop
        t:=reference_timing(APP,CHAIN_LENGTH,BETA,p,c);
        if APP=0 then expected_mode:="11"; elsif APP=1 then expected_mode:="00";
        else expected_mode:=reference_mode(t,position); end if;
        offset:=(j+c*257) mod 65535;
        expected_bits(c):=filtered(seq(offset),seq((offset+1) mod 65535),seq((offset+2) mod 65535),before_chain(c*CHAIN_LENGTH),expected_mode);
        check(mode_valid(c)='1' and active_mode(2*c+1 downto 2*c)=expected_mode and scan_in(c)=expected_bits(c),"PLPF output and independent input-stage feedback");
        check(past_bits(c)=before_chain(c*CHAIN_LENGTH),"actual per-chain first FF feedback");
        if j>0 and scan_in(c)/=previous(c) then serial_transitions:=serial_transitions+1; end if;
        if scan_in(c)/=before_chain(c*CHAIN_LENGTH) then temporal_weight(c):=temporal_weight(c)+CHAIN_LENGTH-position; end if;
        previous(c):=scan_in(c);
        ref_chain((c+1)*CHAIN_LENGTH-1 downto c*CHAIN_LENGTH):=
          before_chain((c+1)*CHAIN_LENGTH-2 downto c*CHAIN_LENGTH)&expected_bits(c);
        if mode_select(2*c+1 downto 2*c)="11" then
          exposure(c*CHAIN_LENGTH+CHAIN_LENGTH-1-position):=exposure(c*CHAIN_LENGTH+CHAIN_LENGTH-1-position)+1;
        end if;
      end loop;
      wait until rising_edge(clk); wait for 100 ps;
      check(chain_flat=ref_chain,"every scan FF equals the software-style register model");
      inspect(j+1);
      for bit_index in chain_flat'range loop
        check(chain_flat(bit_index)='0' or chain_flat(bit_index)='1',"no X/U scan bits after reset");
        if chain_flat(bit_index)/=before_chain(bit_index) then ff_changes:=ff_changes+1; end if;
      end loop;
      if position=CHAIN_LENGTH-1 then
        check(pattern_done='1',"completion exactly at enabled Lth shift");
        for c in 0 to NUM_CHAINS-1 loop
          if chain_flat((c+1)*CHAIN_LENGTH-1)/=initial_q(c) then pattern_weight(c):=pattern_weight(c)+CHAIN_LENGTH; end if;
          for i in 1 to CHAIN_LENGTH-1 loop
            if chain_flat(c*CHAIN_LENGTH+i-1)/=chain_flat(c*CHAIN_LENGTH+i) then pattern_weight(c):=pattern_weight(c)+i; end if;
          end loop;
          check(pattern_weight(c)=temporal_weight(c),"independent pattern-based WTM with correct orientation");
          duplicate:=false;
          for old in 0 to integer(p)-1 loop
            if stored(old)((c+1)*CHAIN_LENGTH-1 downto c*CHAIN_LENGTH)=chain_flat((c+1)*CHAIN_LENGTH-1 downto c*CHAIN_LENGTH) then duplicate:=true; end if;
          end loop;
          if not duplicate then distinct(c):=distinct(c)+1; end if;
        end loop;
        duplicate:=false;
        for old in 0 to integer(p)-1 loop if stored(old)=chain_flat then duplicate:=true; end if; end loop;
        if not duplicate then distinct_tuples:=distinct_tuples+1; end if;
        stored(p):=chain_flat;
      else check(pattern_done='0',"no spurious pattern completion"); end if;
      if j mod 1024=511 then
        scan_enable<='0';
        for pause in 1 to 3 loop
          wait until rising_edge(clk); wait for 100 ps;
          inspect(j+1); check(chain_flat=ref_chain and pattern_done='0',"joint pause, pulse clearing, stable FF feedback");
        end loop;
        scan_enable<='1';
      end if;
    end loop;
    scan_enable<='0';
    for c in 0 to NUM_CHAINS-1 loop
      distinct_total:=distinct_total+distinct(c);
      weighted_total:=weighted_total+temporal_weight(c);
      report "[DIVERSITY] " & integer'image(APP) & "," & integer'image(c) & "," & integer'image(distinct(c)) & "," & integer'image(PATTERNS);
      for k in 0 to CHAIN_LENGTH-1 loop
        expected_count:=0;
        for pat in 0 to PATTERNS-1 loop
          t:=reference_timing(APP,CHAIN_LENGTH,BETA,pat,c);
          if APP=0 or (APP>=2 and k>=t.a and k<t.a+t.b) then expected_count:=expected_count+1; end if;
        end loop;
        check(exposure(c*CHAIN_LENGTH+k)=expected_count,"physical-position unfiltered exposure");
        report "[EXPOSURE] " & integer'image(APP) & "," & integer'image(c) & "," & integer'image(k) & "," & integer'image(exposure(c*CHAIN_LENGTH+k)) & "," & integer'image(PATTERNS);
      end loop;
    end loop;
    report "[METRIC] " & integer'image(APP) & "," & integer'image(CHAIN_LENGTH) & "," & integer'image(BETA) & "," & integer'image(NUM_CHAINS) & "," & integer'image(PATTERNS) & "," & integer'image(PATTERNS*CHAIN_LENGTH) & "," & integer'image(serial_transitions) & "," & integer'image(weighted_total) & "," & integer'image(ff_changes) & "," & integer'image(distinct_total) & "," & integer'image(distinct_tuples) & "," & integer'image(schedule_period(APP,CHAIN_LENGTH,BETA)) & "," & time'image(now);
    report "[PASS] " & name_of(APP) & " exact phases, every scan FF, modes, pauses, complete patterns, WTM identity and physical exposure";
    report "[ENGINE_COMPLETE] " & name_of(APP) & " at " & time'image(now);
    finished<=true; wait;
  end process;
end architecture;
