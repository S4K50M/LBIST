library ieee;use ieee.std_logic_1164.all;
entity tb_phase6a_controller_integration is generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2;FAULT_ID:natural:=0);port(test_done:out boolean);end;
architecture test of tb_phase6a_controller_integration is signal done:boolean:=false;begin
 engine:entity work.phase6a_processor_check generic map(APPROACH=>APPROACH,BETA=>BETA,CONFIG_ID=>CONFIG_ID,FAULT_ID=>FAULT_ID) port map(done);
 process begin wait until done;report "[TB_COMPLETE] tb_phase6a_controller_integration at "&time'image(now);test_done<=true;wait;end process;end;
