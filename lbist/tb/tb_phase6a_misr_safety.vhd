library ieee;use ieee.std_logic_1164.all;use ieee.numeric_std.all;
entity tb_phase6a_misr_safety is port(test_done:out boolean);end;
architecture test of tb_phase6a_misr_safety is
 signal clk:std_logic:='0';signal rst,start,pause,abort_test:std_logic:='0';
 signal tm,se,ce,pd,done,err,valid,match,detected,unload,response:std_logic;
 signal phase:std_logic_vector(2 downto 0);signal pos,patterns:natural;
 signal q:std_logic_vector(15 downto 0);signal finished:boolean:=false;signal scenario_id:natural:=0;
 signal scenario:std_logic_vector(3 downto 0);
 signal pattern_index:std_logic_vector(15 downto 0);
begin
 test_done<=finished;
 scenario<=std_logic_vector(to_unsigned(scenario_id,4));
 pattern_index<=std_logic_vector(to_unsigned(patterns,16));
 process begin while not finished loop clk<='0';wait for 5 ns;clk<='1';wait for 5 ns;end loop;wait;end process;
 c:entity work.lbist_test_controller generic map(4,2)
 port map(clk,rst,start,pause,abort_test,'1','1',tm,se,ce,pd,done,err,phase,pos,patterns);
 unload<=se when phase="100" and not(scenario_id=4 and pos=0 and patterns=0) else '0';
 response<='1' when scenario_id=7 else '0';
 a:entity work.phase6a_safe_misr generic map(4,2)
 port map(clk,rst,unload,ce,response,done,err,phase,patterns,x"0000",q,valid,match,detected);
 process
 procedure tick is begin wait until rising_edge(clk);wait for 1 ns;wait until falling_edge(clk);wait for 100 ps;end;
 begin
 for k in 0 to 7 loop
  scenario_id<=k;rst<='0';start<='0';abort_test<='0';wait for 2 ns;
  assert valid='0' and match='0' and detected='0' report "[FAIL] reset invalidation" severity failure;
  tick;rst<='1';tick;start<='1';tick;start<='0';
  if k>=1 and k<=3 then
   while phase/="010" loop tick;end loop;
   if k=2 then while phase/="011" loop tick;end loop;end if;
   if k=3 then while phase/="100" loop tick;end loop;end if;
   abort_test<='1';tick;abort_test<='0';
  elsif k=5 then
   while phase/="010" loop tick;end loop;start<='1';tick;start<='0';
  elsif k=6 then
   while phase/="100" loop tick;end loop;rst<='0';wait for 1 ns;
   assert valid='0' report "[FAIL] midway reset" severity failure;
  end if;
  if k/=6 then
   while done/='1' loop
    assert valid='0' and match='0' and detected='0' report "[FAIL] premature result" severity failure;tick;
   end loop;
   if k=0 then assert valid='1' and match='1' and detected='0' report "[FAIL] normal completion" severity failure;
   elsif k=7 then assert valid='1' and match='0' and detected='1' report "[FAIL] completed faulty response" severity failure;
   else assert valid='0' and match='0' and detected='0' report "[FAIL] invalid stream accepted" severity failure;end if;
  end if;
  report "[SAFETY] "&integer'image(k)&",PASS";
 end loop;
 report "[TB_COMPLETE] tb_phase6a_misr_safety at "&time'image(now);finished<=true;wait;
 end process;
 process begin wait until finished for 20 ms;assert finished report "[FAIL] watchdog" severity failure;wait;end process;
end;
