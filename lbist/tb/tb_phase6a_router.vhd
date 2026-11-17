library ieee;use ieee.std_logic_1164.all;use ieee.numeric_std.all;
use work.phase2_tb_pkg.all;use work.p_WIRES.all;
entity tb_phase6a_router is port(test_done:out boolean);end;
architecture test of tb_phase6a_router is
 signal clk:std_logic:='0';signal rst,scan_enable,is_unload:std_logic:='0';
 signal approach_select:std_logic_vector(2 downto 0):="000";
 signal scan_in,scan_out,scan_feedback,router_valid:std_logic;
 signal mode_select:std_logic_vector(1 downto 0);
 signal generator_state:std_logic_vector(15 downto 0);
 signal pc,instr:reg32;signal scan_state:std_logic_vector(63 downto 0);
 signal position:natural;signal finished:boolean:=false;
begin
 test_done<=finished;scan_state<=pc&instr;
 process begin while not finished loop clk<='0';wait for 5 ns;clk<='1';wait for 5 ns;end loop;wait;end process;
 r:entity work.lbist_pattern_router port map(clk,rst,scan_enable,is_unload,scan_feedback,approach_select,scan_in,mode_select,generator_state,position,router_valid);
 bank:entity work.reg_IF_RF_scan port map(clk,rst,'1',x"00000000",pc,x"00000000",instr,scan_enable,scan_in,scan_out,scan_feedback);
 process
 constant seq:bit_sequence:=sequence_model(x"AAAA");
 variable q:std_logic_vector(63 downto 0);variable md:std_logic_vector(1 downto 0);
 variable g,p,k:natural;variable bitn:std_logic;
 procedure edge is begin wait until rising_edge(clk);wait for 200 ps;wait until falling_edge(clk);wait for 200 ps;end;
 begin
 for a in 0 to 4 loop
  rst<='0';scan_enable<='0';approach_select<=std_logic_vector(to_unsigned(a,3));is_unload<='0';q:=(others=>'0');edge;edge;
  rst<='1';wait for 200 ps;
  for ord in 0 to 36*128-1 loop
   p:=ord/128;k:=ord mod 64;
   if ord mod 128>=64 then is_unload<='1';else is_unload<='0';end if;
   scan_enable<='1';wait for 200 ps;g:=22;
   if a=3 then if p mod 2=0 then g:=32;else g:=16;end if;
   elsif a=4 then g:=14+p mod 17;end if;
   md:="00";
   if a=0 or (a=2 and k>=g and k<g+20) or (a=3 and k>=g and k<g+16) or (a=4 and k>=g and k<g+20) then md:="11";end if;
   check(router_valid='1' and mode_select=md,"router pre-edge physical schedule and both lanes");
   check(generator_state=window(seq,ord),"router LFSR clock enable");
   bitn:=filtered(seq(ord),seq(ord+1),seq(ord+2),q(0),md);
   check(scan_feedback=q(0) and scan_out=q(63) and scan_in=bitn,"real IF/RF feedback and routed input");
   q:=q(62 downto 0)&bitn;edge;check(scan_state=q,"all real bank scan FFs");
  end loop;
  report "[ROUTER] "&integer'image(a)&",36,4608,PASS";
 end loop;
 scan_enable<='0';
 for a in 5 to 7 loop
  approach_select<=std_logic_vector(to_unsigned(a,3));wait for 1 ns;
  check(router_valid='0' and scan_in='0',"invalid approach rejected");
 end loop;
 report "[TB_COMPLETE] tb_phase6a_router at "&time'image(now);finished<=true;wait;
 end process;
 process begin wait until finished for 20 ms;assert finished report "[FAIL] router watchdog" severity failure;wait;end process;
end;
