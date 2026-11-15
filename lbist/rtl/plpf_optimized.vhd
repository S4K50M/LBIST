library ieee;
use ieee.std_logic_1164.all;
entity plpf_optimized is
  port (current_bit, future1, future2, past_bit : in std_logic;
        mode : in std_logic_vector(1 downto 0);
        scan_in, mode_valid : out std_logic);
end entity;
architecture rtl of plpf_optimized is
begin
  process(current_bit, future1, future2, past_bit, mode)
  begin
    scan_in <= past_bit; mode_valid <= '1';
    case mode is
      when "11" => scan_in <= current_bit;
      when "01" =>
        if past_bit='0' then scan_in <= current_bit and future1;
        elsif past_bit='1' then scan_in <= current_bit or future1;
        else scan_in <= 'X'; end if;
      when "00" =>
        if past_bit='0' then scan_in <= current_bit and future1 and future2;
        elsif past_bit='1' then scan_in <= current_bit or future1 or future2;
        else scan_in <= 'X'; end if;
      when others => mode_valid <= '0'; -- invalid: retain input-stage value
    end case;
  end process;
end architecture;
