library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;
entity tb_basic_controller is
  generic (CHAIN_LENGTH : positive := 64; BETA : natural := 20);
end entity;
architecture test of tb_basic_controller is
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
  stimulus: process
    variable position,low_first,high_count,low_last : natural := 0;
    variable before_mode : std_logic_vector(1 downto 0);
  begin
    wait until rising_edge(clk); wait for 100 ps;
    check(count=0 and mode="00" and done='0',"BC01 synchronous reset");
    report "[PASS] BC01 Reset";
    rst<='0'; scan_enable<='1';
    for pattern in 1 to 256 loop
      low_first:=0; high_count:=0; low_last:=0;
      for step in 0 to CHAIN_LENGTH-1 loop
        check(position=step and count=position and mode=reference_mode(position),"BC02..BC05 pre-edge mode/independent counter");
        if step<ALPHA then low_first:=low_first+1;
        elsif step<CHAIN_LENGTH-ALPHA then high_count:=high_count+1;
        else low_last:=low_last+1; end if;
        if pattern=1 and (step=ALPHA or step=CHAIN_LENGTH-ALPHA or step=0) then
          scan_enable<='0'; before_mode:=mode;
          for pause in 1 to 3 loop
            wait until rising_edge(clk); wait for 100 ps;
            check(count=position and mode=before_mode and done='0',"BC08 paused boundary and pulse clear");
          end loop;
          scan_enable<='1';
        end if;
        wait until rising_edge(clk); wait for 100 ps;
        position:=(position+1) mod CHAIN_LENGTH;
        check(count=position and mode=reference_mode(position),"BC07/BC12 rollover and combinational next mode");
        if step=CHAIN_LENGTH-1 then check(done='1',"BC06 completion edge");
        else check(done='0',"BC06 no early completion"); end if;
      end loop;
      check(low_first=ALPHA and high_count=BETA and low_last=ALPHA,"BC02/BC04 exact region lengths");
    end loop;
    report "[PASS] BC02 First low region; BC03 first boundary; BC04 high region; BC05 second boundary";
    report "[PASS] BC06 exact completion; BC07 rollover; BC08 pause/resume; BC09 256 consecutive patterns";
    -- A completion pulse clears on the next disabled edge, even while count holds.
    scan_enable<='0'; wait until rising_edge(clk); wait for 100 ps;
    check(count=0 and done='0',"BC08 completion pulse not stretched across pause");
    scan_enable<='1';
    for step in 1 to 5 loop wait until rising_edge(clk); wait for 100 ps; end loop;
    rst<='1'; wait for 100 ps;
    check(count=5,"BC10 reset must not take effect asynchronously");
    wait until rising_edge(clk); wait for 100 ps;
    check(count=0 and mode="00" and done='0',"BC10 mid-pattern reset");
    rst<='0'; wait until rising_edge(clk); wait for 100 ps;
    check(count=1 and mode=reference_mode(1),"BC10 restart from first position");
    report "[PASS] BC10 synchronous mid-pattern reset; BC11 legal boundary configuration; BC12 no latency or extra cycles";
    report "[CONTROLLER] " & integer'image(CHAIN_LENGTH) & "," & integer'image(ALPHA) & "," & integer'image(BETA) & "," & integer'image(ALPHA) & ",256," & integer'image(256*CHAIN_LENGTH);
    report "[TB_COMPLETE] tb_basic_controller at " & time'image(now);
    test_done<=true; wait;
  end process;
end architecture;
