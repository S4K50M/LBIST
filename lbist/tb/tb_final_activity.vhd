library ieee;use ieee.std_logic_1164.all;
entity tb_final_activity is generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2);port(test_done:out boolean);end;
architecture test of tb_final_activity is signal finished:boolean:=false;begin
 engine:entity work.final_activity_check generic map(APPROACH=>APPROACH,BETA=>BETA,CONFIG_ID=>CONFIG_ID) port map(finished);
 process begin wait until finished;test_done<=true;report "[TB_COMPLETE] tb_final_activity at "&time'image(now);wait;end process;
end;
