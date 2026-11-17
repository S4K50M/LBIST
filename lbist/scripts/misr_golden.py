"""Independent MSB-first polynomial long-division reference; no DUT signatures."""
import argparse,csv,json,random
from pathlib import Path
POLYNOMIAL=0x11021
def signature(bits,seed=0):
    remainder=seed
    for bit in bits:
        remainder=(remainder<<1) ^ (int(bit)<<16)
        if remainder&0x10000:remainder^=POLYNOMIAL
    return remainder
def responses(words,seed=0,width=64):
    result=[]
    for word in words:
        assert int(word,16)<(1<<width)
        seed=signature(format(int(word,16),f"0{width}b"),seed);result.append(seed)
    return result
def unit():
    r=random.Random(20261118)
    vectors=["0"*256,"1"*256,"01"*128,("1"+"0"*15)*16,"".join(str(r.randrange(2)) for _ in range(256))]
    root=Path(__file__).resolve().parents[2]
    decl="\n".join(f'constant V{i}:std_logic_vector(0 to 255):="{v}";' for i,v in enumerate(vectors))
    statements=[]
    for i,v in enumerate(vectors):
        statements.append(f"""clear<='1';tick;clear<='0';
 for j in 0 to 255 loop response_bit<=V{i}(j);enable<='1';tick;
 enable<='0';saved:=signature;tick;assert signature=saved report "[FAIL] enable hold" severity failure;end loop;
 assert signature=x"{signature(v):04X}" report "[FAIL] Python unit signature {i}" severity failure;
 report "[UNIT] {i},{signature(v):04X},256,PASS";""")
    text="""library ieee;use ieee.std_logic_1164.all;
entity tb_misr_16 is port(test_done:out boolean);end;
architecture test of tb_misr_16 is
signal clk:std_logic:='0';signal rst:std_logic:='0';
signal enable,clear,response_bit:std_logic:='0';signal signature:std_logic_vector(15 downto 0);
signal finished:boolean:=false;
"""+decl+"""
begin
test_done<=finished;
process begin while not finished loop clk<='0';wait for 5 ns;clk<='1';wait for 5 ns;end loop;wait;end process;
d:entity work.misr_16 port map(clk,rst,enable,clear,response_bit,signature);
process variable saved:std_logic_vector(15 downto 0);
procedure tick is begin wait until rising_edge(clk);wait for 1 ns;wait until falling_edge(clk);end;
begin
wait for 2 ns;assert signature=x"0000" report "[FAIL] async reset" severity failure;
rst<='1';tick;
"""+ "\n".join(statements)+"""
clear<='1';enable<='1';response_bit<='1';tick;
assert signature=x"0000" report "[FAIL] clear priority" severity failure;
report "[TB_COMPLETE] tb_misr_16 at "&time'image(now);finished<=true;wait;end process;
process begin wait until finished for 200 us;assert finished report "[FAIL] watchdog" severity failure;wait;end process;
end;
"""
    (root/"lbist/tb/tb_misr_16.vhd").write_text(text)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--unit",action="store_true");p.add_argument("--responses")
    p.add_argument("--seed",type=lambda s:int(s,0),default=0)
    p.add_argument("--polynomial",type=lambda s:int(s,0),default=0x11021)
    p.add_argument("--patterns",type=int);p.add_argument("--bits-per-response",type=int,default=64)
    a=p.parse_args()
    if a.unit:unit()
    if a.responses:
        assert 0<=a.seed<65536 and a.polynomial.bit_length()==17 and a.polynomial&1
        POLYNOMIAL=a.polynomial
        words=json.loads(Path(a.responses).read_text())
        if a.patterns is not None:
            assert 0<a.patterns<=len(words);words=words[:a.patterns]
        s=responses(words,a.seed,a.bits_per_response)
        print(json.dumps(dict(Polynomial=hex(POLYNOMIAL),Seed=a.seed,Signatures=[f"{v:04X}" for v in s],Bits=len(words)*a.bits_per_response)))
