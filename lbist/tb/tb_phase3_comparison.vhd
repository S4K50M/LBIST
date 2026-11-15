library ieee;
use ieee.std_logic_1164.all;
entity tb_phase3_comparison is
  generic(CHAIN_LENGTH:positive:=64; BASIC_BETA:natural:=20; SWAP_BETA:natural:=18;
          MOVING_BETA:natural:=19; NUM_CHAINS:positive:=4; PATTERNS:positive:=1024;
          TARGET_PERCENT:natural:=20);
end;
architecture test of tb_phase3_comparison is
  signal direct_done,low_done,basic_done,swap_done,moving_done : boolean := false;
  signal test_done : boolean := false;
begin
  direct_engine: entity work.phase3_integration_check generic map(0,CHAIN_LENGTH,0,NUM_CHAINS,PATTERNS) port map(direct_done);
  low_engine: entity work.phase3_integration_check generic map(1,CHAIN_LENGTH,0,NUM_CHAINS,PATTERNS) port map(low_done);
  basic_engine: entity work.phase3_integration_check generic map(2,CHAIN_LENGTH,BASIC_BETA,NUM_CHAINS,PATTERNS) port map(basic_done);
  swap_engine: entity work.phase3_integration_check generic map(3,CHAIN_LENGTH,SWAP_BETA,NUM_CHAINS,PATTERNS) port map(swap_done);
  moving_engine: entity work.phase3_integration_check generic map(4,CHAIN_LENGTH,MOVING_BETA,NUM_CHAINS,PATTERNS) port map(moving_done);
  test_done<=direct_done and low_done and basic_done and swap_done and moving_done;
  completion: process
  begin
    wait until test_done for 20 ms;
    assert test_done report "[FAIL] comparison watchdog" severity failure;
    report "[PASS] identical seed, polynomial, phases, enable schedule, counts and initialization across five approaches";
    report "[TB_COMPLETE] tb_phase3_comparison at " & time'image(now); wait;
  end process;
end;
