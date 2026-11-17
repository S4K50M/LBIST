library ieee;use ieee.std_logic_1164.all;use ieee.numeric_std.all;
entity lbist_pattern_router is
 generic(BETA:natural:=20;SWAP_BETA:natural:=16);
 port(clk,rst,scan_enable,is_unload,scan_feedback:in std_logic;
 approach_select:in std_logic_vector(2 downto 0);
 scan_in:out std_logic;mode_select:out std_logic_vector(1 downto 0);
 generator_state:out std_logic_vector(15 downto 0);shift_count:out natural;configuration_valid:out std_logic);
end;
architecture rtl of lbist_pattern_router is
 function basic_beta return natural is begin return BETA-(BETA mod 2);end;
 signal reset_hi,raw,c,f1,f2,en_s,en_u,serial,valid,configuration_ok:std_logic;
 signal state:std_logic_vector(15 downto 0);
 signal basic,mode,ss,su,ms,mu:std_logic_vector(1 downto 0);
 signal bpos:natural;
begin
 reset_hi<=not rst;en_s<=scan_enable and not is_unload;en_u<=scan_enable and is_unload;
 l:entity work.lfsr_16 port map(clk,reset_hi,scan_enable,raw,state);
 p:entity work.phase_shifter port map(state,c,f1,f2);
 b:entity work.basic_controller generic map(64,basic_beta) port map(clk,reset_hi,scan_enable,basic,bpos,open);
 -- Separate scheduling lanes: each existing controller counts one 64-bit word
 -- per captured pattern, on its own SHIFT or UNLOAD edges. LFSR advances on both.
 s0:entity work.swap_controller generic map(64,SWAP_BETA,1)
  port map(clk,reset_hi,en_s,ss,open,open,open,open,open);
 s1:entity work.swap_controller generic map(64,SWAP_BETA,1)
  port map(clk,reset_hi,en_u,su,open,open,open,open,open);
 m0:entity work.moving_controller generic map(64,BETA,1,0)
  port map(clk,reset_hi,en_s,ms,open,open,open,open,open,open);
 m1:entity work.moving_controller generic map(64,BETA,1,0)
  port map(clk,reset_hi,en_u,mu,open,open,open,open,open,open);
 mode<="11" when approach_select="000" else "00" when approach_select="001"
  else basic when approach_select="010" else ss when approach_select="011" and is_unload='0'
  else su when approach_select="011" else ms when approach_select="100" and is_unload='0'
  else mu when approach_select="100" else "00";
 f:entity work.plpf_dynamic port map(c,f1,f2,scan_feedback,mode,serial,open,valid);
 configuration_ok<='1' when unsigned(approach_select)<=4 and not(approach_select="010" and BETA mod 2/=0) else '0';
 configuration_valid<=configuration_ok;
 scan_in<=serial when configuration_ok='1' else '0';
 mode_select<=mode;generator_state<=state;shift_count<=bpos;
end;
