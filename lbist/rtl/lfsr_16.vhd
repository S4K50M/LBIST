library ieee;
use ieee.std_logic_1164.all;

-- State(i)=T[j+i], output=T[j]=state(0). Shift toward bit 0.
-- P(x)=x^16+x^15+x^13+x^4+1 implies
-- T[j+16]=T[j+15] xor T[j+13] xor T[j+4] xor T[j].
entity lfsr_16 is
  generic (SEED : std_logic_vector(15 downto 0) := x"AAAA");
  port (clk, rst, enable : in std_logic;
        random_bit : out std_logic;
        state_out : out std_logic_vector(15 downto 0));
end entity;
architecture rtl of lfsr_16 is
  function safe_seed(s : std_logic_vector) return std_logic_vector is
  begin
    if s = x"0000" then return x"AAAA"; end if;
    for i in s'range loop
      if s(i)/='0' and s(i)/='1' then return x"AAAA"; end if;
    end loop;
    return s;
  end;
  signal state : std_logic_vector(15 downto 0);
begin
  process(clk, rst)
  begin
    if rst='1' then state <= safe_seed(SEED);
    elsif rising_edge(clk) then
      if enable='1' then
        if state=x"0000" then state <= safe_seed(SEED);
        else state <= (state(15) xor state(13) xor state(4) xor state(0)) & state(15 downto 1);
        end if;
      end if;
    end if;
  end process;
  random_bit <= state(0);
  state_out <= state;
end architecture;
