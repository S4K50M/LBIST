library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
use work.phase2_tb_pkg.all;
entity tb_reg_IF_RF_scan is
  generic(PATTERNS : positive := 256; SEED : natural := 12345);
end entity;
architecture test of tb_reg_IF_RF_scan is
  signal clk : std_logic:='0';
  signal rst : std_logic:='1';
  signal ld : std_logic:='1';
  signal scan_enable,scan_in,scan_out,scan_feedback : std_logic:='0';
  signal pc_d,instr,pc_q,rf_instr,pc_ref,instr_ref : reg32:=(others=>'0');
  signal q,reference_q : std_logic_vector(63 downto 0);
  signal event_id : std_logic_vector(7 downto 0):=(others=>'0');
  signal test_done : boolean:=false;
begin
  assert PATTERNS>=256 report "[CONFIG_ERROR] PATTERNS must be >=256" severity failure;
  q<=pc_q&rf_instr; reference_q<=pc_ref&instr_ref;
  dut: entity work.reg_IF_RF_scan port map(clk,rst,ld,pc_d,pc_q,instr,rf_instr,scan_enable,scan_in,scan_out,scan_feedback);
  original: entity work.reg_IF_RF port map(clk,rst,ld,pc_d,pc_ref,instr,instr_ref);
  clocking: process begin
    while not test_done loop wait for 1 ns;exit when test_done;clk<=not clk;end loop;wait;
  end process;
  watchdog: process begin
    wait until test_done for 20 ms;check(test_done,"register watchdog");wait;
  end process;
  stimulus: process
    variable expected,word,old : std_logic_vector(63 downto 0):=(others=>'0');
    variable random_state : unsigned(31 downto 0):=to_unsigned(SEED,32);
    variable shifts : natural:=0;
    procedure randomize is begin
      random_state:=random_state xor shift_left(random_state,13);
      random_state:=random_state xor shift_right(random_state,17);
      random_state:=random_state xor shift_left(random_state,5);
    end;
    procedure inspect is begin
      check(q=expected,"all 64 IF/RF bits equal independent scoreboard");
      check(scan_out=expected(63),"pre/post scan-out oldest bit");
      check(scan_feedback=expected(0),"feedback is actual input-stage FF");
    end;
    procedure edge is begin
      inspect;
      if scan_enable='1' then expected:=expected(62 downto 0)&scan_in;shifts:=shifts+1;
      elsif ld='0' then expected:=pc_d&instr;end if;
      wait until rising_edge(clk);wait for 100 ps;inspect;
      old:=expected;wait until falling_edge(clk);wait for 100 ps;
      check(q=old,"SCAN15 no falling-edge storage update");inspect;
    end;
    procedure load_scan(v : std_logic_vector(63 downto 0)) is begin
      scan_enable<='1';ld<='1';
      for k in 63 downto 0 loop scan_in<=v(k);wait for 100 ps;edge;end loop;
      check(q=v,"SCAN05 exact 64-shift load and vector mapping");
    end;
  begin
    wait for 200 ps;rst<='0';wait for 100 ps;inspect;
    check(reference_q=x"0000000000000000","original async reset");
    event_id<=x"01";report "[PASS] SCAN01 asynchronous active-low reset between edges";
    wait until falling_edge(clk);wait for 100 ps;rst<='1';ld<='0';
    pc_d<=x"12345678";instr<=x"89ABCDEF";event_id<=x"02";wait for 100 ps;edge;
    check(q=reference_q,"SCAN02 functional load reference");
    report "[PASS] SCAN02 functional load and exact PC/instruction mapping";
    ld<='1';pc_d<=x"FEDCBA98";instr<=x"76543210";event_id<=x"03";wait for 100 ps;edge;
    check(q=reference_q,"SCAN03 hold original reference");report "[PASS] SCAN03 functional hold";
    event_id<=x"0B";
    for k in 0 to 255 loop
      randomize;pc_d<=std_logic_vector(random_state);randomize;instr<=std_logic_vector(random_state);
      if k mod 3=0 then ld<='1';else ld<='0';end if;
      wait for 100 ps;edge;check(q=reference_q,"SCAN11 randomized original/scan equivalence");
    end loop;
    report "[PASS] SCAN11 256 deterministic functional load/hold cycles match original";
    event_id<=x"04";load_scan(x"A55AC33CF00F9669");
    report "[PASS] SCAN04/SCAN05 scan overrides active-low functional stall, 64 exact shifts";
    event_id<=x"06";load_scan(x"55AA66990FF033CC");
    report "[PASS] SCAN06/SCAN07 scan-out ordering and real first-stage feedback on every shift";
    scan_enable<='0';ld<='1';event_id<=x"08";wait for 100 ps;edge;
    ld<='0';pc_d<=x"10203040";instr<=x"50607080";event_id<=x"09";wait for 100 ps;edge;
    check(q=reference_q,"functional capture matches original after scan");report "[PASS] SCAN08/SCAN09 one functional capture after scan";
    event_id<=x"0A";load_scan(x"0123456789ABCDEF");
    report "[PASS] SCAN10 captured response serialized correctly while loading next pattern";
    event_id<=x"0D";
    for p in 0 to PATTERNS-1 loop
      if p=0 then word:=(others=>'0');
      elsif p=1 then word:=(others=>'1');
      elsif p=2 then word:=x"AAAAAAAAAAAAAAAA";
      elsif p=3 then word:=x"5555555555555555";
      elsif p<68 then word:=(others=>'0');word(p-4):='1';
      elsif p<132 then word:=(others=>'1');word(p-68):='0';
      else randomize;word(63 downto 32):=std_logic_vector(random_state);
           randomize;word(31 downto 0):=std_logic_vector(random_state);
      end if;
      load_scan(word);
    end loop;
    report "[PASS] SCAN13/SCAN14 at least 256 patterns: zero, one, alternating, walking one/zero and deterministic random";
    event_id<=x"0C";scan_enable<='1';scan_in<='1';wait for 100 ps;edge;
    rst<='0';expected:=(others=>'0');wait for 100 ps;inspect;
    check(reference_q=x"0000000000000000","original reset during scan");
    report "[PASS] SCAN12 asynchronous reset during incomplete scan";
    report "[PASS] SCAN15 clock/enable alignment, every pre/post-edge bit and no extra shifts";
    report "[SCAN_METRIC] UNIT,"&integer'image(PATTERNS)&","&integer'image(shifts);
    report "[TB_COMPLETE] tb_reg_IF_RF_scan at "&time'image(now);
    test_done<=true;wait;
  end process;
end architecture;
