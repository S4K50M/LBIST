"""Record source/configuration provenance without changing prior phases."""
from pathlib import Path
import csv,hashlib
R=Path(__file__).resolve().parents[2];O=R/"Results/Phase6A/reports"
def main():
 paths=list((R/"lbist/tb").glob("*phase6a*.vhd"))
 paths+=list((R/"lbist/scripts").glob("*phase6a*.py"))+list((R/"lbist/scripts").glob("*phase6a*.tcl"))
 paths += [R/"lbist/rtl"/n for n in ["lbist_pattern_router.vhd","phase6a_safe_misr.vhd","phase6a_controlled_misr.vhd"]]
 paths += [R/"docs/phase6a_design.md",R/"Results/Phase6A/README.md",R/"Results/Phase6A/configs.json",R/"Results/Phase6A/feasibility.json"]
 with (O/"source_manifest.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["File","Bytes","SHA256"]);w.writeheader()
  for p in sorted(set(paths)):
   b=p.read_bytes();w.writerow(dict(File=p.relative_to(R).as_posix(),Bytes=len(b),SHA256=hashlib.sha256(b).hexdigest()))
 program=(R/"cMIPS/prog.bin").read_bytes();digest=hashlib.sha256(program).hexdigest()
 assert digest=="fbb3da2760faf41147f751b857cb8b2c0105cec1e03fd824fa64387f45abae50"
 with (O/"program_provenance.csv").open("w",newline="") as f:
  fields=["Program","Bytes","SHA256","LFSRSeed","MISRSeed","Polynomial","ChainLength","Patterns","ClockNS","EntryNS"]
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  w.writerow(dict(Program="cMIPS/prog.bin",Bytes=len(program),SHA256=digest,LFSRSeed="AAAA",MISRSeed=0,Polynomial="11021",ChainLength=64,Patterns=256,ClockNS=20,EntryNS=380))
 print("Phase6A source/configuration/program SHA-256 provenance recorded.")
if __name__=="__main__":main()
