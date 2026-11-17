"""Only completed native experiments contribute to coverage and WTM."""
from pathlib import Path
import csv,re,json,hashlib,argparse
from build_phase6a import model,mode
from misr_golden import responses,signature
from phase3_wtm_optimizer import describe
from phase5a_trace import Phase5Trace,verify_preview
from render_waveform_previews import render_window
R=Path(__file__).resolve().parents[2];O=R/"Results/Phase6A";NAMES=["Direct","Constant_n3","Basic","Swap","Moving"]
def write(name,rows):
 p=O/"reports"/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)) if rows else ["Result"]);w.writeheader();w.writerows(rows)
def load(c,f):
 tag=f"c{c['ID']}_f{f}";folder=O/"Faults"
 row=next(csv.DictReader((folder/"reports"/(tag+".csv")).open()))
 assert row["Result"]=="PASS" and int(row["CompletionTime"].split()[0])<100_000_000_000
 text=(folder/"logs"/(tag+".log")).read_text()
 assert "[FAIL]" not in text and "Failure:" not in text
 completed=re.search(r"\[ENGINE_COMPLETE\] processor at ([0-9]+ ps)",text)
 assert completed and completed[1]==row["CompletionTime"],"actual instance completion time"
 assert f"[CONFIG] {c['ID']},{c['Approach']},{c['Beta']}" in text
 captures=re.findall(r"\[CAPTURE\] (\d+),([0-9a-fA-F]+),([0-9a-fA-F]+),([0-9a-fA-F]+),PASS",text)
 assert len(captures)==256 and [int(a) for a,_,_,_ in captures]==list(range(1,257))
 actual=[a.upper() for _,a,b,d in captures if a==b==d];assert len(actual)==256
 predicted,activity=model(c["Approach"],c["Beta"],f);assert actual==predicted
 sigs=re.findall(r"\[SIGNATURE\] (\d+),(\d+),([0-9A-Fa-f]+)",text)
 golden=responses(predicted)
 assert len(sigs)==256 and all(int(fid)==f and int(p)==i+1 and int(s,16)==golden[i] for i,(fid,p,s) in enumerate(sigs))
 assert "[SEQUENCE] 16384,256,16384,256" in text
 assert re.search(r"\[ISOLATION\] 4287,0,0,0,\d+,0",text)
 measured=tuple(map(int,re.search(r"\[ACTIVITY\] (\d+),(\d+),(\d+)",text).groups()))
 expected=(round(activity["MeasuredWTM"]*256*64*2080),round(activity["ScanFFSwitching"]*256*64*64),round(activity["SerialToggleRate"]*256*64))
 assert measured==expected,(tag,measured,expected)
 native_activity=dict(MeasuredWTM=measured[0]/(256*64*2080),ScanFFSwitching=measured[1]/(256*64*64),SerialToggleRate=measured[2]/(256*64))
 return actual,[int(s,16) for _,_,s in sigs],native_activity,row
def check_trace(trace,prefix,expected,safety=False):
 state=caps=bits=0;limit=8 if safety else 16384;wanted_caps=2 if safety else 256
 sig_name="q" if safety else "signature";valid_name="valid" if safety else "signature_valid"
 clocks={t for t,v in trace.values(prefix,"clk") if v=="1"}
 reset_events=[t for t,v in trace.values(prefix,"rst") if v=="0"]
 for t in sorted(clocks|set(reset_events)):
  read=lambda n,pre=False:trace.integer(prefix,n,t,pre)
  if read("rst")==0:state=caps=bits=0
  elif t in clocks:
   phase=read("phase" if safety else "test_phase",True)
   cap=read("ce" if safety else "capture_enable",True)
   unload=read("unload" if safety else "misr_enable",True)
   if cap:caps+=1
   if unload and phase==4 and read("err" if safety else "error_status",True)==0:
    state=signature([read("response" if safety else "scan_out",True)],state);bits+=1
  assert read(sig_name)==state,(prefix,t,"MISR pre-edge serial input and hold")
  valid=bool(read("rst") and read("done") and not read("err" if safety else "error_status")
             and caps==wanted_caps and bits==limit and read("phase" if safety else "test_phase")==5
             and read("pattern_index")==wanted_caps)
  assert read(valid_name)==int(valid),(prefix,t,"completion validity")
  assert read("match" if safety else "signature_match")==int(valid and state==expected)
  assert read("detected" if safety else "fault_detected")==int(valid and state!=expected)
 return len(clocks)
def main(partial=False):
 configs=json.loads((O/"configs.json").read_text());verification=[];campaign=[];coverage=[];wtm=[];gold=[];cycles=[];exposure=[];thresholds=[];evolution=[]
 for c in configs:
  cid=c["ID"];name=NAMES[c["Approach"]]
  try:words,gs,activity,row=load(c,0)
  except FileNotFoundError:
   verification.append(dict(Config=cid,Fault=0,Result="NOT_RUN"));continue
  gold.append(dict(Config=cid,Approach=name,Beta=c["Beta"],Signature=f"{gs[-1]:04X}",
   ExpectedSignature=f"{responses(model(c['Approach'],c['Beta'])[0])[-1]:04X}",ActualSignature=f"{gs[-1]:04X}",ResponseBits=16384,Result="PASS"))
  a=c["Approach"];estimated=0.5 if a==0 else 1/14 if a==1 else float(__import__("fractions").Fraction(describe(["","","basic","swap","moving"][a],64,c["Beta"],1)["EstimatedWTM"]))
  wtm.append(dict(Config=cid,Approach=name,Beta=c["Beta"],EstimatedWTM=estimated*100,MeasuredWTM=activity["MeasuredWTM"]*100,
                  SerialToggleRate=activity["SerialToggleRate"],ScanFFSwitching=activity["ScanFFSwitching"]))
  series=[]
  for fid in range(17):
   try:aw,sg,act,r=load(c,fid)
   except FileNotFoundError:
    verification.append(dict(Config=cid,Fault=fid,Result="NOT_RUN"));continue
   verification.append(dict(Config=cid,Approach=name,Beta=c["Beta"],Fault=fid,NativeTop=r["Testbench"],CompletionTime=r["CompletionTime"],Result="PASS"))
   cycles.append(dict(Config=cid,Fault=fid,SHIFT=16384,CAPTURE=256,UNLOAD=16384,Payload=33024,
     CompletionPS=int(r["CompletionTime"].split()[0]),OverheadPeriods=round(int(r["CompletionTime"].split()[0])/20000-33024,5),
     TotalClockEdges=int(r["CompletionTime"].split()[0])//20000,
     OverheadClockEdges=int(r["CompletionTime"].split()[0])//20000-33024,
     NonPauseOverheadEdges=int(r["CompletionTime"].split()[0])//20000-33024-3,PauseCycles=3))
   if fid==0:continue
   direct=[i+1 for i,(x,y) in enumerate(zip(aw,words)) if x!=y];mis=[i+1 for i,(x,y) in enumerate(zip(sg,gs)) if x!=y]
   campaign.append(dict(Config=cid,Approach=name,Beta=c["Beta"],FaultID=fid,DirectDetected=bool(direct),MISRDetected=sg[-1]!=gs[-1],
    FirstDirect=direct[0] if direct else "",FirstMISR=mis[0] if mis else "",Golden=f"{gs[-1]:04X}",Actual=f"{sg[-1]:04X}",
    Aliasing=bool(direct) and sg[-1]==gs[-1],ResponseBits=16384,PayloadCycles=33024,MeasuredWTM=act["MeasuredWTM"]*100,
    ScanFFSwitching=act["ScanFFSwitching"],SerialToggleRate=act["SerialToggleRate"],CompletionTime=r["CompletionTime"],Result="VALID"))
   series.append((direct,sg))
   if fid==1:
    evolution.extend(dict(Config=cid,Pattern=i+1,Golden=gs[i],Actual=sg[i]) for i in range(256))
   if cid==2:
    old=next(r for r in csv.DictReader((R/"Results/Phase5C/reports/fault_campaign.csv").open()) if int(r["FaultID"])==fid)
    assert old["FaultySignature"]==f"{sg[-1]:04X}","Basic original reproduction"
  if len(series)==16:
   for target in [25,50,75,100]:
    hit=next((n for n in range(1,257) if 100*sum(s[n-1]!=gs[n-1] for _,s in series)/16>=target),None)
    thresholds.append(dict(Config=cid,Approach=name,CoverageTarget=target,Patterns=hit or "UNREACHED",Cycles=129*hit if hit else "UNREACHED"))
   for n in [1,4,8,16,32,64,128,256]:
    coverage.append(dict(Config=cid,Approach=name,Patterns=n,Eligible=16,DirectCoverage=100*sum(any(i<=n for i in ds) for ds,_ in series)/16,
      MISRCoverage=100*sum(s[n-1]!=gs[n-1] for _,s in series)/16,Cycles=n*129))
  for position in range(64):
   exposure.append(dict(Config=cid,Approach=name,PhysicalPosition=position,HighExposure=sum(mode(a,c["Beta"],p,63-position)==3 for p in range(256))/256))
 write("phase6a_verification_summary.csv",verification);write("phase6a_fault_campaign.csv",campaign)
 write("phase6a_fault_coverage.csv",coverage);write("phase6a_wtm_comparison.csv",wtm);write("phase6a_golden_signatures.csv",gold)
 write("phase6a_detection_latency.csv",campaign);write("phase6a_misr_aliasing.csv",campaign);write("phase6a_test_cycles.csv",cycles)
 write("phase6a_exposure.csv",exposure)
 write("phase6a_thresholds.csv",thresholds);write("phase6a_signature_evolution.csv",evolution)
 inv=list(csv.DictReader((R/"Results/Phase5C/reports/fault_inventory.csv").open()))
 for fault in inv:
  bit=int(fault["Bit"]);stuck=int(fault["FaultType"]=="SA1")
  instruction=fault["Signal"]=="instruction_input"
  fault["ActivationCondition"]=f"functional net bit {bit} differs from {stuck}"
  fault["PropagationPath"]="ordinary instruction input to IF/RF instruction half" if instruction else "aligned scan operand through original PC+4 adder to IF/RF PC half"
  fault["Observation"]="actual MSB-first serial unload and zero-seeded polynomial MISR"
  fault["SupportedStimulus"]="held ROM word 1460FFFA" if instruction else "actual routed scan-loaded PC operand"
  fault["ExcitationLimit"]="not excited by held instruction" if instruction and ((0x1460fffa>>bit)&1)==stuck else "measure response outcome per approach"
 write("phase6a_fault_inventory.csv",inv)
 feasibility=json.loads((O/"feasibility.json").read_text())
 for f in feasibility:
  f["MeasuredWTM"]=next((r["MeasuredWTM"] for r in wtm if r["Config"]==f["Config"]),"NOT_RUN")
  f["MeasuredErrorPP"]=abs(f["MeasuredWTM"]-f["Target"]) if isinstance(f["MeasuredWTM"],float) else ""
  f["MeasuredMatchTolerancePP"]=0.5
  f["MeasuredMatched"]=bool(f["Feasible"] and isinstance(f["MeasuredErrorPP"],float) and f["MeasuredErrorPP"]<=0.5)
 write("phase6a_feasibility.csv",feasibility)
 matched=[]
 for target,selection,ids in [(10,"optimizer",[5,7,9]),(15,"optimizer",[6,8,10]),(20,"optimizer",[2,11]),(20,"measured_calibration",[2,4])]:
  values=[r["MeasuredWTM"] for r in wtm if r["Config"] in ids]
  if len(values)!=len(ids):continue
  spread=max(values)-min(values);near=all(abs(v-target)<=0.5 for v in values)
  matched.append(dict(Target=target,Selection=selection,Configurations=";".join(map(str,ids)),
   MinMeasuredWTM=min(values),MaxMeasuredWTM=max(values),SpreadPP=spread,PairwiseTolerancePP=0.5,
   PairwiseMatched=spread<=0.5,AllWithinTargetTolerance=near,
   Status="MATCHED_FEASIBLE" if spread<=0.5 and near else "PAIRWISE_ONLY_TARGET_MISSED" if spread<=0.5 else "UNMATCHED_MEASURED",
   Excluded="Swap 20% infeasible; fixed references not targetable" if target==20 else "fixed references not targetable"))
 write("phase6a_matched_comparisons.csv",matched)
 if not partial:assert len(verification)==len(configs)*17 and all(r["Result"]=="PASS" for r in verification)
 print("Native cases PASS:",sum(v["Result"]=="PASS" for v in verification),"/",len(configs)*17)
 if partial:return
 regressions=[]
 for tag in ["tb_basic_controller","tb_swap_controller","tb_moving_controller","tb_reg_IF_RF_scan","tb_core_scan_isolation","tb_misr_16","functional_lwsw","functional_stalls"]:
  row=next(csv.DictReader((O/"Regression/reports"/(tag+".csv")).open()))
  assert row["Result"]=="PASS";text=(O/"Regression/logs"/(tag+".log")).read_text()
  assert "[FAIL]" not in text
  if tag.startswith("functional"):
   assert text.count("Failure:")==1 and "cMIPS BREAKPOINT at PC=00000038" in text
   assert re.findall(r"(?im)^([0-9a-f]{8})\s*$",text)==[f"{v&0xffffffff:08x}" for v in range(-10,0)]
  else:assert "Failure:" not in text
  regressions.append(row)
 write("phase6a_regressions.csv",regressions)
 for tag,count in [("safety",8),("router",5)]:
  row=next(csv.DictReader((O/"Router/reports"/(tag+".csv")).open()));assert row["Result"]=="PASS"
  text=(O/"Router/logs"/(tag+".log")).read_text();assert text.count(",PASS")==count and "[FAIL]" not in text
 import matplotlib;matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 folder=O/"Comparison/figures";folder.mkdir(parents=True,exist_ok=True)
 for metric in ["MISRCoverage","DirectCoverage"]:
  fig,ax=plt.subplots()
  for c in configs[:5]:
   rows=[v for v in coverage if v["Config"]==c["ID"]];ax.plot([r["Patterns"] for r in rows],[r[metric] for r in rows],"o-",label=NAMES[c["Approach"]])
  ax.set(xlabel="Patterns",ylabel=metric);ax.legend();fig.tight_layout();fig.savefig(folder/(metric+".svg"));plt.close(fig)
 fig,ax=plt.subplots()
 for c in configs:
  w=next(v for v in wtm if v["Config"]==c["ID"]);fc=next(v for v in coverage if v["Config"]==c["ID"] and v["Patterns"]==256)
  ax.scatter(w["MeasuredWTM"],fc["MISRCoverage"]);ax.annotate(str(c["ID"]),(w["MeasuredWTM"],fc["MISRCoverage"]))
 ax.set(xlabel="Measured weighted scan activity (%)",ylabel="Final signature coverage (%)");fig.tight_layout();fig.savefig(folder/"coverage_wtm.svg");plt.close(fig)
 for title,field in [("exposure","HighExposure")]:
  fig,ax=plt.subplots()
  for cid in [2,3,4]:
   rows=[v for v in exposure if v["Config"]==cid];ax.plot([v["PhysicalPosition"] for v in rows],[v[field] for v in rows],label=NAMES[configs[cid]["Approach"]])
  ax.legend();ax.set(xlabel="Physical position, scan-in=0",ylabel="High-region exposure");fig.tight_layout();fig.savefig(folder/(title+".svg"));plt.close(fig)
 fig,ax=plt.subplots()
 for offset,metric in [(-.17,"DirectCoverage"),(.17,"MISRCoverage")]:
  rows=[next(r for r in coverage if r["Config"]==cid and r["Patterns"]==256) for cid in range(5)]
  ax.bar([i+offset for i in range(5)],[r[metric] for r in rows],width=.34,label=metric)
 ax.set_xticks(range(5),NAMES);ax.legend();ax.set(ylabel="Original-16 fault coverage (%)");fig.tight_layout();fig.savefig(folder/"direct_vs_misr.svg");plt.close(fig)
 fig,ax=plt.subplots()
 for f in feasibility:
  if f["Feasible"]:
   ax.scatter(f["Target"],f["MeasuredWTM"],label=f["Approach"]+" beta="+str(f["Beta"]))
 ax.plot([7,22],[7,22],"k--");ax.legend(fontsize=7);ax.set(xlabel="Requested WTM (%)",ylabel="Measured WTM (%)");fig.tight_layout();fig.savefig(folder/"requested_vs_measured.svg");plt.close(fig)
 from collections import Counter
 fig,ax=plt.subplots()
 for cid in range(5):
  counts=Counter(r["FirstDirect"] or 0 for r in campaign if r["Config"]==cid)
  ax.plot(sorted(counts),[counts[k] for k in sorted(counts)],"o-",label=NAMES[cid])
 ax.legend();ax.set(xlabel="First detection pattern (0 = undetected)",ylabel="Faults");fig.tight_layout();fig.savefig(folder/"latency_distribution.svg");plt.close(fig)
 fig,ax=plt.subplots()
 rows=[r for r in thresholds if r["Config"]<5 and r["CoverageTarget"]==75]
 ax.bar([r["Approach"] for r in rows],[r["Cycles"] if isinstance(r["Cycles"],int) else float("nan") for r in rows])
 for i,r in enumerate(rows):
  if not isinstance(r["Cycles"],int):ax.annotate("UNREACHED",(i,0))
 ax.set(ylabel="Payload cycles to 75% signature coverage");fig.tight_layout();fig.savefig(folder/"cycles_to_coverage.svg");plt.close(fig)
 fig,ax=plt.subplots()
 for off,low,high,label in [(-.17,1,8,"PC input (8 eligible)"),(.17,9,16,"Instruction input (8 eligible)")]:
  values=[sum(r["MISRDetected"] for r in campaign if r["Config"]==cid and low<=r["FaultID"]<=high) for cid in range(5)]
  ax.bar([i+off for i in range(5)],values,width=.34,label=label)
 ax.set_xticks(range(5),NAMES);ax.legend();ax.set(ylabel="Detected faults");fig.tight_layout();fig.savefig(folder/"regions.svg");plt.close(fig)
 fig,ax=plt.subplots()
 rows=[r for r in evolution if r["Config"]==3]
 ax.plot([r["Pattern"] for r in rows],[r["Golden"] for r in rows],label="Fault-free")
 ax.plot([r["Pattern"] for r in rows],[r["Actual"] for r in rows],label="Fault 1",alpha=.75)
 ax.legend();ax.set(xlabel="Pattern",ylabel="Swap 16-bit prefix signature");fig.tight_layout();fig.savefig(folder/"signature_evolution.svg");plt.close(fig)
 previews=[];events=[]
 safety_path=O/"Router/waveforms/safety.vcd";safety=Phase5Trace(safety_path);sp="/tb_phase6a_misr_safety"
 check_trace(safety,sp,0,True)
 for scenario in range(8):
  t=next(t for t,v in safety.values(sp,"scenario") if int(v,2)==scenario)
  end=next((u for u,v in safety.values(sp,"scenario") if u>t),safety.end)
  path=safety_path.with_name(f"safety_case_{scenario}.svg")
  render_window(safety,sp,["clk","rst","scenario","phase","ce","unload","done","err","q","valid","match","detected"],t,end,path,f"Safety scenario {scenario}")
  previews.append(verify_preview(safety,sp,path))
  key="err" if scenario in [1,2,3,5] else "done" if scenario==4 else "valid"
  marks=[u for u,v in safety.values(sp,key) if t<=u<end and v=="1"]
  if marks:
   at=marks[0];zoom=path.with_name(f"safety_case_{scenario}_zoom.svg")
   render_window(safety,sp,["clk","phase","unload","done","err","q","valid","match","detected"],max(0,at-10000),min(safety.end,at+12000),zoom,"Completion safety edge",[(at,"captured validity/error event")])
   previews.append(verify_preview(safety,sp,zoom));events.append(dict(Case=f"safety_{scenario}",Event=key,TimePS=at))
 for cid in [3,4]:
  trace=Phase5Trace(O/"Faults/waveforms"/f"c{cid}_f0.vcd");prefix="/tb_phase6a_fault_comparison/engine"
  end=next(t for t,v in trace.values(prefix,"pattern_index") if int(v,2)==18)
  path=trace.path.with_name(f"c{cid}_progression_wrap.svg")
  render_window(trace,prefix,["rst","pattern_index","test_phase","scan_enable","mode_select","capture_enable"],0,end,path,"Swap/Moving progression through eighteen captures")
  previews.append(verify_preview(trace,prefix,path))
 for cid in range(5):
  tag=f"c{cid}_f0";path=O/"Faults/waveforms"/(tag+".vcd");trace=Phase5Trace(path);prefix="/tb_phase6a_fault_comparison/engine"
  check_trace(trace,prefix,next(int(g["Signature"],16) for g in gold if g["Config"]==cid))
  clocks=[t for t,v in trace.values(prefix,"clk") if v=="1"]
  shift=next(t for t in clocks if trace.integer(prefix,"scan_enable",t,True) and trace.integer(prefix,"test_phase",t,True)==2)
  cap=next(t for t in clocks if trace.integer(prefix,"capture_enable",t,True))
  unload=next(t for t in clocks if trace.integer(prefix,"misr_enable",t,True))
  final=next(t for t,v in trace.values(prefix,"signature_valid") if v=="1")
  for t,label in [(shift,"shift"),(cap,"capture"),(unload,"unload"),(final,"complete")]:
   dest=path.with_name(tag+"_"+label+".svg")
   render_window(trace,prefix,["clk","test_phase","scan_enable","mode_select","scan_in","scan_feedback","scan_out","capture_enable","signature","signature_valid","fault_detected","protected_equal"],max(0,t-10000),t+12000,dest,tag+" "+label,[(t,label)])
   previews.append(verify_preview(trace,prefix,dest))
   events.append(dict(Case=tag,Event=label,TimePS=t))
 for cid in range(5):
  path=O/"Faults/waveforms"/f"c{cid}_f1.vcd"
  if not path.exists():continue
  trace=Phase5Trace(path);prefix="/tb_phase6a_fault_comparison/engine"
  expected=next(int(g["Signature"],16) for g in gold if g["Config"]==cid)
  check_trace(trace,prefix,expected)
  row=next(r for r in campaign if r["Config"]==cid and r["FaultID"]==1)
  if row["FirstDirect"]:
   edges=[t for t,v in trace.values(prefix,"clk") if v=="1" and trace.integer(prefix,"capture_enable",t,True)]
   t=edges[int(row["FirstDirect"])-1];dest=path.with_name(path.stem+"_fault_capture.svg")
   render_window(trace,prefix+"/dut",["clk","legal_capture","increment_operand","PCincd","capture_word","RF_PCincd","RF_instruction"],t-10000,t+12000,dest,"Actual fault-1 capture at first detected pattern",[(t,"capture edge")])
   previews.append(verify_preview(trace,prefix+"/dut",dest))
  t=next(t for t,v in trace.values(prefix,"signature_valid") if v=="1")
  dest=path.with_name(path.stem+"_fault_result.svg")
  render_window(trace,prefix,["clk","scan_out","misr_enable","signature","signature_valid","signature_match","fault_detected","protected_equal"],t-10000,t+12000,dest,"Completed faulty stream has a valid comparison",[(t,f"expected {expected:04X}; actual {trace.integer(prefix,'signature',t):04X}")])
  previews.append(verify_preview(trace,prefix,dest))
 write("waveform_validation.csv",previews)
 write("phase6a_waveform_events.csv",events)
 before=json.loads((O/"work/protected.json").read_text())
 audit=[dict(File=p,BeforeSHA256=s,AfterSHA256=hashlib.sha256((R/p).read_bytes()).hexdigest()) for p,s in before.items()]
 assert all(r["BeforeSHA256"]==r["AfterSHA256"] for r in audit);write("protected_integrity.csv",audit)
 print("All original-16 campaigns valid; all protected files unchanged:",len(audit))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--partial",action="store_true");main(p.parse_args().partial)
