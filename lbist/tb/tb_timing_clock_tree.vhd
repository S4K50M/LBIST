library ieee;use ieee.std_logic_1164.all;
entity tb_timing_clock_tree is generic(M:positive:=8;D:positive:=82);port(test_done:out boolean);end;
architecture test of tb_timing_clock_tree is
 signal board_clk:std_logic:='0';signal button:std_logic:='1';
 signal clk,phi1,phi2,phi3,rst:std_logic;
 constant T:time:=10 ns*D/M;
begin
 board_clk<=not board_clk after 5 ns;
 dut:entity work.final_clock_tree generic map(M,D) port map(board_clk,button,clk,phi1,phi2,phi3,rst);
 process variable previous:time;begin
  test_done<=false;wait for 100 ns;button<='0';wait until rst='1';
  wait until rising_edge(clk);previous:=now;
  for k in 1 to 4 loop
   wait until rising_edge(clk);assert abs(now-previous-T)<=2 ps report "[FAIL] MMCM period (1ps simulator quantization)" severity failure;previous:=now;
   wait for 100 ps;assert phi1='0' and phi2='1' and phi3='0' report "[FAIL] phase at main rising edge" severity failure;
   wait for T/4;assert phi2='0' and phi3='1' report "[FAIL] phi2 pulse/phi3 phase" severity failure;
   wait for T/4;assert clk='0' and phi1='0' and phi3='0' report "[FAIL] main falling edge" severity failure;
   wait for T/4;assert phi1='1' report "[FAIL] phi1 phase" severity failure;
  end loop;
  report "[PASS] actual UNISIM MMCM period, duty cycles and all relative phases";
  report "[TB_COMPLETE] tb_timing_clock_tree at "&time'image(now);test_done<=true;wait;
 end process;
 process begin wait for 1 ms;assert test_done report "[FAIL] MMCM lock watchdog" severity failure;wait;end process;
end;
