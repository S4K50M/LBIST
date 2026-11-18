"""Generate simulation-only timing variants; original processor RTL is unchanged."""
from pathlib import Path
from decimal import Decimal
import sys,re,json,hashlib
R=Path(__file__).resolve().parents[2];O=R/'Results/Final/FPGA_Analysis/Timing_Closure'
def main():
 m,d=map(int,sys.argv[1:]);period=Decimal(10)*d/m;scale=period/20
 dest=O/'generated'/f'm{m}_d{d}';dest.mkdir(parents=True,exist_ok=True)
 def scaled(s):
  def repl(match):
   value,unit=match.groups()
   return f'{Decimal(value)*scale:f} {unit}' if unit!='ms' else match[0]
  return re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s+(ns|ps|us|ms)\b',repl,s)
 manifest=[]
 for name in ['final_activity_check','phase6a_processor_check','tb_final_functional_activity']:
  src=R/'lbist/tb'/(name+'.vhd');target=dest/(name+'.vhd');target.write_text(scaled(src.read_text()))
  manifest.append(dict(Source=str(src.relative_to(R)),Target=str(target.relative_to(R)),SourceSHA256=hashlib.sha256(src.read_bytes()).hexdigest(),Scale=str(scale)))
 src=R/'cMIPS/vhdl/packageWires.vhd';s=src.read_text()
 s,n=re.subn(r'(constant CLOCK_PER\s*: time := )20 ns;',rf'\g<1>{period:f} ns;',s);assert n==1
 (dest/'packageWires.vhd').write_text(s)
 manifest.append(dict(Source=str(src.relative_to(R)),Target=str((dest/'packageWires.vhd').relative_to(R)),SourceSHA256=hashlib.sha256(src.read_bytes()).hexdigest(),Change='CLOCK_PER only',Scale=str(scale)))
 # The legacy simulation PLL has two CLOCK_PER/8 waits. Split a fractional
 # picosecond between its low/high halves so the quarter-period does not drift
 # away from the main clock at XSim's 1ps resolution. No CPU RTL is changed.
 src=R/'cMIPS/vhdl/altera.vhd';s=src.read_text()
 old="clk4x <= '0';\n    wait for CLOCK_PER / 8;\n    clk4x <= '1';\n    wait for CLOCK_PER / 8;"
 new="clk4x <= '0';\n    wait for (CLOCK_PER / (8 ps)) * 1 ps;\n    clk4x <= '1';\n    wait for CLOCK_PER / 4 - (CLOCK_PER / (8 ps)) * 1 ps;"
 assert old in s;s=s.replace(old,new,1);(dest/'altera.vhd').write_text(s)
 manifest.append(dict(Source=str(src.relative_to(R)),Target=str((dest/'altera.vhd').relative_to(R)),SourceSHA256=hashlib.sha256(src.read_bytes()).hexdigest(),Change='Simulation PLL fractional-picosecond half ticks only',Scale=str(scale)))
 for item in manifest:item['TargetSHA256']=hashlib.sha256((R/item['Target']).read_bytes()).hexdigest()
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
 (dest/'clock.tcl').write_text(f'set timing_mult {m}\nset timing_divide {d}\nset timing_period {period:f}\nset timing_scale {scale:f}\nset timing_tag m{m}_d{d}\n')
 print('Generated timing-only fixtures:',dest,'period',period,'ns; watchdog remains 20 ms.')
if __name__=='__main__':main()
