library ieee;
use ieee.std_logic_1164.all;
entity tb_moving_integration is
  generic(CHAIN_LENGTH:positive:=64; BETA:natural:=16; NUM_CHAINS:positive:=4; PATTERNS:positive:=1024);
end;
architecture test of tb_moving_integration is
  signal test_done : boolean := false;
begin
  engine: entity work.phase3_integration_check generic map(4,CHAIN_LENGTH,BETA,NUM_CHAINS,PATTERNS) port map(test_done);
  completion: process
  begin
    wait until test_done for 20 ms;
    assert test_done report "[FAIL] integration wrapper watchdog" severity failure;
    report "[TB_COMPLETE] tb_moving_integration at " & time'image(now); wait;
  end process;
end;
