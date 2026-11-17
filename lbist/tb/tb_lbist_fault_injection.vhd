library ieee;use ieee.std_logic_1164.all;
entity tb_lbist_fault_injection is generic(FAULT_ID:natural:=0);port(test_done:out boolean);end;
architecture test of tb_lbist_fault_injection is signal done:boolean:=false;
begin
 engine:entity work.phase5bc_processor_check generic map(FAULT_ID=>FAULT_ID) port map(done);
 process begin wait until done;report "[TB_COMPLETE] tb_lbist_fault_injection at "&time'image(now);test_done<=true;wait;end process;
end;
