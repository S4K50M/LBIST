library ieee;use ieee.std_logic_1164.all;
package phase6a_golden_pkg is
type signatures_t is array(natural range <>) of std_logic_vector(15 downto 0);
constant GOLDENS:signatures_t:=(0=>x"9A6A",1=>x"5DCB",2=>x"AFBC",3=>x"9C7F",4=>x"F21E",5=>x"5DCB",6=>x"8D9F",7=>x"55AE",8=>x"E24D",9=>x"C795",10=>x"5AEC",11=>x"6DB2");end;
