library ieee;use ieee.std_logic_1164.all;use work.p_wires.all;
entity final_fpga_top is generic(DESIGN_CONFIG:natural:=2;CPU_VCO_MULT:positive:=10;CPU_CLK_DIVIDE:positive:=20);
 port(board_clk,reset_button:in std_logic;
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
architecture rtl of final_fpga_top is signal rst,clk,phi1,phi2,phi3:std_logic;
begin
 u_clock:entity work.final_clock_tree generic map(CPU_VCO_MULT,CPU_CLK_DIVIDE) port map(board_clk,reset_button,clk,phi1,phi2,phi3,rst);
 u_system:entity work.final_processor_system generic map(DESIGN_CONFIG) port map(
rst,clk,phi1,phi2,phi3,i_aVal,i_wait,i_addr,instr,d_aVal,d_wait,d_addr,data_inp,data_out,wr,b_sel,busFree,nmi,irq,i_busErr,d_busErr,start,pause,abort_test,fabric_idle,capture_ready,approach_select,expected_signature,external_test_mode,external_scan_enable,external_capture_enable,external_scan_in,external_phase,scan_out,scan_feedback,isolation_ack,protocol_error,test_done,error_status,signature_valid,signature_match,fault_detected,actual_signature);
end;
