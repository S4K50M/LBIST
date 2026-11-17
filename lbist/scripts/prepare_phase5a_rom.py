"""Create a simulation ROM constant from the existing, unchanged program image."""
from pathlib import Path
import hashlib
import struct

ROOT = Path(__file__).resolve().parents[2]
def prepare():
    data = (ROOT / "cMIPS/prog.bin").read_bytes()
    assert data and len(data) % 4 == 0 and len(data) <= 1024
    words = struct.unpack("<" + "I" * (len(data) // 4), data)
    digest = hashlib.sha256(data).hexdigest()
    text = """-- Generated from cMIPS/prog.bin; no placeholder program is substituted.
-- SHA256: """ + digest + """
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.p_WIRES.all;
package phase5a_rom_pkg is
  type words_t is array(0 to 255) of reg32;
  constant PROGRAM_WORDS : words_t := (
""" + ",\n".join(f'    {i} => x"{word:08X}"' for i, word in enumerate(words)) + """,
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
"""
    (ROOT / "lbist/tb/phase5a_rom_pkg.vhd").write_text(text)
    print(f"ROM: {len(words)} original words; SHA256 {digest}")
if __name__ == "__main__":
    prepare()
