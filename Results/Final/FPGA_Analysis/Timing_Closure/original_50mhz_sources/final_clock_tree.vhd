library ieee;use ieee.std_logic_1164.all;
library unisim;use unisim.vcomponents.all;
-- 100 MHz primary -> related 50 MHz processor phases.
-- Relative to clk rising at 0 ns: phi1=15..20, phi2=0..5, phi3=5..10 ns.
entity final_clock_tree is port(board_clk,reset_button:in std_logic;clk,phi1,phi2,phi3,rst:out std_logic);end;
architecture rtl of final_clock_tree is
 signal fb,fb_buf,c0,c1,c2,c3,cpu,locked:std_logic;
 signal reset_sync:std_logic_vector(1 downto 0):=(others=>'0');
 attribute ASYNC_REG:string;attribute ASYNC_REG of reset_sync:signal is "TRUE";
begin
 mmcm:MMCME2_BASE generic map(BANDWIDTH=>"OPTIMIZED",CLKIN1_PERIOD=>10.0,
  DIVCLK_DIVIDE=>1,CLKFBOUT_MULT_F=>10.0,CLKOUT0_DIVIDE_F=>20.0,
  CLKOUT1_DIVIDE=>20,CLKOUT1_DUTY_CYCLE=>0.25,CLKOUT1_PHASE=>270.0,
  CLKOUT2_DIVIDE=>20,CLKOUT2_DUTY_CYCLE=>0.25,CLKOUT2_PHASE=>0.0,
  CLKOUT3_DIVIDE=>20,CLKOUT3_DUTY_CYCLE=>0.25,CLKOUT3_PHASE=>90.0)
 port map(CLKIN1=>board_clk,CLKFBIN=>fb_buf,RST=>reset_button,PWRDWN=>'0',
  CLKFBOUT=>fb,CLKFBOUTB=>open,CLKOUT0=>c0,CLKOUT0B=>open,CLKOUT1=>c1,CLKOUT1B=>open,
  CLKOUT2=>c2,CLKOUT2B=>open,CLKOUT3=>c3,CLKOUT3B=>open,CLKOUT4=>open,CLKOUT5=>open,CLKOUT6=>open,LOCKED=>locked);
 feedback_buffer:BUFG port map(I=>fb,O=>fb_buf);
 u_clk:BUFG port map(I=>c0,O=>cpu);
 u_phi1:BUFG port map(I=>c1,O=>phi1);u_phi2:BUFG port map(I=>c2,O=>phi2);u_phi3:BUFG port map(I=>c3,O=>phi3);
 clk<=cpu;
 process(cpu,locked,reset_button) begin
  if locked='0' or reset_button='1' then reset_sync<=(others=>'0');
  elsif rising_edge(cpu) then reset_sync<=reset_sync(0)&'1';end if;
 end process;
 rst<=reset_sync(1);
end;
