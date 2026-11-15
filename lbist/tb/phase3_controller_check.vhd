library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
use work.phase3_tb_pkg.all;
entity phase3_controller_check is
  generic (APP : natural := 3; CHAIN_LENGTH : positive := 64;
           BETA : natural := 16; NUM_CHAINS : positive := 4;
           INITIAL_POSITION : natural := 0);
  port(test_done : out boolean);
end entity;
architecture test of phase3_controller_check is
  signal clk : std_logic := '0';
  signal rst : std_logic := '1';
  signal scan_enable : std_logic := '0';
  signal finished : boolean := false;
  signal mode_select : std_logic_vector(2*NUM_CHAINS-1 downto 0);
  signal pattern_done : std_logic;
  signal shift_count, moving_position : natural := 0;
  signal pattern_index : std_logic_vector(31 downto 0);
  signal alpha_debug,gamma_debug : std_logic_vector(16*NUM_CHAINS-1 downto 0);
  signal shift_count_v,moving_position_v,beta_v : std_logic_vector(15 downto 0);
  signal mode_0,mode_1,mode_2,mode_3 : std_logic_vector(1 downto 0);
  signal alpha_0,gamma_0 : std_logic_vector(15 downto 0);
begin
  test_done<=finished;
  shift_count_v<=std_logic_vector(to_unsigned(shift_count,16));
  moving_position_v<=std_logic_vector(to_unsigned(moving_position,16));
  beta_v<=std_logic_vector(to_unsigned(BETA mod 65536,16));
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
    assert finished report "[FAIL] controller watchdog" severity failure; wait;
  end process;
  swap_dut: if APP=3 generate
    dut: entity work.swap_controller generic map(CHAIN_LENGTH,BETA,NUM_CHAINS)
      port map(clk,rst,scan_enable,mode_select,shift_count,pattern_done,pattern_index,alpha_debug,gamma_debug);
  end generate;
  moving_dut: if APP=4 generate
    dut: entity work.moving_controller generic map(CHAIN_LENGTH,BETA,NUM_CHAINS,INITIAL_POSITION)
      port map(clk,rst,scan_enable,mode_select,shift_count,pattern_done,pattern_index,moving_position,alpha_debug,gamma_debug);
  end generate;
  stimulus: process
    variable ref_pos,ref_pattern : natural := 0;
    variable t : timing_t;
    variable region_counts : nat_array(0 to NUM_CHAINS-1);
    variable visited : nat_array(0 to schedule_period(APP,CHAIN_LENGTH,BETA)-1) := (others=>0);
    procedure inspect is
    begin
      check(shift_count=ref_pos and to_integer(unsigned(pattern_index))=ref_pattern,"independent position/pattern counters");
      if APP=4 then
        check(moving_position=(ref_pattern+INITIAL_POSITION) mod schedule_period(APP,CHAIN_LENGTH,BETA),"MC04/MC07 unit movement/wrap");
      end if;
      for c in 0 to NUM_CHAINS-1 loop
        t:=reference_timing(APP,CHAIN_LENGTH,BETA,ref_pattern,c,INITIAL_POSITION);
        check(mode_select(2*c+1 downto 2*c)=reference_mode(t,ref_pos),"SC02..SC05 / MC02..MC03 pre-edge mode");
        check(to_integer(unsigned(alpha_debug(16*c+15 downto 16*c)))=t.a and
              to_integer(unsigned(gamma_debug(16*c+15 downto 16*c)))=t.g,"alpha/gamma identity and per-chain placement");
        check(t.a+t.b+t.g=CHAIN_LENGTH and t.a>=14 and t.g>=14,"length conservation");
      end loop;
    end;
  begin
    wait until rising_edge(clk); wait for 100 ps;
    inspect; check(pattern_done='0',"SC01/MC01 reset");
    report "[PASS] " & name_of(APP) & " SC01/MC01 reset and initial region";
    rst<='0'; scan_enable<='1';
    for p in 0 to 255 loop
      region_counts:=(others=>0);
      visited((p+INITIAL_POSITION) mod visited'length):=visited((p+INITIAL_POSITION) mod visited'length)+1;
      for s in 0 to CHAIN_LENGTH-1 loop
        inspect;
        for c in 0 to NUM_CHAINS-1 loop
          if mode_select(2*c+1 downto 2*c)="11" then region_counts(c):=region_counts(c)+1; end if;
        end loop;
        if p=0 and (s=0 or s=14 or s=CHAIN_LENGTH/2) then
          scan_enable<='0';
          for pause in 1 to 3 loop
            wait until rising_edge(clk); wait for 100 ps; inspect;
            check(pattern_done='0',"pause does not create completion");
          end loop;
          scan_enable<='1';
        end if;
        wait until rising_edge(clk); wait for 100 ps;
        if ref_pos=CHAIN_LENGTH-1 then
          ref_pos:=0; ref_pattern:=ref_pattern+1;
          check(pattern_done='1',"SC06/MC08 exact completion");
        else ref_pos:=ref_pos+1; check(pattern_done='0',"no early done"); end if;
        inspect;
      end loop;
      for c in 0 to NUM_CHAINS-1 loop check(region_counts(c)=BETA,"exact beta enabled shifts per chain"); end loop;
    end loop;
    for i in visited'range loop check(visited(i)>0,"MC14 entire legal movement cycle visited"); end loop;
    report "[PASS] SC02..SC09 / MC02..MC08 all modes, regions, odd/even patterns/chains, movement and wrap";
    report "[PASS] SC10..SC12/SC14/SC15 / MC09/MC11/MC12/MC14/MC15 pause, 256 patterns, no extra cycles";
    scan_enable<='0'; wait until rising_edge(clk); wait for 100 ps; inspect;
    check(pattern_done='0',"done clears on disabled clock");
    scan_enable<='1';
    for k in 1 to 5 loop wait until rising_edge(clk); wait for 100 ps; end loop;
    rst<='1'; wait for 100 ps; check(shift_count=5,"reset must be synchronous");
    wait until rising_edge(clk); wait for 100 ps;
    ref_pos:=0; ref_pattern:=0; inspect;
    check(pattern_done='0',"mid-pattern reset discards incomplete pattern");
    report "[PASS] SC11/MC10 synchronous mid-pattern reset";
    report "[UNIT_COMPLETE] " & name_of(APP) & " at " & time'image(now);
    finished<=true; wait;
  end process;
end architecture;
