library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
-- Explicit, non-overlapped 64 SHIFT / one CAPTURE / 64 UNLOAD schedule.
-- Both SHIFT and UNLOAD advance the external PRNG/Basic controller.
-- DONE and aborted tests remain isolated until asynchronous active-low reset.
entity lbist_test_controller is
  generic(CHAIN_LENGTH : positive:=64; NUM_PATTERNS : positive:=256);
  port(clk,rst,start,pause,abort_test,isolation_ack,capture_ready : in std_logic;
       test_mode,scan_enable,capture_enable,pattern_done,test_done,error_status : out std_logic;
       current_state : out std_logic_vector(2 downto 0);
       shift_count,pattern_count : out natural);
end entity;
architecture rtl of lbist_test_controller is
  type state_t is (NORMAL,TEST_IDLE,SHIFT,CAPTURE,UNLOAD,TEST_DONE_STATE);
  signal state : state_t:=NORMAL;
  signal position : natural range 0 to CHAIN_LENGTH-1:=0;
  signal patterns : natural range 0 to NUM_PATTERNS:=0;
  signal failed : std_logic:='0';
begin
  assert CHAIN_LENGTH<=4096 and NUM_PATTERNS<=4096 report "[CONFIG_ERROR] controller bounds 1..4096" severity failure;
  current_state<=std_logic_vector(to_unsigned(state_t'pos(state),3));
  test_mode<='0' when state=NORMAL else '1';
  scan_enable<='1' when (state=SHIFT or state=UNLOAD) and pause='0' and abort_test='0' and start='0' else '0';
  capture_enable<='1' when state=CAPTURE and pause='0' and abort_test='0' and start='0' and capture_ready='1' else '0';
  test_done<='1' when state=TEST_DONE_STATE else '0';
  error_status<=failed;shift_count<=position;pattern_count<=patterns;
  process(clk,rst)
  begin
    if rst='0' then state<=NORMAL;position<=0;patterns<=0;failed<='0';pattern_done<='0';
    elsif rising_edge(clk) then
      pattern_done<='0';
      if state/=NORMAL and state/=TEST_DONE_STATE and (abort_test='1' or start='1') then
        state<=TEST_DONE_STATE;failed<='1';
      elsif pause='0' then
        case state is
          when NORMAL =>
            if start='1' then state<=TEST_IDLE;position<=0;patterns<=0;end if;
          when TEST_IDLE =>
            if isolation_ack='1' then state<=SHIFT;end if;
          when SHIFT =>
            if position=CHAIN_LENGTH-1 then position<=0;state<=CAPTURE;
            else position<=position+1;end if;
          when CAPTURE =>
            if capture_ready='1' then state<=UNLOAD;position<=0;end if;
          when UNLOAD =>
            if position=CHAIN_LENGTH-1 then
              position<=0;patterns<=patterns+1;pattern_done<='1';
              if patterns=NUM_PATTERNS-1 then state<=TEST_DONE_STATE;else state<=SHIFT;end if;
            else position<=position+1;end if;
          when TEST_DONE_STATE => null;
        end case;
      end if;
    end if;
  end process;
end architecture;
