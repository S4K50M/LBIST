"""Generate CE-only variants without changing their verified source files."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "lbist/core_scan/phase5a"
HEADER = (ROOT / "cMIPS/vhdl/core.vhd").read_text().split("-- CPU core")[0]


def extract(file, entity, last=False):
    text = (ROOT / "cMIPS/vhdl" / file).read_text()
    pos = re.search(r"entity\s+" + entity + r"\s+is", text, re.I).start()
    start = text.rfind("library ", 0, pos)
    arches = list(re.finditer(r"architecture\s+(\w+)\s+of\s+" + entity + r"\s+is", text[pos:], re.I))
    arch = arches[-1] if last else arches[0]
    offset = pos + arch.end()
    end = re.search(r"end\s+(?:architecture(?:\s+\w+)?|" + arch[1] + r")\s*;", text[offset:], re.I)
    return HEADER + text[start:offset + end.end()]


def add_ports(text, entity, ports):
    end = re.search(r"end(?:\s+entity)?\s+" + entity + r"\s*;", text, re.I).start()
    at = text.rfind(");", 0, end)
    return text[:at] + "; " + ports + text[at:]


def rename(text, entity):
    for pattern in [r"(entity\s+)" + entity + r"(\s+is)",
                    r"(end\s+)" + entity + r"(\s*;)",
                    r"(architecture\s+\w+\s+of\s+)" + entity + r"(\s+is)"]:
        text = re.sub(pattern, r"\g<1>" + entity + r"_test\g<2>", text, flags=re.I)
    return text


def ce(text):
    return re.sub(r"rising_edge\((\w+)\)", r"(rising_edge(\1) and hold='0')", text, flags=re.I)


def maps(text):
    clean = re.sub(r"--[^\n]*", lambda m: " " * len(m[0]), text)
    pattern = r"(\w+)\s*:\s*(\w+)(\s+generic\s+map\s*\([^;]*?\))?\s+port\s+map\s*\(([^;]*?)\);"
    return list(re.finditer(pattern, clean, re.I))


def args(text):
    result, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(": depth += 1
        elif ch == ")": depth -= 1
        elif ch == "," and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    return result + [text[start:].strip()]


def formals(text, entity):
    pos = re.search(r"entity\s+" + entity + r"\s+is", text, re.I).end()
    end = pos + re.search(r"end(?:\s+entity)?\s+" + entity + r"\s*;", text[pos:], re.I).start()
    sub = text[pos:end]
    sub = sub[sub.lower().index("port") + 4:].strip()[1:]
    sub = sub[:sub.rfind(");")]
    result = []
    for field in sub.split(";"):
        field = re.sub(r"--[^\n]*", "", field)
        match = re.match(r"\s*([\w,\s]+):\s*(in|out)\s+(.+)", field, re.I | re.S)
        assert match, field
        result.extend((n.strip(), match[2].lower(), match[3].strip()) for n in match[1].split(","))
    return result


def replace_instances(text, types, hold="hold"):
    for m in reversed(maps(text)):
        if m[2].lower() not in types: continue
        local_hold = "phi2_sync(1)" if hold == "isolation_hold" and m[1].lower() in ["u_ifetch_stalled", "u_dmem_stalled"] else hold
        extra = ", hold => " + local_hold if "=>" in m[4] else ", " + local_hold
        new = m[1] + ": entity work." + types[m[2].lower()] + (m[3] or "") + " port map (" + m[4] + extra + ");"
        text = text[:m.start()] + new + text[m.end():]
    return text


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    source = {}
    for file, names in [
        ("aux_module.vhd", ["register32", "registerN", "counter32", "FFD"]),
        ("pipestages.vhd", ["reg_RF_EX", "reg_EX_MM", "reg_MM_WB"]),
        ("exception.vhd", ["reg_excp_IF_RF", "reg_excp_RF_EX", "reg_excp_EX_MM", "reg_excp_MM_WB"]),
    ]:
        for name in names:
            original = extract(file, name)
            source[name.lower()] = original
            text = rename(ce(add_ports(original, name, "hold : in std_logic")), name)
            (DEST / (name + "_test.vhd")).write_text(text)

    ram = extract("units.vhd", "ram_dual")
    ram = rename(ce(add_ports(ram, "ram_dual", """hold,read_hold : in std_logic;
       state_debug : out std_logic_vector(N_WORDS*WIDTH+WIDTH-1 downto 0)""")), "ram_dual")
    at = ram.lower().index("begin", ram.lower().index("architecture")) + 5
    ram = ram[:at] + """
  state_debug(N_WORDS*WIDTH+WIDTH-1 downto N_WORDS*WIDTH)<=q;
  probe: for k in 0 to N_WORDS-1 generate
    state_debug((k+1)*WIDTH-1 downto k*WIDTH)<=ram(k);
  end generate;
""" + ram[at:]
    (DEST / "ram_dual_test.vhd").write_text(ram)
    ram = ram.replace("rising_edge(rclk) and hold='0'", "rising_edge(rclk) and read_hold='0'")
    (DEST / "ram_dual_test.vhd").write_text(ram)

    bank = extract("units.vhd", "reg_bank", True)
    source["reg_bank"] = bank
    bank = rename(ce(add_ports(bank, "reg_bank", """hold,read_hold : in std_logic;
       state_debug : out std_logic_vector(2111 downto 0)""")), "reg_bank")
    at = bank.lower().index("begin", bank.lower().index("architecture rtl")) + 5
    bank = bank[:at] + """
  state_debug(2111 downto 2048)<=pre_A&pre_B;
  probe: for k in 0 to 31 generate
    state_debug(32*k+31 downto 32*k)<=reg_file_A(k);
    state_debug(1024+32*k+31 downto 1024+32*k)<=reg_file_B(k);
  end generate;
""" + bank[at:]
    at = bank.lower().index("begin", bank.lower().index("architecture dual_port_ram"))
    bank = bank[:at] + "signal debug_a,debug_b : std_logic_vector(1055 downto 0);\n" + bank[at:]
    for letter, output, debug in [("A", "pre_A", "debug_a"), ("B", "pre_B", "debug_b")]:
        pattern = re.compile(r"PORT_" + letter + r":\s*ram_dual(\s+generic\s+map\s*\([^;]+?\))\s+port\s+map\s*\(([^;]+?)\);", re.I)
        bank, count = pattern.subn(lambda m: "PORT_" + letter + ": entity work.ram_dual_test" + m[1] +
                                  " port map (" + m[2] + ",hold,read_hold," + debug + ");", bank)
        assert count == 1
    at = bank.lower().index("begin", bank.lower().index("architecture dual_port_ram")) + 5
    bank = bank[:at] + "\n state_debug<=debug_a&debug_b;\n" + bank[at:]
    bank = bank.replace("rising_edge(rdclk) and hold='0'", "rising_edge(rdclk) and read_hold='0'")
    (DEST / "reg_bank_test.vhd").write_text(bank)

    alu = extract("units.vhd", "alu")
    source["alu"] = alu
    alu = rename(add_ports(alu, "alu", "hold : in std_logic"), "alu")
    alu = replace_instances(alu, {"register32": "register32_test"})
    (DEST / "alu_test.vhd").write_text(alu)

    core = (ROOT / "lbist/core_scan/core_scan.vhd").read_text()
    core = core.replace("-- Scan ports do NOT isolate the rest of the processor.",
                        "-- This variant adds processor hold enables and a qualified capture.")
    core = core.replace("entity core_scan is", "entity core_scan_test is", 1).replace("end core_scan;", "end core_scan_test;", 1)
    core = core.replace("architecture rtl of core_scan is", "architecture rtl of core_scan_test is", 1)
    core = add_ports(core, "core_scan_test", """test_mode,capture_enable,fabric_idle,capture_ready : in std_logic;
       test_phase : in std_logic_vector(2 downto 0);
       isolation_ack,protocol_error : out std_logic;
       protected_state : out std_logic_vector(8191 downto 0);
       protected_width : out natural;
       scan_state : out std_logic_vector(63 downto 0);
       pc_observe : out reg32;
       memory_write_attempt,register_write_attempt,register_write_actual : out std_logic""")
    terms, widths, coverage = [], [], []
    def probe(expr, typ):
        if typ.lower() == "std_logic": terms.append(expr); widths.append("1")
        elif typ.lower() == "boolean": terms.append("BOOL2SL(" + expr + ")"); widths.append("1")
        elif typ.lower() in ["t_alu_fun", "exception_type"]:
            terms.append("std_logic_vector(to_unsigned(" + typ + "'pos(" + expr + "),16))"); widths.append("16")
        else: terms.append(expr); widths.append(expr + "'length")
    for m in maps(core):
        kind = m[2].lower()
        if kind not in source: continue
        actual, outputs = args(m[4]), []
        for i, (name, direction, typ) in enumerate(formals(source[kind], m[2])):
            if direction != "out" or kind in ["reg_bank", "alu"]: continue
            expr = actual[i].split("=>")[-1].strip()
            if expr.lower() == "open": continue
            probe(expr, typ); outputs.append(expr)
        coverage.append(dict(Instance=m[1], Primitive=m[2], Outputs=outputs))
    for expr, typ in [("CAUSE", "reg32"), ("ll_sc_bit", "std_logic"), ("RANDOM", "reg32"),
                      ("HI", "reg32"), ("LO", "reg32"), ("gpr_probe", "std_logic_vector"),
                      ("ExcCode", "reg5"), ("nullify_MM_pre", "std_logic")]:
        probe(expr, typ)
    core = replace_instances(core, {k: k + "_test" for k in source if k != "reg_bank"}, "isolation_hold")
    core = core.replace("U_regs: reg_bank", "U_regs: entity work.reg_bank_test(dual_port_ram)")
    core = core.replace("phi1, WB_wreg, a_rs", "phi1, safe_gpr_write, a_rs", 1)
    core = core.replace("WB_a_c,WB_C, regs_A,regs_B);", "WB_a_c,WB_C, regs_A,regs_B,isolation_hold,phi1_sync(1),gpr_probe);")
    assert len(re.findall(r"elsif rising_edge\(clk\) then", core)) == 3
    core = core.replace("elsif rising_edge(clk) then", "elsif rising_edge(clk) and isolation_hold='0' then")
    core = core.replace("RF_instruction", "RF_decode_word")
    core = core.replace("signal RF_PCincd, RF_decode_word : reg32;", "signal RF_PCincd, RF_decode_word, RF_instruction : reg32;")
    old = """              instr_fetched, RF_decode_word,
              scan_enable,scan_in,scan_out,scan_feedback);"""
    assert old in core
    core = core.replace(old, """              capture_word, RF_instruction,
              legal_shift,scan_in,scan_out,scan_feedback);""", 1)
    core = core.replace("port map (clk,rst, IF_RF_ld, PCincd, RF_PCincd,", "port map (clk,rst, selected_ld, PCincd, RF_PCincd,", 1)
    assert "datab => PC_aligned" in core
    core = core.replace("datab => PC_aligned", "datab => increment_operand", 1)
    core = core.replace("if rst = '1' and phi2 = '1' then", "if rst = '1' and phi2 = '1' and isolation_hold='0' then", 1)
    for pattern, replacement in [
        (r"i_aVal\s*<= '0';", "i_aVal <= isolation_hold;"),
        (r"d_aVal\s*<= MM_aVal;", "d_aVal <= MM_aVal when isolation_hold='0' else '1';"),
        (r"wr\s*<= MM_wrmem;", "wr <= MM_wrmem when isolation_hold='0' else '1';"),
        (r"busFree\s*<= EX_aVal_cond;", "busFree <= EX_aVal_cond when isolation_hold='0' else '1';"),
        (r"b_sel\s*<= i_byte_sel;", "byte_select_internal <= i_byte_sel;"),
    ]:
        core, count = re.subn(pattern, replacement, core, count=1)
        assert count == 1, pattern
    at = core.index("\nbegin", core.index("architecture rtl"))
    body = core[at:]
    for port in ["irq", "nmi", "i_wait", "d_wait", "i_busErr", "d_busErr", "data_inp"]:
        body = re.sub(r"\b" + port + r"\b", "functional_" + port, body, flags=re.I)
    core = core[:at] + body
    declarations = """
  signal isolation_hold : std_logic:='0';
  signal phi1_sync,phi2_sync,ack_sync : std_logic_vector(1 downto 0):=(others=>'0');
  attribute ASYNC_REG : string;
  attribute ASYNC_REG of phi1_sync,phi2_sync,ack_sync : signal is "TRUE";
  signal capture_seen,error_latch,legal_shift,legal_capture,selected_ld,safe_gpr_write : std_logic:='0';
  signal capture_word,increment_operand : reg32;
  signal byte_select_internal : reg4;
  signal functional_irq : reg6;
  signal functional_nmi,functional_i_wait,functional_d_wait,functional_i_busErr,functional_d_busErr : std_logic;
  signal functional_data_inp : reg32;
  signal gpr_probe : std_logic_vector(2111 downto 0);
  constant SNAPSHOT_BITS : positive := """ + " + ".join(widths) + """;
  signal snapshot : std_logic_vector(SNAPSHOT_BITS-1 downto 0);
"""
    core = core[:at] + declarations + core[at:]
    at = core.index("\nbegin", core.index("architecture rtl")) + len("\nbegin")
    logic = """
  assert SNAPSHOT_BITS<=8192 report "[CONFIG_ERROR] protected-state probe too narrow" severity failure;
  isolation_ack<=ack_sync(1);protocol_error<=error_latch;
  pc_observe<=PC;scan_state<=RF_PCincd&RF_instruction;
  protected_width<=SNAPSHOT_BITS;
  snapshot<=""" + "&".join(terms) + """;
  protected_state<=std_logic_vector(resize(unsigned(snapshot),8192));
  memory_write_attempt<='1' when MM_aVal='0' and MM_wrmem='0' else '0';
  register_write_attempt<='1' when WB_wreg='0' and WB_a_c/="00000" else '0';
  register_write_actual<='1' when safe_gpr_write='0' and WB_a_c/="00000" else '0';
  safe_gpr_write<=WB_wreg when isolation_hold='0' else '1';
  b_sel<=byte_select_internal when isolation_hold='0' else "0000";
  functional_irq<=irq when isolation_hold='0' else "000000";
  functional_nmi<=nmi when isolation_hold='0' else '0';
  functional_i_wait<=i_wait when isolation_hold='0' else '1';
  functional_d_wait<=d_wait when isolation_hold='0' else '1';
  functional_i_busErr<=i_busErr when isolation_hold='0' else '1';
  functional_d_busErr<=d_busErr when isolation_hold='0' else '1';
  functional_data_inp<=data_inp when isolation_hold='0' else x"00000000";
  RF_decode_word<=RF_instruction when isolation_hold='0' else x"00000000";
  capture_word<=instr_fetched when isolation_hold='0' else instr;
  -- Only the test capture steers the actual scanned PC half into the
  -- existing PC+4 adder. The architectural PC and fetch address stay held.
  increment_operand<=RF_PCincd(31 downto 2)&"00" when legal_capture='1' else PC_aligned;
  selected_ld<=IF_RF_ld when isolation_hold='0' else not legal_capture;
  legal_shift<='1' when ack_sync(1)='1' and test_mode='1' and scan_enable='1' and capture_enable='0'
    and (test_phase="010" or test_phase="100") else '0';
  legal_capture<='1' when ack_sync(1)='1' and test_mode='1' and capture_enable='1' and scan_enable='0'
    and test_phase="011" and capture_ready='1' and capture_seen='0' else '0';
  mode_latch: process(clk,rst)
  begin
    if rst='0' then isolation_hold<='0';
    elsif falling_edge(clk) then
      if test_mode='1' and fabric_idle='1' then isolation_hold<='1';end if;
    end if;
  end process;
  read_phase_hold: process(phi1,rst)
  begin
    if rst='0' then phi1_sync<=(others=>'0');
    elsif falling_edge(phi1) then phi1_sync<=phi1_sync(0)&isolation_hold;end if;
  end process;
  flag_phase_hold: process(phi2,rst)
  begin
    if rst='0' then phi2_sync<=(others=>'0');
    elsif falling_edge(phi2) then phi2_sync<=phi2_sync(0)&isolation_hold;end if;
  end process;
  entry_acknowledgement: process(clk,rst)
  begin
    if rst='0' then ack_sync<=(others=>'0');
    elsif rising_edge(clk) then
      ack_sync<=ack_sync(0)&(isolation_hold and phi1_sync(1) and phi2_sync(1));
    end if;
  end process;
  protocol: process(clk,rst)
  begin
    if rst='0' then capture_seen<='0';error_latch<='0';
    elsif rising_edge(clk) then
      if test_phase/="011" then capture_seen<='0';
      elsif legal_capture='1' then capture_seen<='1';end if;
      if (scan_enable='1' and legal_shift='0') or
         (capture_enable='1' and legal_capture='0') or
         (isolation_hold='1' and test_mode='0') then error_latch<='1';end if;
    end if;
  end process;
"""
    core = core[:at] + logic + core[at:]
    # CONTEXT became a reserved word in VHDL-2008; the old core is VHDL-93.
    core = re.sub(r"\bContext\b", "context_reg", core, flags=re.I)
    (ROOT / "lbist/core_scan/core_scan_test.vhd").write_text(core)
    (ROOT / "Results/Phase5A/phase5a_state_coverage.json").write_text(json.dumps(
        dict(Instances=coverage, DirectProcesses=["CAUSE", "ll_sc_bit", "RANDOM"],
             GPRBits=2112, ProbeTerms=terms,
             IdentifierRename={"Context": "context_reg"},
             HoldDomains={"clk": "isolation_hold", "phi1": "phi1_sync(1)", "phi2": "phi2_sync(1)"},
             Acknowledgement="two-stage clk synchronizer after both inactive-edge hold synchronizers",
             CaptureCone="scan PC half -> alignment -> existing U_INCPC +4; raw instruction input"), indent=2))
    # Strip inherited line-end whitespace only in the new generated copies.
    for path in list(DEST.glob("*.vhd")) + [ROOT / "lbist/core_scan/core_scan_test.vhd"]:
        path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()).rstrip() + "\n")
    print("Generated", len(list(DEST.glob("*.vhd"))), "CE variants and core_scan_test.")


if __name__ == "__main__":
    build()
