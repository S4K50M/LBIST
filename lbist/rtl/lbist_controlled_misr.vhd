library ieee;use ieee.std_logic_1164.all;
-- Production control/analysis boundary. Connect response_bit to real CPU
-- scan_out and acknowledge entry only after all processor hold domains agree.
entity lbist_controlled_misr is
 generic(CHAIN_LENGTH:positive:=64;NUM_PATTERNS:positive:=256);
 port(clk,rst,start,pause,abort_test,isolation_ack,capture_ready,response_bit:in std_logic;
 expected_signature:in std_logic_vector(15 downto 0);
 test_mode,scan_enable,capture_enable,pattern_done,test_done,error_status:out std_logic;
 current_state:out std_logic_vector(2 downto 0);shift_count,pattern_count:out natural;
 actual_signature:out std_logic_vector(15 downto 0);
 signature_valid,signature_match,fault_detected:out std_logic);
end;
architecture rtl of lbist_controlled_misr is
 signal se,done,unload:std_logic;signal phase:std_logic_vector(2 downto 0);
begin
 scan_enable<=se;test_done<=done;current_state<=phase;
 unload<=se when phase="100" else '0';
 controller:entity work.lbist_test_controller generic map(CHAIN_LENGTH,NUM_PATTERNS)
  port map(clk,rst,start,pause,abort_test,isolation_ack,capture_ready,test_mode,se,capture_enable,
   pattern_done,done,error_status,phase,shift_count,pattern_count);
 analyzer:entity work.lbist_misr_top
  port map(clk,rst,unload,response_bit,done,expected_signature,actual_signature,
   signature_valid,signature_match,fault_detected);
end;
