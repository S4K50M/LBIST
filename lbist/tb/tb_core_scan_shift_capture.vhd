library ieee;
use ieee.std_logic_1164.all;
entity tb_core_scan_shift_capture is
  generic(PATTERNS : positive:=256; ENTRY_NS : positive:=380);
end entity;
architecture test of tb_core_scan_shift_capture is
  signal test_done : boolean:=false;
begin
  engine: entity work.phase5a_processor_check generic map(PATTERNS,ENTRY_NS,false) port map(test_done);
  process begin
    wait until test_done;
    report "[TB_COMPLETE] tb_core_scan_shift_capture at "&time'image(now);wait;
  end process;
end architecture;
