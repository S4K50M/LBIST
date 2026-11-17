library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
use work.phase2_tb_pkg.all;
entity tb_lbist_test_controller is
  generic(LENGTH : positive:=64; PATTERNS : positive:=256);
end entity;
architecture test of tb_lbist_test_controller is
  signal clk : std_logic:='0';
  signal rst : std_logic:='0';
  signal start,pause,abort_test,ack,ready : std_logic:='0';
  signal tm,se,ce,pd,done,error_status : std_logic;
  signal state : std_logic_vector(2 downto 0);
  signal count,patterns_done : natural;
  signal shift_count_v,pattern_index : std_logic_vector(15 downto 0);
  signal test_done : boolean:=false;
begin
  dut: entity work.lbist_test_controller generic map(LENGTH,PATTERNS)
    port map(clk,rst,start,pause,abort_test,ack,ready,tm,se,ce,pd,done,error_status,state,count,patterns_done);
  shift_count_v<=std_logic_vector(to_unsigned(count,16));
  pattern_index<=std_logic_vector(to_unsigned(patterns_done,16));
  clocking: process begin
    while not test_done loop wait for 1 ns;exit when test_done;clk<=not clk;end loop;wait;
  end process;
  watchdog: process begin wait until test_done for 20 ms;check(test_done,"FSM watchdog");wait;end process;
  stimulus: process
    variable rs,rpos,rpatterns,shifts,captures,unloads : natural:=0;
    variable old_state : natural;
    procedure inspect is begin
      check(to_integer(unsigned(state))=rs and count=rpos and patterns_done=rpatterns,"independent FSM/counter model");
      check(tm=BOOL2SL(rs/=0) and done=BOOL2SL(rs=5),"mode and completion");
      check(se=BOOL2SL((rs=2 or rs=4) and pause='0' and abort_test='0' and start='0'),"scan phase and pause qualification");
      check(ce=BOOL2SL(rs=3 and pause='0' and abort_test='0' and start='0' and ready='1'),"single capture qualification");
    end;
    procedure edge is begin
      inspect;old_state:=rs;
      if pause='0' then
        case rs is
          when 0 => if start='1' then rs:=1;end if;
          when 1 => if ack='1' then rs:=2;end if;
          when 2 | 4 =>
            if rs=2 then shifts:=shifts+1;else unloads:=unloads+1;end if;
            if rpos=LENGTH-1 then
              rpos:=0;
              if rs=2 then rs:=3;
              else rpatterns:=rpatterns+1;if rpatterns=PATTERNS then rs:=5;else rs:=2;end if;end if;
            else rpos:=rpos+1;end if;
          when 3 => if ready='1' then captures:=captures+1;rs:=4;end if;
          when others => null;
        end case;
      end if;
      wait until rising_edge(clk);wait for 100 ps;inspect;
      check(pd=BOOL2SL(old_state=4 and pause='0' and rpos=0),"pattern pulse only at last unload edge");
      wait until falling_edge(clk);wait for 100 ps;
    end;
  begin
    wait until falling_edge(clk);wait for 100 ps;inspect;rst<='1';ready<='1';start<='1';wait for 100 ps;edge;
    start<='0';wait for 100 ps;
    for k in 1 to 3 loop edge;end loop;
    ack<='1';wait for 100 ps;edge;
    while rs/=5 loop
      if rpatterns=0 and rpos=0 and rs=2 then
        pause<='1';wait for 100 ps;for k in 1 to 3 loop edge;end loop;pause<='0';wait for 100 ps;
      end if;
      if rpatterns=0 and rs=3 then
        ready<='0';wait for 100 ps;for k in 1 to 3 loop edge;end loop;ready<='1';wait for 100 ps;
      end if;
      if rpatterns=0 and rpos=0 and rs=4 then
        pause<='1';wait for 100 ps;for k in 1 to 2 loop edge;end loop;
        pause<='0';wait for 100 ps;
      end if;
      edge;
    end loop;
    check(shifts=PATTERNS*LENGTH and unloads=shifts and captures=PATTERNS,"exact shift/capture/unload totals");
    report "[PASS] independent FSM, handshakes, exact counts, pause, capture wait, all patterns";
    report "[SEQUENCE] "&integer'image(shifts)&","&integer'image(captures)&","&integer'image(unloads)&","&integer'image(rpatterns);
    -- Sticky DONE, asynchronous reset, abort, illegal restart and mid-SHIFT reset.
    edge;rst<='0';wait for 100 ps;check(state="000" and tm='0',"asynchronous controller reset");
    rst<='1';start<='1';wait until rising_edge(clk);wait until falling_edge(clk);start<='0';
    wait until rising_edge(clk);wait until falling_edge(clk);abort_test<='1';
    wait until rising_edge(clk);wait for 100 ps;
    check(done='1' and error_status='1' and se='0' and ce='0',"early abort fails closed");
    rst<='0';abort_test<='0';wait for 100 ps;rst<='1';start<='1';
    wait until rising_edge(clk);wait until falling_edge(clk);
    wait until rising_edge(clk);wait for 100 ps;
    check(done='1' and error_status='1',"illegal repeated start fails closed");
    rst<='0';start<='0';wait for 100 ps;check(state="000","reset returns NORMAL");
    rst<='1';start<='1';wait until rising_edge(clk);wait until falling_edge(clk);start<='0';
    wait until rising_edge(clk);wait until falling_edge(clk);
    wait until rising_edge(clk);wait for 100 ps;
    check(state/="000" and state/="101","reset exercised during a live pattern");
    rst<='0';wait for 100 ps;check(state="000" and count=0 and patterns_done=0,"mid-pattern asynchronous reset");
    report "[PASS] DONE hold, abort, illegal restart and mid-test reset";
    report "[TB_COMPLETE] tb_lbist_test_controller at "&time'image(now);
    test_done<=true;wait;
  end process;
end architecture;
