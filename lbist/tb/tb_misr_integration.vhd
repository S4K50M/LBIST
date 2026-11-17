library ieee;use ieee.std_logic_1164.all;
entity tb_misr_integration is generic(FAULT_ID:natural:=0);port(test_done:out boolean);end;
architecture test of tb_misr_integration is signal done:boolean:=false;
begin
 engine:entity work.phase5bc_processor_check generic map(FAULT_ID=>FAULT_ID) port map(done);
 process begin wait until done;report "[TB_COMPLETE] tb_misr_integration at "&time'image(now);test_done<=true;wait;end process;
end;
