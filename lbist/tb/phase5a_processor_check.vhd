library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
use work.phase2_tb_pkg.all;
use work.phase5a_rom_pkg.all;
entity phase5a_processor_check is
  generic(PATTERNS : positive:=256; ENTRY_NS : positive:=380; ISOLATION_ONLY : boolean:=false);
  port(test_done : out boolean);
end entity;
architecture test of phase5a_processor_check is
  signal clk : std_logic:='0';
  signal phi1,phi2,phi3 : std_logic:='0';
  signal rst : std_logic:='0';
  signal finished : boolean:=false;
  signal start,pause,abort_test : std_logic:='0';
  signal test_mode,scan_enable,capture_enable,pattern_done,done,error_status : std_logic;
  signal isolation_ack,protocol_error : std_logic;
  signal test_phase : std_logic_vector(2 downto 0);
  signal shift_count,pattern_count,protected_width : natural;
  signal shift_count_v,pattern_index : std_logic_vector(15 downto 0);
  signal protected_state : std_logic_vector(8191 downto 0);
  signal scan_state : std_logic_vector(63 downto 0);
  signal pc_observe,i_addr,d_addr,data_out : reg32;
  signal i_aval,d_aval,wr,busfree : std_logic;
  signal bsel : reg4;
  signal memory_write_attempt,register_write_attempt,register_write_actual : std_logic;
  signal scan_in,scan_out,scan_feedback,raw_bit,current_bit,future1,future2,mode_valid : std_logic;
  signal mode_select,active_mode : std_logic_vector(1 downto 0);
  signal generator_state : std_logic_vector(15 downto 0);
  signal basic_count : natural;
  signal basic_done : std_logic;
  signal generator_reset : std_logic;
  signal fabric_idle,capture_ready : std_logic:='0';
  signal exit_attempt,bad_command : std_logic:='0';
  signal core_tm,core_se,core_ce : std_logic;
  signal irq : reg6:=(others=>'0');
  signal nmi : std_logic:='0';
  signal bus_error : std_logic:='1';
  signal instruction,data_inp : reg32;
  signal reference_rst : std_logic;
  signal ref_ia,ref_da,ref_wr,ref_busfree : std_logic;
  signal ref_i_addr,ref_d_addr,ref_data,ref_instr,ref_dinp : reg32;
  signal ref_bsel : reg4;
  type memory_t is array(0 to 1023) of reg32;
  signal ram : memory_t := (others=>(others=>'0'));
  signal memory_writes : natural:=0;
  signal event_id : std_logic_vector(7 downto 0):=(others=>'0');
  signal protected_equal : std_logic:='1';
  constant program : words_t:=load_program;
begin
  test_done<=finished;
  shift_count_v<=std_logic_vector(to_unsigned(shift_count,16));
  pattern_index<=std_logic_vector(to_unsigned(pattern_count,16));
  core_tm<=test_mode and not exit_attempt;
  core_se<=scan_enable or bad_command;core_ce<=capture_enable or bad_command;
  generator_reset<=not rst;
  instruction<=rom_word(program,i_addr);
  ref_instr<=rom_word(program,ref_i_addr);
  data_inp<=ram(to_integer(unsigned(d_addr(11 downto 2)))) when not is_x(d_addr) else (others=>'0');
  ref_dinp<=ram(to_integer(unsigned(ref_d_addr(11 downto 2)))) when not is_x(ref_d_addr) else (others=>'0');
  reference_rst<=rst and not isolation_ack;
  ctrl: entity work.lbist_test_controller generic map(64,PATTERNS)
    port map(clk,rst,start,pause,abort_test,isolation_ack,capture_ready,
      test_mode,scan_enable,capture_enable,pattern_done,done,error_status,test_phase,shift_count,pattern_count);
  dut: entity work.core_scan_test
    port map(rst,clk,phi1,phi2,phi3,i_aval,'1',i_addr,instruction,
      d_aval,'1',d_addr,data_inp,data_out,wr,bsel,busfree,nmi,irq,bus_error,bus_error,
      core_se,scan_in,scan_out,scan_feedback,core_tm,core_ce,fabric_idle,capture_ready,test_phase,
      isolation_ack,protocol_error,protected_state,protected_width,scan_state,pc_observe,
      memory_write_attempt,register_write_attempt,register_write_actual);
  reference: entity work.core
    port map(reference_rst,clk,phi1,phi2,phi3,ref_ia,'1',ref_i_addr,ref_instr,
      ref_da,'1',ref_d_addr,ref_dinp,ref_data,ref_wr,ref_bsel,ref_busfree,'0',"000000",'1','1');
  lfsr: entity work.lfsr_16 port map(clk,generator_reset,scan_enable,raw_bit,generator_state);
  phases: entity work.phase_shifter port map(generator_state,current_bit,future1,future2);
  basic: entity work.basic_controller generic map(64,20)
    port map(clk,generator_reset,scan_enable,mode_select,basic_count,basic_done);
  plpf: entity work.plpf_dynamic
    port map(current_bit,future1,future2,scan_feedback,mode_select,scan_in,active_mode,mode_valid);
  clocking: process begin
    while not finished loop
      clk<='0';phi1<='0';phi2<='0';phi3<='0';
      wait for 5 ns;exit when finished;phi1<='1';
      wait for 5 ns;exit when finished;clk<='1';phi1<='0';phi2<='1';
      wait for 5 ns;exit when finished;phi2<='0';phi3<='1';
      wait for 5 ns;
    end loop;wait;
  end process;
  watchdog: process begin wait until finished for 20 ms;check(finished,"processor test watchdog");wait;end process;
  memory_model: process(clk)
  begin
    if rising_edge(clk) then
      if rst='1' and d_aval='0' and wr='0' then
        check(isolation_ack='0',"no actual RAM or peripheral write during isolation");
        ram(to_integer(unsigned(d_addr(11 downto 2))))<=data_out;
        memory_writes<=memory_writes+1;
      end if;
    end if;
  end process;
  state_monitor: process
    variable snapshot : std_logic_vector(8191 downto 0);
    variable recorded : boolean:=false;
    variable entered_test : boolean:=false;
  begin
    wait on clk,phi1,phi2,phi3,rst;
    wait for 100 ps;
    if rst='0' then recorded:=false;protected_equal<='1';
    elsif isolation_ack='1' then
      entered_test:=true;
      check(not is_x(scan_state),"reset-defined IF/RF storage never contains unknown bits");
      if not recorded then snapshot:=protected_state;recorded:=true;
      else
        check(protected_state=snapshot,"ALL audited architectural state holds across every CPU phase");
        protected_equal<=BOOL2SL(protected_state=snapshot);
      end if;
      check(i_aval='1' and d_aval='1' and wr='1' and bsel="0000","requests, memory/peripheral writes and byte enables suppressed");
      check(register_write_actual='0',"GPR writes suppressed");
    elsif test_mode='0' then
      if not entered_test then
        check(i_addr=ref_i_addr and d_addr=ref_d_addr and wr=ref_wr and i_aval=ref_ia and d_aval=ref_da and data_out=ref_data and bsel=ref_bsel,
          "initial normal-mode exact original-core equivalence");
      else
        -- Original reset intentionally leaves many pipeline data fields and
        -- the GPR arrays unreset. Their inactive bus values need not match
        -- after the reference has drained for a different number of phases.
        -- Compare every valid transaction and every instruction request.
        check(i_aval=ref_ia and d_aval=ref_da,"restart request-valid equivalence");
        if i_aval='0' then check(i_addr=ref_i_addr,"restart instruction address");end if;
        if d_aval='0' then
          check(d_addr=ref_d_addr and wr=ref_wr and bsel=ref_bsel,"restart data transaction controls");
          if wr='0' then check(data_out=ref_data,"restart data write value");end if;
        end if;
      end if;
    end if;
  end process;
  stimulus: process
    constant seq : bit_sequence:=sequence_model(x"AAAA");
    variable expected,golden,observed_response,unloaded_response : std_logic_vector(63 downto 0);
    variable saved : std_logic_vector(8191 downto 0);
    variable frozen_pc : reg32;
    variable source_index,shifts,captures,unloads,mem_attempts,reg_attempts,phase_before,previous_patterns : natural:=0;
    variable value,expected_out : std_logic;
    variable wanted_mode : std_logic_vector(1 downto 0);
    variable count_before : natural;
    variable capture_operand : unsigned(31 downto 0);
    variable writes_before,state_changes,actual_register_writes : natural:=0;
    procedure tick is begin wait until rising_edge(clk);wait for 200 ps;wait until falling_edge(clk);wait for 200 ps;end;
  begin
    wait for 25 ns;rst<='1';
    wait for ENTRY_NS*1 ns;
    wait until falling_edge(clk);wait for 200 ps;start<='1';event_id<=x"01";
    tick;start<='0';
    -- The host must declare that its fabric has no outstanding transactions.
    for k in 1 to 3 loop tick;check(isolation_ack='0' and scan_enable='0',"no test entry without fabric-idle handshake");end loop;
    fabric_idle<='1';capture_ready<='1';tick;
    while isolation_ack/='1' loop
      check(scan_enable='0' and capture_enable='0',"no scan/capture until every clock phase is isolated");
      tick;
    end loop;
    check(isolation_ack='1',"registered test entry");
    saved:=protected_state;frozen_pc:=pc_observe;
    writes_before:=memory_writes;
    golden:=std_logic_vector(unsigned(frozen_pc)+4)&rom_word(program,frozen_pc);
    expected:=scan_state;event_id<=x"02";
    while done/='1' loop
      -- Sample setup controls after a falling edge, independently of DUT updates.
      phase_before:=to_integer(unsigned(test_phase));count_before:=shift_count;
      previous_patterns:=pattern_count;
      if phase_before=2 and count_before=22 and pattern_count=0 then
        pause<='1';event_id<=x"03";wait for 200 ps;
        for k in 1 to 3 loop
          tick;check(scan_state=expected and protected_state=saved,"pause preserves real scan and protected state");
        end loop;
        pause<='0';event_id<=x"04";wait for 200 ps;
      end if;
      if protected_state/=saved then state_changes:=state_changes+1;end if;
      check(protected_state=saved,"architectural snapshot before scan/capture");
      check(scan_feedback=expected(0) and scan_out=expected(63),"actual scan FF feedback and pre-edge response output");
      if scan_enable='1' then
        wanted_mode:="00";
        if source_index mod 64>=22 and source_index mod 64<42 then wanted_mode:="11";end if;
        check(mode_select=wanted_mode and basic_count=source_index mod 64,"Basic schedule across both shift and unload");
        check(generator_state=window(seq,source_index mod 65535),"one LFSR advance per accepted scan edge");
        value:=filtered(seq(source_index mod 65535),seq((source_index+1) mod 65535),seq((source_index+2) mod 65535),expected(0),wanted_mode);
        check(scan_in=value,"independent real-feedback PLPF reference");
        if phase_before=4 then
          expected_out:=golden(63-count_before);
          check(scan_out=expected_out,"captured response serialized in exact bit order");
          unloaded_response(63-count_before):=scan_out;
          unloads:=unloads+1;
        else shifts:=shifts+1;end if;
        expected:=expected(62 downto 0)&value;source_index:=source_index+1;
      elsif capture_enable='1' then
        check(phase_before=3 and count_before=0,"one capture phase edge");
        -- Independent expected response from the verified scan-loaded word,
        -- not from the DUT's adder output or its captured response.
        capture_operand:=unsigned(expected(63 downto 32));
        capture_operand(1 downto 0):="00";
        golden:=std_logic_vector(capture_operand+4)&rom_word(program,frozen_pc);
        expected:=golden;captures:=captures+1;event_id<=x"05";
      end if;
      if memory_write_attempt='1' then mem_attempts:=mem_attempts+1;end if;
      if register_write_attempt='1' then reg_attempts:=reg_attempts+1;end if;
      if register_write_actual='1' then actual_register_writes:=actual_register_writes+1;end if;
      tick;
      if phase_before=3 and capture_enable/='1' then
        -- CAPTURE just completed and the FSM now selects UNLOAD.
        observed_response:=scan_state;
        check(observed_response=golden,"observed real capture equals independent response");
      end if;
      check(scan_state=expected,"every real IF/RF bit after shift/capture/hold");
      check(protected_state=saved,"protected state unchanged after edge");
      check(generator_state=window(seq,source_index mod 65535) and basic_count=source_index mod 64,"capture/idle do not advance generators");
      check(error_status='0' and protocol_error='0',"legal sequence has no protocol errors");
      if phase_before=4 and count_before=63 then
        check(pattern_done='1' and pattern_count=previous_patterns+1,"exact pattern completion");
        report "[CAPTURE] "&integer'image(pattern_count)&","&SLV32HEX(observed_response(63 downto 32))&SLV32HEX(observed_response(31 downto 0))&","&
          SLV32HEX(golden(63 downto 32))&SLV32HEX(golden(31 downto 0))&","&
          SLV32HEX(unloaded_response(63 downto 32))&SLV32HEX(unloaded_response(31 downto 0))&",PASS";
      end if;
      if pattern_count=1 then irq<=(others=>'1');nmi<='1';bus_error<='0';end if;
    end loop;
    check(shifts=PATTERNS*64 and unloads=PATTERNS*64 and captures=PATTERNS,"exact non-overlapped scan/capture/unload totals");
    if ENTRY_NS=200 then
      check(mem_attempts>0,"non-vacuous pending memory write suppression");
    else
      check(reg_attempts>0,"non-vacuous register-file write suppression");
    end if;
    check(protected_width>4000,"full GPR/CP0/TLB/pipeline storage observation");
    report "[PASS] real core protected-state hold, all CPU phases, write suppression and interrupt/exception isolation";
    report "[ISOLATION] "&integer'image(protected_width)&","&integer'image(state_changes)&","&
      integer'image(mem_attempts)&","&integer'image(memory_writes-writes_before)&","&
      integer'image(reg_attempts)&","&integer'image(actual_register_writes);
    report "[SEQUENCE] "&integer'image(shifts)&","&integer'image(captures)&","&integer'image(unloads)&","&integer'image(pattern_count);
    event_id<=x"06";
    if ISOLATION_ONLY then
      -- Deliberately illegal simultaneous scan/capture while DONE must not shift.
      bad_command<='1';tick;check(protocol_error='1' and scan_state=expected,"illegal controls rejected without a shift");
      bad_command<='0';
    end if;
    exit_attempt<='1';event_id<=x"07";tick;
    check(isolation_ack='1' and protected_state=saved,"dropping test mode cannot resume a corrupt pipeline");
    -- Reset-only exit; both real cores restart under identical reset/input policy.
    rst<='0';irq<=(others=>'0');nmi<='0';bus_error<='1';exit_attempt<='0';fabric_idle<='0';
    wait for 1 ns;check(scan_state=x"0000000000000000" and isolation_ack='0',"asynchronous reset exits test mode");
    wait for 24 ns;rst<='1';event_id<=x"08";
    for k in 1 to 20 loop tick;end loop;
    check(test_mode='0' and isolation_ack='0',"functional restart after reset");
    report "[PASS] reset-only exit and functional restart against original core";
    report "[ENGINE_COMPLETE] processor at "&time'image(now);
    finished<=true;wait;
  end process;
end architecture;
