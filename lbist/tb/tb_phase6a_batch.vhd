library ieee;use ieee.std_logic_1164.all;
-- Independent real processors, memories, clocks, generators and scoreboards.
-- Sharing this simulator does not share any mutable DUT state or stimulus.
entity tb_phase6a_batch is
 generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2;
         FIRST_FAULT:natural:=1;LAST_FAULT:natural:=16);
 port(test_done:out boolean);
end;
architecture test of tb_phase6a_batch is
 type flags_t is array(FIRST_FAULT to LAST_FAULT) of boolean;
 signal completed:flags_t:=(others=>false);signal finished:boolean:=false;
begin
 test_done<=finished;
 instances:for fid in FIRST_FAULT to LAST_FAULT generate
  engine:entity work.phase6a_processor_check
   generic map(APPROACH=>APPROACH,BETA=>BETA,CONFIG_ID=>CONFIG_ID,FAULT_ID=>fid)
   port map(completed(fid));
 end generate;
 process(completed) variable all_done:boolean;
 begin
  all_done:=true;for fid in completed'range loop all_done:=all_done and completed(fid);end loop;
  finished<=all_done;
 end process;
 process begin wait until finished for 20 ms;
  assert finished report "[FAIL] independent replica watchdog" severity failure;
  report "[TB_COMPLETE] tb_phase6a_batch at "&time'image(now);wait;
 end process;
end;
