library ieee;use ieee.std_logic_1164.all;
entity misr_signature_checker is
 port(done:in std_logic;actual_signature,expected_signature:in std_logic_vector(15 downto 0);
 signature_valid,signature_match,fault_detected:out std_logic);
end;
architecture rtl of misr_signature_checker is begin
 signature_valid<=done;
 signature_match<='1' when done='1' and actual_signature=expected_signature else '0';
 fault_detected<='1' when done='1' and actual_signature/=expected_signature else '0';
end;
