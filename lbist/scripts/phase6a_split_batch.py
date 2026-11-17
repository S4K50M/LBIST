"""Split native report records by their actual instance hierarchy; fail closed."""
from pathlib import Path
import re,csv,sys,json
from phase6a_results import load,O
def split(cid,first,last):
 c=json.loads((O/"configs.json").read_text())[cid]
 tag=f"batch_c{cid}_{first}_{last}";folder=O/"Batch"
 summary=next(csv.DictReader((folder/"reports"/(tag+".csv")).open()))
 assert summary["Result"]=="PASS"
 text=(folder/"logs"/(tag+".log")).read_text()
 assert "[TB_COMPLETE] tb_phase6a_batch" in text and "[FAIL]" not in text and "Failure:" not in text
 records={i:[] for i in range(first,last+1)};lines=text.splitlines()
 for i,line in enumerate(lines[:-1]):
  if not line.startswith("Note: "):continue
  metadata=lines[i+1]
  match=re.search(r"instances\((\d+)\)/engine/",metadata.replace("\\",""))
  if match:
   fid=int(match[1]);assert fid in records
   records[fid].extend([line,metadata])
 for fid,parts in records.items():
  child="\n".join(parts)+"\n"
  assert child.count("[CAPTURE]")==child.count("[SIGNATURE]")==256
  assert "[ENGINE_COMPLETE]" in child and f"[CONFIG] {cid},{c['Approach']},{c['Beta']}" in child
  case=f"c{cid}_f{fid}";out=O/"Faults";(out/"logs").mkdir(parents=True,exist_ok=True)
  (out/"logs"/(case+".log")).write_text(child)
  row=dict(Case=case,Testbench="tb_phase6a_batch",Group="Faults",Result="PASS",
           CompletionTime=summary["CompletionTime"],Capture=0,WDBBytes=0,
           NativeLog=f"Results/Phase6A/Batch/logs/{tag}.log",Instance=f"/tb_phase6a_batch/instances({fid})/engine")
  with (out/"reports"/(case+".csv")).open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
  load(c,fid) # independent response, CRC, activity, configuration and isolation checks
  print("INDEPENDENT REAL PROCESSOR CASE PASS:",case)
if __name__=="__main__":split(*map(int,sys.argv[1:]))
