library ieee;
use ieee.std_logic_1164.all;
-- Controller changes mode on the inactive edge (or meets setup/hold).
-- Feedback MUST be the scan-input-stage FF Q, not scan-out or raw LFSR.
-- No registers: mode changes never consume a shift cycle or reset LFSR.
entity plpf_dynamic is
  port (current_bit, future1, future2, past_bit : in std_logic;
        mode_select : in std_logic_vector(1 downto 0);
        scan_in : out std_logic;
        active_mode : out std_logic_vector(1 downto 0);
        mode_valid : out std_logic);
end entity;
architecture rtl of plpf_dynamic is
  signal all_one, any_one : std_logic;
begin
  -- Share the two-input reductions across n=2 and n=3.
  all_one <= current_bit and future1;
  any_one <= current_bit or future1;
  active_mode <= mode_select;
  process(current_bit, future2, past_bit, mode_select, all_one, any_one)
  begin
    scan_in <= past_bit; mode_valid <= '1';
    case mode_select is
      when "11" => scan_in <= current_bit;
      when "01" =>
        if past_bit='0' then scan_in <= all_one;
        elsif past_bit='1' then scan_in <= any_one;
        else scan_in <= 'X'; end if;
      when "00" =>
        if past_bit='0' then scan_in <= all_one and future2;
        elsif past_bit='1' then scan_in <= any_one or future2;
        else scan_in <= 'X'; end if;
      when others => mode_valid <= '0';
    end case;
  end process;
end architecture;
