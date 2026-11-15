library ieee;
use ieee.std_logic_1164.all;
entity tb_swap_controller is
  generic(CHAIN_LENGTH:positive:=64; BETA:natural:=16; NUM_CHAINS:positive:=4; INITIAL_POSITION:natural:=0);
end;
architecture test of tb_swap_controller is
  signal test_done : boolean := false;
begin
  engine: entity work.phase3_controller_check generic map(3,CHAIN_LENGTH,BETA,NUM_CHAINS,INITIAL_POSITION) port map(test_done);
  completion: process
  begin
    wait until test_done for 20 ms;
    assert test_done report "[FAIL] wrapper watchdog" severity failure;
    report "[TB_COMPLETE] tb_swap_controller at " & time'image(now); wait;
  end process;
end;
