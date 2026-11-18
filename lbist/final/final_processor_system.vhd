library ieee;use ieee.std_logic_1164.all;use ieee.numeric_std.all;
use work.p_wires.all;
-- Comparable processor boundary, with actual functional and tester interfaces.
-- DESIGN_CONFIG: 0 original core; 1 isolated scan core; 2 complete programmable LBIST.
-- All debug observation ports are OPEN. No fault-injection variant is instantiated.
entity final_processor_system is
 generic(DESIGN_CONFIG:natural:=2);
 port(rst,clk,phi1,phi2,phi3:in std_logic;
 i_aVal:out std_logic;i_wait:in std_logic;i_addr:out reg32;instr:in reg32;
 d_aVal:out std_logic;d_wait:in std_logic;d_addr:out reg32;data_inp:in reg32;
 data_out:out reg32;wr:out std_logic;b_sel:out reg4;busFree:out std_logic;
 nmi:in std_logic;irq:in reg6;i_busErr,d_busErr:in std_logic;
 start,pause,abort_test,fabric_idle,capture_ready:in std_logic;
 approach_select:in std_logic_vector(2 downto 0);expected_signature:in std_logic_vector(15 downto 0);
 external_test_mode,external_scan_enable,external_capture_enable,external_scan_in:in std_logic;
 external_phase:in std_logic_vector(2 downto 0);
 scan_out,scan_feedback,isolation_ack,protocol_error:out std_logic;
 test_done,error_status,signature_valid,signature_match,fault_detected:out std_logic;
 actual_signature:out std_logic_vector(15 downto 0));
end;
architecture rtl of final_processor_system is
 signal tm,se,ce,si,so,feedback,ack,pe,done,err,valid_config,unload:std_logic;
 signal phase:std_logic_vector(2 downto 0);signal pos,patterns:natural;
begin
 assert DESIGN_CONFIG<=2 report "Invalid final configuration" severity failure;
 baseline:if DESIGN_CONFIG=0 generate
  u_cpu:entity work.core port map(rst,clk,phi1,phi2,phi3,i_aVal,i_wait,i_addr,instr,d_aVal,d_wait,d_addr,data_inp,data_out,wr,b_sel,busFree,nmi,irq,i_busErr,d_busErr);
  scan_out<='0';scan_feedback<='0';isolation_ack<='0';protocol_error<='0';
  test_done<='0';error_status<='0';signature_valid<='0';signature_match<='0';fault_detected<='0';actual_signature<=(others=>'0');
 end generate;
 scan_cpu:if DESIGN_CONFIG/=0 generate
  u_cpu:entity work.core_scan_test port map(rst,clk,phi1,phi2,phi3,i_aVal,i_wait,i_addr,instr,
   d_aVal,d_wait,d_addr,data_inp,data_out,wr,b_sel,busFree,nmi,irq,i_busErr,d_busErr,
   se,si,so,feedback,tm,ce,fabric_idle,capture_ready,phase,ack,pe,
   open,open,open,open,open,open,open);
  scan_out<=so;scan_feedback<=feedback;isolation_ack<=ack;protocol_error<=pe;
 end generate;
 external_tester:if DESIGN_CONFIG=1 generate
  tm<=external_test_mode;se<=external_scan_enable;ce<=external_capture_enable;si<=external_scan_in;phase<=external_phase;
  test_done<='0';error_status<=pe;signature_valid<='0';signature_match<='0';fault_detected<='0';actual_signature<=(others=>'0');
 end generate;
 lbist:if DESIGN_CONFIG=2 generate
  signal controller_error,system_error,is_unload:std_logic;signal modes:std_logic_vector(1 downto 0);
 begin
  system_error<=controller_error or pe or not valid_config;
  u_ctrl:entity work.lbist_test_controller generic map(64,256)
   port map(clk,rst,start,pause,abort_test,ack,capture_ready,tm,se,ce,open,done,controller_error,phase,pos,patterns);
  is_unload<='1' when phase="100" else '0';unload<=se and is_unload;
  u_router:entity work.lbist_pattern_router generic map(20,16)
   port map(clk,rst,se,is_unload,feedback,approach_select,si,modes,open,open,valid_config);
  u_response:entity work.phase6a_safe_misr generic map(64,256)
   port map(clk,rst,unload,ce,so,done,system_error,phase,patterns,expected_signature,
    actual_signature,signature_valid,signature_match,fault_detected);
  test_done<=done;error_status<=system_error;
 end generate;
end;
