library ieee;use ieee.std_logic_1164.all;
-- Connect unload_enable to accepted UNLOAD scan enable, never SHIFT enable.
-- Same-clock serial source is sampled before the bank shifts.
entity lbist_misr_top is
 port(clk,rst,unload_enable,response_bit,test_done:in std_logic;
 expected_signature:in std_logic_vector(15 downto 0);
 actual_signature:out std_logic_vector(15 downto 0);
 signature_valid,signature_match,fault_detected:out std_logic);
end;
architecture rtl of lbist_misr_top is signal s:std_logic_vector(15 downto 0);
begin
 actual_signature<=s;
 m:entity work.misr_16 port map(clk,rst,unload_enable,'0',response_bit,s);
 c:entity work.misr_signature_checker port map(test_done,s,expected_signature,signature_valid,signature_match,fault_detected);
end;
