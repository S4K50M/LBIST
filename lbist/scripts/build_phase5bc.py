"""Generate separate Phase 5B/C variants; never rewrite verified phase sources."""
from pathlib import Path
import csv, hashlib, json, subprocess
R=Path(__file__).resolve().parents[2]
def put(p,s):
    p=R/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def step(s,b):
    f=((s>>15)&1)^b
    return ((s<<1)&65535)^(0x1021 if f else 0)
def build():
    before=R/"Results/Phase5B/work/protected.json"
    before.parent.mkdir(parents=True,exist_ok=True)
    if not before.exists():
        names=subprocess.check_output(["git","ls-tree","-r","--name-only","-z","1c4eec0"],cwd=R).decode().split("\0")
        before.write_text(json.dumps({n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names if n}))
    for phase in ["Phase5B","Phase5C"]:
        put(f"Results/{phase}/.gitignore","work/\n*.wdb\n*.vcd\n/*.log\n*.jou\n.Xil/\n")
    rows=list(csv.DictReader((R/"Results/Phase5A/phase5a_capture_unload.csv").open()))
    rows=[r for r in rows if r["Case"]=="core_shift_capture_P256"]
    s=0; sigs=[]
    for row in rows:
        for b in f'{int(row["Expected"],16):064b}': s=step(s,int(b))
        sigs.append(s)
    put("lbist/tb/phase5bc_golden_pkg.vhd",
        "library ieee;use ieee.std_logic_1164.all;\npackage phase5bc_golden_pkg is\n"
        +f'constant GOLDEN_FINAL : std_logic_vector(15 downto 0):=x"{s:04X}";\nend package;\n')
    core=(R/"lbist/core_scan/core_scan_test.vhd").read_text().replace("core_scan_test","core_scan_fault")
    core=core.replace("  port (","  generic(FAULT_ID : natural:=0);\n  port (",1)
    at=core.index("begin",core.index("architecture rtl"))
    fn="""  function injected(v:reg32;region:natural) return reg32 is
    variable q:reg32:=v;variable site,bitn:natural;
    type bits_t is array(0 to 3) of natural;
    constant pc_bits:bits_t:=(2,3,16,31);
    constant ins_bits:bits_t:=(0,1,16,31);
  begin
    if FAULT_ID>0 and FAULT_ID<=16 then
      site:=(FAULT_ID-1)/2;
      if site/4=region then
        if region=0 then bitn:=pc_bits(site mod 4);else bitn:=ins_bits(site mod 4);end if;
        if FAULT_ID mod 2=1 then q(bitn):='0';else q(bitn):='1';end if;
      end if;
    end if;return q;
  end;
"""
    core=core[:at]+fn+core[at:]
    core=core.replace("capture_word<=instr_fetched when isolation_hold='0' else instr;",
        "capture_word<=injected(instr,1) when legal_capture='1' else instr_fetched when isolation_hold='0' else instr;")
    core=core.replace('increment_operand<=RF_PCincd(31 downto 2)&"00" when legal_capture',
        'increment_operand<=injected(RF_PCincd(31 downto 2)&"00",0) when legal_capture')
    put("lbist/core_scan/fault_injection/core_scan_fault.vhd",core)
    eng=(R/"lbist/tb/phase5a_processor_check.vhd").read_text().replace("phase5a_processor_check","phase5bc_processor_check")
    eng=eng.replace("generic(PATTERNS","generic(FAULT_ID:natural:=0; PATTERNS")
    eng=eng.replace("entity work.core_scan_test","entity work.core_scan_fault generic map(FAULT_ID)")
    eng=eng.replace("begin\n  test_done", """  signal signature:std_logic_vector(15 downto 0);
  signal misr_enable,signature_valid,signature_match,fault_detected:std_logic;
begin
  misr_enable<=scan_enable when test_phase="100" else '0';
  response_analyzer:entity work.lbist_misr_top
    port map(clk,rst,misr_enable,scan_out,done,work.phase5bc_golden_pkg.GOLDEN_FINAL,
             signature,signature_valid,signature_match,fault_detected);
  test_done""",1)
    eng=eng.replace("variable writes_before", "variable model_sig:unsigned(15 downto 0):=(others=>'0');\n    variable fb:std_logic;\n    variable writes_before")
    eng=eng.replace("unloads:=unloads+1;", """fb:=model_sig(15) xor scan_out;
          model_sig:=shift_left(model_sig,1);
          if fb='1' then model_sig:=model_sig xor x"1021";end if;
          unloads:=unloads+1;""")
    # Independent expected fault transformation before the functional +4.
    eng=eng.replace('golden:=std_logic_vector(capture_operand+4)&rom_word(program,frozen_pc);',"""
        case FAULT_ID is
          when 1=>capture_operand(2):='0';when 2=>capture_operand(2):='1';
          when 3=>capture_operand(3):='0';when 4=>capture_operand(3):='1';
          when 5=>capture_operand(16):='0';when 6=>capture_operand(16):='1';
          when 7=>capture_operand(31):='0';when 8=>capture_operand(31):='1';
          when others=>null;
        end case;
        golden:=std_logic_vector(capture_operand+4)&rom_word(program,frozen_pc);
        case FAULT_ID is
          when 9=>golden(0):='0';when 10=>golden(0):='1';
          when 11=>golden(1):='0';when 12=>golden(1):='1';
          when 13=>golden(16):='0';when 14=>golden(16):='1';
          when 15=>golden(31):='0';when 16=>golden(31):='1';
          when others=>null;
        end case;""")
    eng=eng.replace('check(scan_state=expected,"every real', 'check(signature=std_logic_vector(model_sig),"MISR exact recurrence and hold");\n      check(scan_state=expected,"every real')
    eng=eng.replace('report "[CAPTURE] "', 'report "[SIGNATURE] "&integer\'image(FAULT_ID)&","&integer\'image(pattern_count)&","&SLV32HEX(x"0000"&signature);\n        report "[CAPTURE] "')
    eng=eng.replace('event_id<=x"06";',"""check(signature_valid='1',"comparator valid only after completion");
    if FAULT_ID=0 then check(signature_match='1' and fault_detected='0',"fault-free golden signature");end if;
    report "[FINAL_SIGNATURE] "&integer'image(FAULT_ID)&","&SLV32HEX(x"0000"&signature);
    event_id<=x"06";""")
    eng=eng.replace('phase_before:=to_integer', 'check(signature_valid=\'0\',"no premature comparator PASS");\n      phase_before:=to_integer')
    put("lbist/tb/phase5bc_processor_check.vhd","\n".join(line.rstrip() for line in eng.splitlines())+"\n")
    regression=(R/"lbist/tb/tb_core_scan_test_regression.vhd").read_text()
    regression=regression.replace("tb_core_scan_test_regression","tb_core_fault_regression").replace("entity work.core_scan_test","entity work.core_scan_fault")
    put("lbist/tb/tb_core_fault_regression.vhd",regression)
    for name in ["tb_misr_integration","tb_lbist_fault_injection"]:
        put(f"lbist/tb/{name}.vhd",f"""library ieee;use ieee.std_logic_1164.all;
entity {name} is generic(FAULT_ID:natural:=0);port(test_done:out boolean);end;
architecture test of {name} is signal done:boolean:=false;
begin
 engine:entity work.phase5bc_processor_check generic map(FAULT_ID=>FAULT_ID) port map(done);
 process begin wait until done;report "[TB_COMPLETE] {name} at "&time'image(now);test_done<=true;wait;end process;
end;
""")
    inv=[]
    for i in range(1,17):
        site=(i-1)//2;region="increment_operand" if site<4 else "instruction_input"
        bit=([2,3,16,31] if site<4 else [0,1,16,31])[site%4]
        inv.append(dict(FaultID=i,Module="core_scan_fault",Signal=region,Bit=bit,FaultType="SA0" if i%2 else "SA1",
                        InjectionPoint="before original +4" if site<4 else "before actual IF/RF capture input",
                        Eligible=True,Reason="enumerated input-net fault universe; capture only"))
    p=R/"Results/Phase5C/reports/fault_inventory.csv";p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(inv[0]));w.writeheader();w.writerows(inv)
    # Reuse runner implementation in a new result/work directory.
    common=(R/"lbist/scripts/phase5a_common.tcl").read_text().replace("Results Phase5A","Results Phase5B")
    common=common.replace("    set_property xsim.simulate.runtime", """
    foreach rel {lbist/rtl/misr_16.vhd lbist/rtl/misr_signature_checker.vhd lbist/rtl/lbist_misr_top.vhd lbist/core_scan/fault_injection/core_scan_fault.vhd} {
        set f [file join $phase5_root $rel];add_files -fileset sources_1 [list $f]
        set_property file_type {VHDL 2008} [get_files [list $f]]
    }
    foreach name {phase5bc_golden_pkg phase5bc_processor_check tb_misr_16 tb_misr_integration tb_lbist_fault_injection} {
        add_files -fileset sim_1 [list [file join $phase5_root lbist tb $name.vhd]]
    }
    set_property xsim.simulate.runtime""")
    common=common.replace("if {$top in {tb_core_scan_isolation tb_core_scan_shift_capture}}", "if {$top in {tb_core_scan_isolation tb_core_scan_shift_capture tb_misr_integration tb_lbist_fault_injection}}")
    common=common.replace("capture_ready fabric_idle bsel busfree}", "capture_ready fabric_idle bsel busfree signature misr_enable signature_valid signature_match fault_detected}")
    common=common.replace("set out [file join $phase5_root Results Phase5B $group]",
        "set phase Phase5B; if {$group eq {Faults}} {set phase Phase5C};set out [file join $phase5_root Results $phase $group]")
    common=common.replace("capture_ready fabric_idle bsel busfree signature",
        "enable clear response_bit capture_ready fabric_idle bsel busfree signature")
    common=common.replace("tb_core_scan_test_regression","tb_core_fault_regression")
    put("lbist/scripts/phase5bc_common.tcl",common)
    print(f"Generated fault universe: 16; Basic256 golden signature {s:04X}")
if __name__=="__main__":build()
