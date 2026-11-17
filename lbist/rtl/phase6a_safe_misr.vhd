library ieee;use ieee.std_logic_1164.all;
entity phase6a_safe_misr is
 generic(CHAIN_LENGTH:positive:=64;NUM_PATTERNS:positive:=256);
 port(clk,rst,unload_enable,capture_enable,response_bit,test_done,error_status:in std_logic;
 phase:in std_logic_vector(2 downto 0);completed_patterns:in natural;
 expected_signature:in std_logic_vector(15 downto 0);
 signature:out std_logic_vector(15 downto 0);
 signature_valid,signature_match,fault_detected:out std_logic);
end;
architecture rtl of phase6a_safe_misr is
 signal caps:natural range 0 to NUM_PATTERNS:=0;
 signal bits:natural range 0 to NUM_PATTERNS*CHAIN_LENGTH:=0;
 signal position:natural range 0 to CHAIN_LENGTH:=0;
 signal patterns:natural range 0 to NUM_PATTERNS:=0;
 signal active,bad,en,valid:std_logic:='0';
 signal q:std_logic_vector(15 downto 0);
begin
 en<=unload_enable when phase="100" and error_status='0' else '0';
 m:entity work.misr_16 port map(clk,rst,en,'0',response_bit,q);
 signature<=q;
 valid<='1' when rst='1' and test_done='1' and error_status='0' and bad='0'
  and phase="101" and caps=NUM_PATTERNS and patterns=NUM_PATTERNS
  and completed_patterns=NUM_PATTERNS and bits=NUM_PATTERNS*CHAIN_LENGTH and active='0' else '0';
 signature_valid<=valid;
 signature_match<='1' when valid='1' and q=expected_signature else '0';
 fault_detected<='1' when valid='1' and q/=expected_signature else '0';
 process(clk,rst) begin
 if rst='0' then caps<=0;bits<=0;position<=0;patterns<=0;active<='0';bad<='0';
 elsif rising_edge(clk) then
  if error_status='1' then bad<='1';end if;
  if capture_enable='1' then
   if phase/="011" or active='1' or caps=NUM_PATTERNS then bad<='1';
   else caps<=caps+1;active<='1';position<=0;end if;
  end if;
  if unload_enable='1' then
   if phase/="100" or active='0' or bits=NUM_PATTERNS*CHAIN_LENGTH then bad<='1';
   else
    bits<=bits+1;
    if position=CHAIN_LENGTH-1 then
     position<=0;active<='0';
     if patterns<NUM_PATTERNS then patterns<=patterns+1;else bad<='1';end if;
    else position<=position+1;end if;
   end if;
  end if;
 end if;end process;
end;
