library ieee;use ieee.std_logic_1164.all;
-- Port-compatible replacement for the historical lbist_controlled_misr.
entity phase6a_controlled_misr is
 generic(CHAIN_LENGTH:positive:=64;NUM_PATTERNS:positive:=256);
 port(clk,rst,start,pause,abort_test,isolation_ack,capture_ready,response_bit:in std_logic;
 expected_signature:in std_logic_vector(15 downto 0);
 test_mode,scan_enable,capture_enable,pattern_done,test_done,error_status:out std_logic;
 current_state:out std_logic_vector(2 downto 0);shift_count,pattern_count:out natural;
 actual_signature:out std_logic_vector(15 downto 0);
 signature_valid,signature_match,fault_detected:out std_logic);
end;
architecture rtl of phase6a_controlled_misr is
 signal se,ce,done,err,unload:std_logic;signal phase:std_logic_vector(2 downto 0);
 signal patterns:natural;
begin
 scan_enable<=se;capture_enable<=ce;test_done<=done;error_status<=err;
 current_state<=phase;pattern_count<=patterns;
 unload<=se when phase="100" else '0';
 c:entity work.lbist_test_controller generic map(CHAIN_LENGTH,NUM_PATTERNS)
 port map(clk,rst,start,pause,abort_test,isolation_ack,capture_ready,test_mode,se,ce,
 pattern_done,done,err,phase,shift_count,patterns);
 m:entity work.phase6a_safe_misr generic map(CHAIN_LENGTH,NUM_PATTERNS)
 port map(clk,rst,unload,ce,response_bit,done,err,phase,patterns,expected_signature,
 actual_signature,signature_valid,signature_match,fault_detected);
end;
