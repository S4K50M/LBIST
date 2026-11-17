"""New variants only. Two controller lanes preserve one schedule step per capture."""
from pathlib import Path
import csv,json,hashlib,subprocess
from phase3_wtm_optimizer import optimize
from fractions import Fraction
from misr_golden import responses
R=Path(__file__).resolve().parents[2];O=R/"Results/Phase6A"
def put(path,text):
 p=R/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("\n".join(l.rstrip() for l in text.splitlines())+"\n")
def mode(a,b,p,pos):
 if a==0:return 3
 if a==1:return 0
 g=(64-b)//2 if a==2 else (32 if p%2==0 else 32-b) if a==3 else 14+p%(37-b)
 return 3 if g<=pos<g+b else 0
def model(a,b,fid=0):
 q=0x2cae040000;s=0xaaaa;words=[];toggle=ff=weighted=last=0
 for p in range(256):
  for phase in range(2):
   for pos in range(64):
    md=mode(a,b,p,pos);bits=[(s>>i)&1 for i in range(3)]
    bit=bits[0] if md==3 or bits[0]==bits[1]==bits[2] else q&1
    new=((q<<1)|bit)&((1<<64)-1)
    if phase==0:
     diff=q^new;ff+=diff.bit_count();weighted+=sum(i+1 for i in range(64) if diff>>i&1)
     toggle+=bit^last;last=bit
    q=new;s=(s>>1)|((sum(s>>i&1 for i in [0,4,13,15])%2)<<15)
   if phase==0:
    operand=q>>32&0xfffffffc;instr=0x1460fffa
    if 1<=fid<=8:
     k=[2,3,16,31][(fid-1)//2];operand=(operand&~(1<<k))|((fid%2==0)<<k)
    if fid>=9:
     k=[0,1,16,31][(fid-9)//2];instr=(instr&~(1<<k))|((fid%2==0)<<k)
    q=(((operand+4)&0xffffffff)<<32)|instr;words.append(f"{q:016X}")
 return words,dict(MeasuredWTM=weighted/(256*64*2080),ScanFFSwitching=ff/(256*64*64),SerialToggleRate=toggle/(256*64))
def build():
 O.mkdir(parents=True,exist_ok=True);(O/"work").mkdir(exist_ok=True)
 snap=O/"work/protected.json"
 if not snap.exists():
  files=subprocess.check_output(["git","ls-tree","-r","--name-only","-z","40c9649"],cwd=R).decode().split("\0")
  snap.write_text(json.dumps({p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in files if p}))
 put("Results/Phase6A/.gitignore","work/\n*.vcd\n*.wdb\n*.jou\n/*.log\n.Xil/")
 configs=[dict(ID=i,Approach=a,Beta=b,Target="initial") for i,(a,b) in enumerate([(0,20),(1,20),(2,20),(3,16),(4,20)])]
 feasibility=[dict(Approach=name,Target=target,Beta="NA",EstimatedWTM=estimate,Feasible=False,Status="FIXED_REFERENCE",Config=cid)
   for cid,name,estimate in [(0,"direct",50.0),(1,"constant_n3",100/14)] for target in [10,15,20]]
 for a,name in [(2,"basic"),(3,"swap"),(4,"moving")]:
  for target in [10,15,20]:
   r=optimize(name,64,Fraction(target,100),1,True);b=r["Beta"]
   found=next((c for c in configs if c["Approach"]==a and c["Beta"]==b),None)
   if found is None and r["TargetFeasible"]:
    found=dict(ID=len(configs),Approach=a,Beta=b,Target=target);configs.append(found)
   feasibility.append(dict(Approach=name,Target=target,Beta=b,EstimatedWTM=float(Fraction(r["EstimatedWTM"]))*100,
     Feasible=r["TargetFeasible"],Status="IN_RANGE_QUANTIZED" if r["TargetFeasible"] else "INFEASIBLE",Config=found["ID"] if found else ""))
 (O/"configs.json").write_text(json.dumps(configs,indent=2))
 with (O/"feasibility.json").open("w") as f:json.dump(feasibility,f,indent=2)
 gold=[]
 for c in configs:gold.append(responses(model(c["Approach"],c["Beta"])[0])[-1])
 put("lbist/tb/phase6a_golden_pkg.vhd","library ieee;use ieee.std_logic_1164.all;\npackage phase6a_golden_pkg is\n"
  +"type signatures_t is array(natural range <>) of std_logic_vector(15 downto 0);\nconstant GOLDENS:signatures_t:=("
  +",".join(f'{i}=>x"{s:04X}"' for i,s in enumerate(gold))+");end;")
 eng=(R/"lbist/tb/phase5bc_processor_check.vhd").read_text().replace("phase5bc_processor_check","phase6a_processor_check")
 eng=eng.replace("generic(FAULT_ID","generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2;FAULT_ID")
 eng=eng.replace('  signal signature:',"  signal is_unload,router_valid:std_logic;\n  signal signature:")
 start=eng.index("  response_analyzer:");end=eng.index("  test_done",start)
 eng=eng[:start]+"""  response_analyzer:entity work.phase6a_safe_misr generic map(64,PATTERNS)
    port map(clk,rst,misr_enable,capture_enable,scan_out,done,error_status,test_phase,pattern_count,
      work.phase6a_golden_pkg.GOLDENS(CONFIG_ID),signature,signature_valid,signature_match,fault_detected);
"""+eng[end:]
 start=eng.index("  lfsr:");end=eng.index("  clocking:",start)
 eng=eng[:start]+"""  is_unload<='1' when test_phase="100" else '0';
  router:entity work.lbist_pattern_router generic map(BETA,BETA when APPROACH=3 else 16)
   port map(clk,rst,scan_enable,is_unload,scan_feedback,std_logic_vector(to_unsigned(APPROACH,3)),
    scan_in,mode_select,generator_state,basic_count,router_valid);
""".replace("BETA when APPROACH=3 else 16","SWAP_SAFE")+eng[end:]
 eng=eng.replace("architecture test of phase6a_processor_check is","architecture test of phase6a_processor_check is\n  function swap_beta return natural is begin if APPROACH=3 then return BETA;else return 16;end if;end;\n  constant SWAP_SAFE:natural:=swap_beta;")
 eng=eng.replace("    variable count_before : natural;","    variable count_before,gamma,logical_pattern : natural;")
 old='''        if source_index mod 64>=22 and source_index mod 64<42 then wanted_mode:="11";end if;'''
 new='''        logical_pattern:=source_index/128;
        gamma:=(64-BETA)/2;
        if APPROACH=3 then
          if logical_pattern mod 2=0 then gamma:=32;else gamma:=32-BETA;end if;
        elsif APPROACH=4 then gamma:=14+logical_pattern mod (37-BETA);end if;
        if APPROACH=0 then wanted_mode:="11";
        elsif APPROACH=1 then wanted_mode:="00";
        elsif source_index mod 64>=gamma and source_index mod 64<gamma+BETA then wanted_mode:="11";end if;'''
 assert old in eng;eng=eng.replace(old,new)
 eng=eng.replace("work.phase5bc_golden_pkg.GOLDEN_FINAL","work.phase6a_golden_pkg.GOLDENS(CONFIG_ID)")
 eng=eng.replace('report "[FINAL_SIGNATURE] "', 'report "[CONFIG] "&integer\'image(CONFIG_ID)&","&integer\'image(APPROACH)&","&integer\'image(BETA);\n    report "[FINAL_SIGNATURE] "')
 # Actual switching measurements before capture; per-pattern deltas independent of model.
 eng=eng.replace("variable fb:std_logic;","variable fb,last_in:std_logic:='0';\n    variable wtm,ffswitch,serialtoggles:natural:=0;\n    variable before_scan:std_logic_vector(63 downto 0);")
 eng=eng.replace("expected:=expected(62 downto 0)&value;", """before_scan:=expected;
        expected:=expected(62 downto 0)&value;
        if phase_before=2 then
          for j in 0 to 63 loop
            if before_scan(j)/=expected(j) then ffswitch:=ffswitch+1;wtm:=wtm+j+1;end if;
          end loop;
          if scan_in/=last_in then serialtoggles:=serialtoggles+1;end if;last_in:=scan_in;
        end if;""")
 eng=eng.replace('report "[SEQUENCE] "', 'report "[ACTIVITY] "&integer\'image(wtm)&","&integer\'image(ffswitch)&","&integer\'image(serialtoggles);\n    report "[SEQUENCE] "')
 put("lbist/tb/phase6a_processor_check.vhd",eng)
 for top in ["tb_phase6a_controller_integration","tb_phase6a_fault_comparison"]:
  put(f"lbist/tb/{top}.vhd",f"""library ieee;use ieee.std_logic_1164.all;
entity {top} is generic(APPROACH:natural:=2;BETA:natural:=20;CONFIG_ID:natural:=2;FAULT_ID:natural:=0);port(test_done:out boolean);end;
architecture test of {top} is signal done:boolean:=false;begin
 engine:entity work.phase6a_processor_check generic map(APPROACH=>APPROACH,BETA=>BETA,CONFIG_ID=>CONFIG_ID,FAULT_ID=>FAULT_ID) port map(done);
 process begin wait until done;report "[TB_COMPLETE] {top} at "&time'image(now);test_done<=true;wait;end process;end;
""")
 # Reuse compiled project infrastructure via source; redirect all output before runs.
 common=(R/"lbist/scripts/phase5bc_common.tcl").read_text().replace("Results Phase5B","Results Phase6A").replace("Results Phase5C","Results Phase6A")
 common=common.replace("phase5_project {selection}","phase5_project {selection}")
 marker="    set_property xsim.simulate.runtime"
 common=common.replace(marker,"""    foreach n {swap_controller moving_controller lbist_pattern_router phase6a_safe_misr} {
      add_files -fileset sources_1 [list [file join $phase5_root lbist rtl $n.vhd]]
    }
    foreach n {phase6a_golden_pkg phase6a_processor_check tb_phase6a_controller_integration tb_phase6a_fault_comparison tb_phase6a_misr_safety} {
      add_files -fileset sim_1 [list [file join $phase5_root lbist tb $n.vhd]]
    }
"""+marker)
 common=common.replace("set phase Phase5B; if {$group eq {Faults}} {set phase Phase5C}","set phase Phase6A")
 common=common.replace("tb_misr_integration tb_lbist_fault_injection}","tb_misr_integration tb_lbist_fault_injection tb_phase6a_controller_integration tb_phase6a_fault_comparison}")
 common+="""
# Batch file addition avoids repeated native project updates.
proc phase5_project {selection} {
 global phase5_root
 set dir [file join $phase5_root Results Phase6A work project_$selection]
 if {[info exists ::env(PHASE6A_NATIVE_ROOT)]} {set dir [file join $::env(PHASE6A_NATIVE_ROOT) project_$selection]}
 create_project -force phase6a $dir -part xc7a35tcpg236-1
 # Keep the historical project basename used by the case runner.
 close_project
 create_project -force phase5a $dir -part xc7a35tcpg236-1
 set sources {}
 foreach n {packageWires packageMemory_simu packageExcp altera units aux_module pipestages exception core cache instrcache rom ram io uart disk SDcard fpu sdram tb_cMIPS} {
  lappend sources [file join $phase5_root cMIPS vhdl $n.vhd]
 }
 foreach n {lfsr_16 phase_shifter plpf_dynamic basic_controller swap_controller moving_controller reg_IF_RF_scan lbist_test_controller misr_16 misr_signature_checker lbist_misr_top lbist_pattern_router phase6a_safe_misr} {
  lappend sources [file join $phase5_root lbist rtl $n.vhd]
 }
 set modern [concat [glob [file join $phase5_root lbist core_scan phase5a *.vhd]] [list [file join $phase5_root lbist core_scan core_scan_test.vhd] [file join $phase5_root lbist core_scan fault_injection core_scan_fault.vhd]]]
 add_files -fileset sources_1 [concat $sources $modern]
 set_property file_type {VHDL 2008} [get_files $modern]
 set benches {}
 foreach n {phase2_tb_pkg phase5a_rom_pkg phase6a_golden_pkg phase6a_processor_check tb_phase6a_controller_integration tb_phase6a_fault_comparison tb_phase6a_misr_safety tb_core_fault_regression tb_misr_16} {
  lappend benches [file join $phase5_root lbist tb $n.vhd]
 }
 add_files -fileset sim_1 $benches
 set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
}
"""
 common=common.replace(" create_project -force phase6a $dir -part xc7a35tcpg236-1\n # Keep the historical project basename used by the case runner.\n close_project\n","")
 common=common.replace("signature_valid signature_match fault_detected}", "signature_valid signature_match fault_detected phase pos patterns unload response q valid match detected scenario err}")
 put("lbist/scripts/phase6a_common.tcl",common)
 print("Configurations:",configs,"Goldens:",[f"{s:04X}" for s in gold])
if __name__=="__main__":build()
