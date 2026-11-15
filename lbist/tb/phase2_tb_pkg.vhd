library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
package phase2_tb_pkg is
  type bit_sequence is array(natural range <>) of std_logic;
  function sequence_model(seed : std_logic_vector(15 downto 0)) return bit_sequence;
  function window(s : bit_sequence; j : natural) return std_logic_vector;
  function filtered(c, f1, f2, past : std_logic; mode : std_logic_vector(1 downto 0)) return std_logic;
  function mode_code(n : positive) return std_logic_vector;
  function expected_rate(n : positive) return real;
  procedure check(ok : boolean; message_text : string);
end package;
package body phase2_tb_pkg is
  function sequence_model(seed : std_logic_vector(15 downto 0)) return bit_sequence is
    variable a : bit_sequence(0 to 65552);
  begin
    -- Mathematical sequence model, not a copy of the RTL shift expression.
    -- Coefficients of P give T[k]+T[k-1]+T[k-3]+T[k-12]+T[k-16]=0 in GF(2).
    for i in 0 to 15 loop a(i):=seed(i); end loop;
    for k in 16 to a'high loop a(k):=a(k-1) xor a(k-3) xor a(k-12) xor a(k-16); end loop;
    return a;
  end;
  function window(s : bit_sequence; j : natural) return std_logic_vector is
    variable v : std_logic_vector(15 downto 0);
  begin
    for i in 0 to 15 loop v(i):=s(j+i); end loop; return v;
  end;
  function filtered(c, f1, f2, past : std_logic; mode : std_logic_vector(1 downto 0)) return std_logic is
    variable unanimous : boolean;
  begin
    if mode="11" then return c; end if;
    if mode/="01" and mode/="00" then return past; end if;
    -- Independent behavioral rule: change history only if all n bits
    -- agree on the opposite value. Otherwise retain the scan-stage Q.
    unanimous := c=f1;
    if mode="00" then unanimous:=unanimous and c=f2; end if;
    if unanimous then return c; else return past; end if;
  end;
  function mode_code(n : positive) return std_logic_vector is
  begin
    case n is when 1=>return "11"; when 2=>return "01"; when others=>return "00"; end case;
  end;
  function expected_rate(n : positive) return real is
  begin
    case n is when 1=>return 0.5; when 2=>return 1.0/6.0; when others=>return 1.0/14.0; end case;
  end;
  procedure check(ok : boolean; message_text : string) is
  begin
    assert ok report "[FAIL] " & message_text severity failure;
  end;
end package body;
