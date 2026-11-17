library ieee;
use ieee.std_logic_1164.all;
use work.p_WIRES.all;
-- OOC synthesis boundary for the same 64-bit IF/RF bank used in the processor.
-- This is an alternative top, not an additional scan chain in core_scan_test.
entity phase5a_ifrf_subsystem is
  port(clk,rst,ld,scan_enable : in std_logic;
       pc_d,instr : in reg32;pc_q,rf_instr : out reg32;
       scan_out,scan_feedback,pattern_done : out std_logic);
end entity;
architecture rtl of phase5a_ifrf_subsystem is
  signal active_reset,raw,current_bit,future1,future2,serial,feedback,valid : std_logic;
  signal state : std_logic_vector(15 downto 0);
  signal mode_select,active_mode : std_logic_vector(1 downto 0);
  signal count : natural;
begin
  active_reset<=not rst;scan_feedback<=feedback;
  lfsr: entity work.lfsr_16 port map(clk,active_reset,scan_enable,raw,state);
  phase: entity work.phase_shifter port map(state,current_bit,future1,future2);
  control: entity work.basic_controller generic map(64,20)
    port map(clk,active_reset,scan_enable,mode_select,count,pattern_done);
  plpf: entity work.plpf_dynamic
    port map(current_bit,future1,future2,feedback,mode_select,serial,active_mode,valid);
  bank: entity work.reg_IF_RF_scan
    port map(clk,rst,ld,pc_d,pc_q,instr,rf_instr,scan_enable,serial,scan_out,feedback);
end architecture;
