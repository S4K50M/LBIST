-- Generated from cMIPS/prog.bin; no placeholder program is substituted.
-- SHA256: fbb3da2760faf41147f751b857cb8b2c0105cec1e03fd824fa64387f45abae50
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
package phase5a_rom_pkg is
  type words_t is array(0 to 255) of reg32;
  constant PROGRAM_WORDS : words_t := (
    0 => x"3C0F0004",
    1 => x"35EF0010",
    2 => x"3C103C00",
    3 => x"2003FFF6",
    4 => x"34050004",
    5 => x"00000000",
    6 => x"ADE30004",
    7 => x"20630001",
    8 => x"8DE40004",
    9 => x"01E57820",
    10 => x"AE040000",
    11 => x"1460FFFA",
    12 => x"00000000",
    13 => x"00000000",
    14 => x"42000020",
    15 => x"00000000",
    16 => x"00000000",
    17 => x"00000000",
    18 => x"00000000",
    19 => x"00000000",
    others => x"00000000");
  function load_program return words_t;
  function rom_word(words : words_t; address : reg32) return reg32;
end package;
package body phase5a_rom_pkg is
  function load_program return words_t is
  begin return PROGRAM_WORDS; end;
  function rom_word(words : words_t; address : reg32) return reg32 is
  begin
    if is_x(address) then return x"00000000";end if;
    if unsigned(address)<1024 then return words(to_integer(unsigned(address(9 downto 2))));end if;
    return x"00000000";
  end;
end package body;
