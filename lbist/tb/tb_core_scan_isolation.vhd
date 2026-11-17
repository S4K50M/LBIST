library ieee;
use ieee.std_logic_1164.all;
entity tb_core_scan_isolation is
end entity;
architecture test of tb_core_scan_isolation is
  signal test_done : boolean:=false;
begin
  engine: entity work.phase5a_processor_check generic map(8,380,true) port map(test_done);
  process begin
    wait until test_done;
    report "[TB_COMPLETE] tb_core_scan_isolation at "&time'image(now);wait;
  end process;
end architecture;
