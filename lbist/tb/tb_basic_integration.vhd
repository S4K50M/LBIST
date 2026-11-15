library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_basic_integration is
  generic (CHAIN_LENGTH : positive := 64; BETA : natural := 20);
end entity;
architecture test of tb_basic_integration is
  signal clk : std_logic := '0';
  signal rst : std_logic := '1';
  signal scan_enable : std_logic := '0';
  signal test_done : boolean := false;
  signal mode : std_logic_vector(1 downto 0);
  signal count : natural;
  signal done : std_logic;
  function low_length return natural is
  begin
    if BETA>CHAIN_LENGTH then return 0; end if;
    return (CHAIN_LENGTH-BETA)/2;
  end;
  constant ALPHA : natural := low_length;
  function reference_mode(position : natural) return std_logic_vector is
  begin
    if position<ALPHA then return "00";
    elsif position<CHAIN_LENGTH-ALPHA then return "11";
    else return "00"; end if;
  end;
  signal state : std_logic_vector(15 downto 0);
  signal c,f1,f2,raw,scan_in,valid : std_logic;
  signal active : std_logic_vector(1 downto 0);
  signal chain : std_logic_vector(CHAIN_LENGTH-1 downto 0) := (others=>'0');
begin
  clocking: process
  begin
    while not test_done loop
      wait for 1 ns;
      exit when test_done;
      clk<=not clk;
    end loop;
    wait;
  end process;
  watchdog: process
  begin
    wait until test_done for 5 ms;
    assert test_done report "[FAIL] watchdog timeout" severity failure;
    wait;
  end process;
  controller: entity work.basic_controller
    generic map(CHAIN_LENGTH,BETA)
    port map(clk,rst,scan_enable,mode,count,done);
  lfsr: entity work.lfsr_16 port map(clk,rst,scan_enable,raw,state);
  phases: entity work.phase_shifter port map(state,c,f1,f2);
  filter_unit: entity work.plpf_dynamic port map(c,f1,f2,chain(0),mode,scan_in,active,valid);
  scan_model: process(clk)
  begin
    if rising_edge(clk) then
      if rst='1' then chain<=(others=>'0');
      elsif scan_enable='1' then chain<=chain(CHAIN_LENGTH-2 downto 0)&scan_in; end if;
    end if;
  end process;
  stimulus: process
    constant seq : bit_sequence := sequence_model(x"AAAA");
    constant PATTERNS : positive := 1024;
    variable position,transitions,weighted,pattern_weight,pattern_sum,changes : natural := 0;
    variable expected,previous,initial_q : std_logic := '0';
    variable ref_chain,before_chain : std_logic_vector(CHAIN_LENGTH-1 downto 0) := (others=>'0');
    variable estimate,measured,error_pp,serial,activity : real;
    variable weight : natural;
    function tri(n : natural) return real is
    begin return real(n)*(real(n)+1.0)/2.0; end;
  begin
    check(PATTERNS*CHAIN_LENGTH<=65536,"reference sequence supports up to 65536 shifts");
    wait until rising_edge(clk); wait for 100 ps;
    check(count=0 and done='0' and state=x"AAAA" and chain=ref_chain,"integration reset alignment");
    rst<='0'; scan_enable<='1';
    for j in 0 to PATTERNS*CHAIN_LENGTH-1 loop
      position:=j mod CHAIN_LENGTH;
      if position=0 then initial_q:=ref_chain(0); end if;
      check(count=position and mode=reference_mode(position),"independent shift position and mode");
      check(state=window(seq,j),"no skipped or duplicated LFSR state");
      expected:=filtered(seq(j),seq(j+1),seq(j+2),ref_chain(0),reference_mode(position));
      check(valid='1' and scan_in=expected and active=mode,"actual input-stage feedback / combinational alignment");
      if j>0 and scan_in/=previous then transitions:=transitions+1; end if;
      previous:=scan_in;
      if scan_in/=ref_chain(0) then weighted:=weighted+CHAIN_LENGTH-position; end if;
      before_chain:=ref_chain;
      ref_chain:=ref_chain(CHAIN_LENGTH-2 downto 0)&expected;
      wait until rising_edge(clk); wait for 100 ps;
      check(chain=ref_chain and state=window(seq,j+1),"complete scan contents and one LFSR advancement");
      check(count=(j+1) mod CHAIN_LENGTH and mode=reference_mode((j+1) mod CHAIN_LENGTH),"controller rollover / next mode");
      for i in 0 to CHAIN_LENGTH-1 loop
        check(chain(i)='0' or chain(i)='1',"known scan bit");
        if chain(i)/=before_chain(i) then changes:=changes+1; end if;
      end loop;
      if position=CHAIN_LENGTH-1 then
        check(done='1',"full pattern completion pulse");
        pattern_weight:=0;
        if chain(CHAIN_LENGTH-1)/=initial_q then pattern_weight:=CHAIN_LENGTH; end if;
        for i in 1 to CHAIN_LENGTH-1 loop
          if chain(i-1)/=chain(i) then pattern_weight:=pattern_weight+i; end if;
        end loop;
        pattern_sum:=pattern_sum+pattern_weight;
        check(pattern_sum=weighted,"independent pattern-domain WTM orientation");
      else check(done='0',"no spurious completion"); end if;
      if j mod 1024=511 then
        scan_enable<='0';
        for pause in 1 to 3 loop
          wait until rising_edge(clk); wait for 100 ps;
          check(chain=ref_chain and state=window(seq,j+1) and count=(j+1) mod CHAIN_LENGTH and done='0',"integration pause preserves all state");
        end loop;
        scan_enable<='1';
      end if;
    end loop;
    scan_enable<='0';
    estimate:=((tri(ALPHA)+tri(CHAIN_LENGTH)-tri(ALPHA+BETA))/14.0+(tri(ALPHA+BETA)-tri(ALPHA))/2.0)/tri(CHAIN_LENGTH);
    check(abs(estimate-(1.0/14.0+(0.5-1.0/14.0)*real(BETA)/real(CHAIN_LENGTH)))<1.0e-12,"weighted/simplified theoretical WTM cross-check");
    measured:=real(weighted)/(real(PATTERNS)*tri(CHAIN_LENGTH));
    error_pp:=100.0*abs(measured-estimate);
    serial:=real(transitions)/real(PATTERNS*CHAIN_LENGTH-1);
    activity:=real(changes)/real(PATTERNS*CHAIN_LENGTH*CHAIN_LENGTH);
    -- 2 pp allows finite deterministic sampling AND stationary-rate model
    -- approximation at the two mode boundaries; never silently pass excess.
    check(error_pp<=2.0,"WTM error exceeds declared 2 percentage-point tolerance");
    report "[METRIC] " & integer'image(CHAIN_LENGTH) & "," & integer'image(ALPHA) & "," & integer'image(BETA) & "," & integer'image(ALPHA) & ",NA," & real'image(estimate) & "," & real'image(measured) & "," & real'image(error_pp) & "," & real'image(serial) & "," & real'image(activity) & "," & integer'image(PATTERNS) & "," & integer'image(PATTERNS*CHAIN_LENGTH) & "," & time'image(now);
    report "[PASS] 1024 patterns, every shift/mode/scan bit, no X/U, feedback, rollover, pause/resume";
    report "[PASS] independent WTM cross-check and 2 pp error limit; three metrics kept separate";
    report "[TB_COMPLETE] tb_basic_integration at " & time'image(now);
    test_done<=true; wait;
  end process;
end architecture;
