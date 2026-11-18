"""Only final gluing/verification sources; prior RTL is never rewritten."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def put(path,s):
 p=R/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def build():
 system=(R/"lbist/final/final_processor_system.vhd").read_text()
 port=system[system.index(" port("):system.index("end;\narchitecture")]
 port=port.replace("rst,clk,phi1,phi2,phi3:in std_logic;","board_clk,reset_button:in std_logic;")
 names="rst clk phi1 phi2 phi3 i_aVal i_wait i_addr instr d_aVal d_wait d_addr data_inp data_out wr b_sel busFree nmi irq i_busErr d_busErr start pause abort_test fabric_idle capture_ready approach_select expected_signature external_test_mode external_scan_enable external_capture_enable external_scan_in external_phase scan_out scan_feedback isolation_ack protocol_error test_done error_status signature_valid signature_match fault_detected actual_signature".split()
 put("lbist/final/final_fpga_top.vhd","library ieee;use ieee.std_logic_1164.all;use work.p_wires.all;\nentity final_fpga_top is generic(DESIGN_CONFIG:natural:=2;CPU_VCO_MULT:positive:=10;CPU_CLK_DIVIDE:positive:=20);\n"+port+"""
end;
architecture rtl of final_fpga_top is signal rst,clk,phi1,phi2,phi3:std_logic;
begin
 u_clock:entity work.final_clock_tree generic map(CPU_VCO_MULT,CPU_CLK_DIVIDE) port map(board_clk,reset_button,clk,phi1,phi2,phi3,rst);
 u_system:entity work.final_processor_system generic map(DESIGN_CONFIG) port map(
"""+",".join(names)+");\nend;\n")
 # Exact production router generics, including its unselected scheduling lanes.
 eng=(R/"lbist/tb/phase6a_processor_check.vhd").read_text().replace("phase6a_processor_check","final_activity_check")
 eng=eng.replace("generic map(BETA,SWAP_SAFE)","generic map(20,16)")
 at=eng.index("begin\n  misr_enable")
 extra="""  signal prod_ia,prod_da,prod_wr,prod_busfree,prod_so,prod_fb,prod_ack,prod_pe,prod_done,prod_err,prod_valid,prod_match,prod_fault:std_logic;
  signal prod_i_addr,prod_d_addr,prod_data,prod_instruction,prod_input:reg32;
  signal prod_bsel:reg4;signal prod_signature:std_logic_vector(15 downto 0);
"""
 assert at>=0;eng=eng[:at]+extra+eng[at:]
 at=eng.index("  clocking:")
 prod="""  prod_instruction<=rom_word(program,prod_i_addr);
  prod_input<=ram(to_integer(unsigned(prod_d_addr(11 downto 2)))) when not is_x(prod_d_addr) else (others=>'0');
  system_copy:entity work.final_processor_system generic map(2)
   port map(rst,clk,phi1,phi2,phi3,prod_ia,'1',prod_i_addr,prod_instruction,prod_da,'1',prod_d_addr,prod_input,
    prod_data,prod_wr,prod_bsel,prod_busfree,nmi,irq,bus_error,bus_error,start,pause,abort_test,fabric_idle,capture_ready,
    std_logic_vector(to_unsigned(APPROACH,3)),work.phase6a_golden_pkg.GOLDENS(CONFIG_ID),
    '0','0','0','0',"000",prod_so,prod_fb,prod_ack,prod_pe,prod_done,prod_err,prod_valid,prod_match,prod_fault,prod_signature);
  production_equivalence:process
  begin
   wait on clk,phi1,phi2,phi3;wait for 100 ps;
   if rst='1' then
    check(prod_i_addr=i_addr and prod_d_addr=d_addr and prod_data=data_out and prod_wr=wr and prod_ia=i_aval and prod_da=d_aval and prod_bsel=bsel,"production functional interface");
    check(prod_so=scan_out and prod_fb=scan_feedback and prod_ack=isolation_ack,"production real scan interface");
    check(prod_signature=signature and prod_valid=signature_valid and prod_match=signature_match and prod_fault=fault_detected,"production MISR and completion safety");
   end if;
  end process;
"""
 eng=eng[:at]+prod+eng[at:]
 # The reference deliberately attempts a raw test-mode drop. Production exposes
 # only the controlled host interface and remains isolated until reset. Its
 # functional/scan/MISR outputs are compared; the raw protocol flags can differ.
 put("lbist/tb/final_activity_check.vhd",eng)
 put("lbist/tb/tb_final_activity.vhd","""library ieee;use ieee.std_logic_1164.all;
entity tb_final_activity is generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2);port(test_done:out boolean);end;
architecture test of tb_final_activity is signal finished:boolean:=false;begin
 engine:entity work.final_activity_check generic map(APPROACH=>APPROACH,BETA=>BETA,CONFIG_ID=>CONFIG_ID) port map(finished);
 process begin wait until finished;test_done<=true;report "[TB_COMPLETE] tb_final_activity at "&time'image(now);wait;end process;
end;
""")
 functional=(R/'lbist/tb/tb_core_fault_regression.vhd').read_text()
 functional=functional.replace('tb_core_fault_regression','tb_final_functional_activity').replace('entity work.core_scan_fault','entity work.core_scan_test')
 functional=functional.replace('"000",open,open,open,open,open,open,open,open,open);','"000",open,open,open,open,open,open,open);')
 put('lbist/tb/tb_final_functional_activity.vhd',functional)
 print("Final production top and exact-router activity/equivalence fixture generated.")
if __name__=="__main__":build()
