library ieee;use ieee.std_logic_1164.all;use ieee.numeric_std.all;
-- Serial-input MISR: x^16+x^12+x^5+1; MSB-first, seed zero.
-- feedback=q(15) XOR response; q'=q<<1 XOR (1021 if feedback else 0).
-- Active-low async reset > synchronous clear > enable > hold.
entity misr_16 is
 port(clk,rst,enable,clear,response_bit:in std_logic;signature:out std_logic_vector(15 downto 0));
end;
architecture rtl of misr_16 is signal q:unsigned(15 downto 0):=(others=>'0');
begin
 signature<=std_logic_vector(q);
 process(clk,rst) begin
 if rst='0' then q<=(others=>'0');
 elsif rising_edge(clk) then
 if clear='1' then q<=(others=>'0');
 elsif enable='1' then
 if (q(15) xor response_bit)='1' then q<=shift_left(q,1) xor x"1021";
 else q<=shift_left(q,1);end if;
 end if;end if;end process;
end;
