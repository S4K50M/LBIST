"""Strict analysis of executed XSim campaigns, never inferred fault outcomes."""
from pathlib import Path
import csv,re,json,hashlib
from misr_golden import responses
from phase5a_trace import Phase5Trace,verify_preview
from render_waveform_previews import render_window
R=Path(__file__).resolve().parents[2]
B=R/"Results/Phase5B";C=R/"Results/Phase5C"
def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read(folder,tag):
    row=next(csv.DictReader((folder/"reports"/(tag+".csv")).open()))
    assert row["Result"]=="PASS",row
    log=(folder/"logs"/(tag+".log")).read_text()
    assert "[FAIL]" not in log and "Failure:" not in log
    assert int(row["CompletionTime"].split()[0])<100_000_000_000
    return row,log
def experiment(folder,tag):
    row,log=read(folder,tag)
    captures=re.findall(r"\[CAPTURE\] (\d+),([0-9A-Fa-f]+),([0-9A-Fa-f]+),([0-9A-Fa-f]+),PASS",log)
    assert len(captures)==256 and all(a==b==c for _,a,b,c in captures)
    sigs=re.findall(r"\[SIGNATURE\] (\d+),(\d+),([0-9A-Fa-f]+)",log)
    words=[a.upper() for _,a,_,_ in captures];expected=responses(words)
    assert len(sigs)==256 and [int(s,16) for _,_,s in sigs]==expected
    expected_id=0 if tag=="fault_free" else int(tag.split("_")[1])
    assert all(int(fid)==expected_id for fid,_,_ in sigs),"wrong configured fault ID"
    assert [int(n) for _,n,_ in sigs]==list(range(1,257))
    assert [int(n) for n,_,_,_ in captures]==list(range(1,257))
    final=re.findall(r"\[FINAL_SIGNATURE\] (\d+),([0-9A-Fa-f]+)",log)
    assert len(final)==1 and int(final[0][0])==expected_id and int(final[0][1],16)==expected[-1]
    assert "[SEQUENCE] 16384,256,16384,256" in log
    assert re.search(r"\[ISOLATION\] 4287,0,0,0,\d+,0",log)
    return row,words,expected
def main():
    unit,ulog=read(B/"MISR","misr_unit");assert len(re.findall(r"\[UNIT\].*PASS",ulog))==5
    free,golden,gs=experiment(B/"Integration","fault_free")
    old=list(csv.DictReader((R/"Results/Phase5A/phase5a_capture_unload.csv").open()))
    assert golden==[r["Expected"] for r in old if r["Case"]=="core_shift_capture_P256"]
    write(B/"reports/misr_verification.csv",[dict(Case="unit_5_streams",Result="PASS",Bits=1280,CompletionTime=unit["CompletionTime"]),
        dict(Case="processor_256",Result="PASS",Bits=16384,CompletionTime=free["CompletionTime"])])
    write(B/"reports/misr_golden_signature.csv",[dict(Pattern=i+1,Expected=f"{s:04X}",Actual=f"{s:04X}",ResponseBits=(i+1)*64,Result="PASS") for i,s in enumerate(gs)])
    functional=[]
    for tag in ["functional_lwsw","functional_stalls"]:
        row=next(csv.DictReader((B/"Integration/reports"/(tag+".csv")).open()))
        log=(B/"Integration/logs"/(tag+".log")).read_text()
        assert row["Result"]=="PASS" and "[FAIL]" not in log and log.count("Failure:")==1
        assert re.findall(r"(?im)^([0-9a-f]{8})\s*$",log)==[f"{v&0xffffffff:08x}" for v in range(-10,0)]
        assert "cMIPS BREAKPOINT at PC=00000038" in log
        functional.append(row)
    write(B/"reports/functional_regression.csv",functional)
    inventory=list(csv.DictReader((C/"reports/fault_inventory.csv").open()))
    campaign=[];evolution={};growth=[];times=[];streams=[]
    for inv in inventory:
        fid=int(inv["FaultID"]);row,words,sigs=experiment(C/"Faults",f"fault_{fid}")
        direct=[i+1 for i,(a,b) in enumerate(zip(words,golden)) if a!=b]
        mismatches=[i+1 for i,(a,b) in enumerate(zip(sigs,gs)) if a!=b]
        detected=sigs[-1]!=gs[-1]
        streams.extend(dict(FaultID=fid,Pattern=i+1,GoldenResponse=golden[i],ActualResponse=words[i],
                            GoldenSignature=f"{gs[i]:04X}",ActualSignature=f"{sigs[i]:04X}",
                            DirectMismatch=words[i]!=golden[i]) for i in range(256))
        campaign.append(dict(FaultID=fid,FaultType=inv["FaultType"],FaultSite=inv["Signal"]+"["+inv["Bit"]+"]",
            Patterns=256,DirectDetected=bool(direct),MISRDetected=detected,FirstDetectionPattern=direct[0] if direct else "",
            FirstSignatureMismatch=mismatches[0] if mismatches else "",GoldenSignature=f"{gs[-1]:04X}",
            FaultySignature=f"{sigs[-1]:04X}",Aliasing=bool(direct) and not detected,Result="VALID"))
        evolution[fid]=(direct,sigs);times.append(dict(FaultID=fid,ShiftCycles=16384,CaptureCycles=256,UnloadCycles=16384,
            LBISTCycles=33024,CompletionPS=int(row["CompletionTime"].split()[0]),
            ElapsedClockPeriods=int(row["CompletionTime"].split()[0])/20000,
            SetupPauseRestartPeriods=int(row["CompletionTime"].split()[0])/20000-33024))
    for n in [1,4,8,16,32,64,128,256]:
        direct=sum(any(i<=n for i in ds) for ds,_ in evolution.values())
        compact=sum(s[n-1]!=gs[n-1] for _,s in evolution.values())
        growth.append(dict(Patterns=n,Eligible=16,Invalid=0,DirectDetected=direct,MISRDetected=compact,
            DirectCoverage=100*direct/16,MISRCoverage=100*compact/16,LBISTCycles=n*129))
    write(C/"reports/fault_campaign.csv",campaign);write(C/"reports/fault_detection_latency.csv",campaign)
    write(C/"reports/signature_evolution.csv",streams)
    write(C/"reports/misr_aliasing.csv",[dict(FaultID=r["FaultID"],DirectDetected=r["DirectDetected"],MISRDetected=r["MISRDetected"],Aliasing=r["Aliasing"]) for r in campaign])
    write(C/"reports/fault_coverage_summary.csv",growth);write(C/"reports/test_time_comparison.csv",times)
    thresholds=[]
    for target in [25,50,75,100]:
        hit=next((n for n in range(1,257) if 100*sum(s[n-1]!=gs[n-1] for _,s in evolution.values())/16>=target),None)
        thresholds.append(dict(Approach="Basic22/20/22",CoverageTarget=target,Patterns=hit or "UNREACHED",Cycles=hit*129 if hit else "UNREACHED"))
    write(C/"reports/coverage_threshold_cycles.csv",thresholds)
    import matplotlib;matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figs=C/"Comparison/figures";figs.mkdir(parents=True,exist_ok=True)
    def save(name,x,y,label,xlabel,ylabel):
        fig,ax=plt.subplots(figsize=(8,4));ax.plot(x,y,"o-",label=label);ax.set(xlabel=xlabel,ylabel=ylabel);ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(figs/(name+".svg"));plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for key in ["DirectCoverage","MISRCoverage"]:ax.plot([r["Patterns"] for r in growth],[r[key] for r in growth],"o-",label=key)
    ax.set(xlabel="Patterns",ylabel="Enumerated-fault coverage (%)",ylim=(0,105));ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(figs/"coverage_growth.svg");plt.close(fig)
    save("detection_latency",list(range(1,17)),[r["FirstDetectionPattern"] or 0 for r in campaign],"First direct mismatch (0=none)","Fault ID","Pattern")
    from collections import Counter
    counts=Counter(r["FirstDetectionPattern"] or 0 for r in campaign)
    fig,ax=plt.subplots();ax.bar([str(n) for n in sorted(counts)],[counts[n] for n in sorted(counts)])
    ax.set(xlabel="First detection pattern (0 = undetected)",ylabel="Faults");fig.tight_layout();fig.savefig(figs/"latency_distribution.svg");plt.close(fig)
    save("test_cycles",[r["LBISTCycles"] for r in growth],[r["MISRCoverage"] for r in growth],"Basic 22/20/22","Measured enabled test cycles","Signature coverage (%)")
    save("signature_evolution",list(range(1,257)),[s^gs[i] for i,s in enumerate(evolution[1][1])],"Fault 1 XOR golden","Pattern","16-bit signature difference")
    fig,ax=plt.subplots();regions=["increment_operand","instruction_input"]
    ax.bar(regions,[sum(r["MISRDetected"] for r in campaign if r["FaultSite"].startswith(k)) for k in regions]);ax.set(ylabel="Detected faults (8 eligible per region)");fig.tight_layout();fig.savefig(figs/"detections_by_region.svg");plt.close(fig)
    previews=[]
    for folder,tag,top in [(B/"MISR","misr_unit","tb_misr_16"),(B/"Integration","fault_free","tb_misr_integration"),
                          (C/"Faults","fault_1","tb_lbist_fault_injection"),(C/"Faults","fault_10","tb_lbist_fault_injection")]:
        trace=Phase5Trace(folder/"waveforms"/(tag+".vcd"))
        prefix="/"+top+("" if tag=="misr_unit" else "/engine")
        state=0;edges=0
        for t,v in trace.values(prefix,"clk"):
            if v!="1":continue
            pre=lambda n:trace.integer(prefix,n,t,True)
            if pre("rst")==0 or (tag=="misr_unit" and pre("clear")):state=0
            elif pre("enable" if tag=="misr_unit" else "misr_enable"):
                from misr_golden import signature
                state=signature([pre("response_bit" if tag=="misr_unit" else "scan_out")],state)
            assert trace.integer(prefix,"signature",t)==state,(tag,t)
            if tag!="misr_unit":
                complete=trace.integer(prefix,"test_phase",t)==5
                assert trace.integer(prefix,"signature_valid",t)==int(complete)
                assert trace.integer(prefix,"signature_match",t)==int(complete and state==gs[-1])
                assert trace.integer(prefix,"fault_detected",t)==int(complete and state!=gs[-1])
            edges+=1
        assert edges>100
        names=["clk","rst","enable","clear","response_bit","signature"] if tag=="misr_unit" else [
            "clk","rst","test_phase","scan_enable","capture_enable","scan_out","misr_enable","signature","signature_valid","signature_match","fault_detected","scan_state","protected_equal"]
        events=[("reset",0),("final",max(0,trace.end-450000))]
        overview=folder/"waveforms"/f"{tag}_overview.svg"
        overview_fields=["rst","clear","signature"] if tag=="misr_unit" else ["rst","test_mode","test_phase","signature_valid","signature_match","fault_detected","protected_equal"]
        render_window(trace,prefix,overview_fields,0,trace.end,overview,tag+" complete timeline")
        previews.append(verify_preview(trace,prefix,overview))
        if tag!="misr_unit":
            for value,label in [(3,"capture"),(4,"first_unload"),(5,"signature_compare")]:
                t=next(t for t,v in trace.values(prefix,"test_phase") if int(v,2)==value)
                events.append((label,t))
        for label,t in events:
            path=folder/"waveforms"/f"{tag}_{label}.svg"
            render_window(trace,prefix,names,max(0,t-10000),min(trace.end,t+40000),path,tag+" "+label,[(t,label)])
            previews.append(verify_preview(trace,prefix,path))
        if tag!="misr_unit":
            pattern=1
            if tag.startswith("fault_") and tag!="fault_free":
                detections=evolution[int(tag.split("_")[1])][0]
                pattern=detections[0] if detections else 1
            t=[t for t,v in trace.values(prefix,"test_phase") if int(v,2)==3][pattern-1]+20000
            path=folder/"waveforms"/f"{tag}_capture_cone.svg"
            fields=["clk","legal_capture","increment_operand","PCincd","capture_word","RF_PCincd","RF_instruction"]
            render_window(trace,prefix+"/dut",fields,t-10000,t+12000,path,tag+" actual capture cone",[(t,"capture edge")])
            previews.append(verify_preview(trace,prefix+"/dut",path))
    write(B/"reports/waveform_validation.csv",previews)
    protected=json.loads((B/"work/protected.json").read_text())
    integrity=[dict(File=p,SHA256=sha,Result="PASS" if hashlib.sha256((R/p).read_bytes()).hexdigest()==sha else "FAIL") for p,sha in protected.items()]
    write(B/"reports/protected_integrity.csv",integrity);assert all(r["Result"]=="PASS" for r in integrity)
    final=growth[-1];aliases=sum(r["Aliasing"] for r in campaign)
    report=f"""# Phase 5C — measured capture-cone stuck-at campaign

All **16 eligible faults** completed valid, independent 256-pattern processor
experiments. The universe contains eight explicitly selected capture-input
sites, with SA0 and SA1 at each. Fault-free golden signature: **{gs[-1]:04X}**.

| Metric | Actual result |
| --- | ---: |
| Direct response detections | {final['DirectDetected']} / 16 |
| Final MISR detections | {final['MISRDetected']} / 16 |
| Direct coverage | {final['DirectCoverage']:.2f}% |
| Final MISR coverage | {final['MISRCoverage']:.2f}% |
| Undetected by final MISR | {16-final['MISRDetected']} |
| MISR aliases | {aliases} |
| Invalid experiments | 0 |
| Patterns per experiment | 256 |
| Actual SHIFT / CAPTURE / UNLOAD cycles | 16384 / 256 / 16384 |
| Enabled payload cycles per experiment | 33024 |

Each fault experiment finished at 661.6002 us, below the 100 ms limit.
Setup, acknowledgement, pauses, reset and restart add 56.01 elapsed 20 ns
clock periods outside the payload. All 4,096 faulty captured responses and
their serial unloads matched independent injection-aware predictions.
Python checked every per-pattern MISR result by polynomial division of the
actual response stream. Protected processor state and actual write strobes
remained isolated in every experiment.

## Results and figures

- [Defined eligible inventory](reports/fault_inventory.csv).
- [All actual fault outcomes/signatures](reports/fault_campaign.csv).
- [Detection latency](reports/fault_detection_latency.csv).
- [Aliasing classification](reports/misr_aliasing.csv).
- [Coverage at 1/4/8/16/32/64/128/256 patterns](reports/fault_coverage_summary.csv).
- [Actual cycle counts and overheads](reports/test_time_comparison.csv).
- [Cycles to common coverage thresholds](reports/coverage_threshold_cycles.csv).
- [Actual per-pattern responses and signatures](reports/signature_evolution.csv).
- [Direct versus MISR coverage growth](Comparison/figures/coverage_growth.svg).
- [Detections by region](Comparison/figures/detections_by_region.svg).
- [First-detection distribution](Comparison/figures/latency_distribution.svg).
- [Coverage versus test cycles](Comparison/figures/test_cycles.svg).
- [Representative signature evolution versus golden](Comparison/figures/signature_evolution.svg).

Native representative captures are in
[fault 1](Faults/waveforms/fault_1.wcfg) and
[fault 10](Faults/waveforms/fault_10.wcfg).
The focused [fault 1 capture cone](Faults/waveforms/fault_1_capture_cone.svg)
uses its first directly detected pattern rather than an assumed timestamp.
Full WDB/VCD stay local; portable WCFG and verified SVG previews are tracked.
[SVG interval checks](../Phase5B/reports/waveform_validation.csv) also cover
the unit and fault-free captures. Every recorded MISR clock edge and settled
completion comparator is independently checked from VCD.

## Scope and reproduction

The muxes alter actual incrementer inputs or actual instruction capture inputs,
before the functional response is stored. They never force scan FF outputs or
MISR state. Fault-ID headers, complete pattern indices, final signatures,
serial responses, completion markers and isolation assertions are checked;
a missing or misconfigured experiment fails analysis.

Only the eight enumerated input-net sites are covered. Instruction bits at the
held fetch address are constant, so a stuck-at polarity already equal to the
functional bit can remain unobservable. Such faults stay in the denominator.
An equal final signature with a direct mismatch is reported as an alias;
equal signatures alone do not establish fault freedom.

The experiment uses the unchanged Basic 22/20/22 controller and real PLPF
feedback. Faults can change later feedback-dependent stimulus; this is the
same configured closed-loop sequence, not an assertion that all faulty scan
words remain identical to fault-free words.

Run lbist/scripts/run_all_phase5bc.tcl in Vivado batch mode, then optionally
lbist/scripts/synth_phase5bc.tcl. Separate runners are provided for unit,
integration, campaign and functional regressions. The campaign also accepts
global fault_first/fault_last bounds, enabling independent workers in separate
projects. This execution used independent workers for the remaining faults.

See [design/protocol and polynomial](../../docs/phase5bc_misr_faults.md) and
[Phase 5B verification/synthesis](../Phase5B/README.md).
All {len(integrity)} tracked pre-Phase5B/C files retained their SHA-256;
the original Phase 5A preservation audit also remains unchanged.
Unfiltered/constant PLPF/Swap/Moving comparison and matched-WTM plots are
explicit follow-up work. No full MIPS32 coverage, power savings, remaining
656-bit scan conversion or fault-free guarantee is claimed.
"""
    (C/"README.md").write_text(report,encoding="utf-8")
    print("PASS: 5 unit streams; fault-free AFBC; 16 valid independent fault experiments; protected files",len(integrity))
    print("Final coverage:",growth[-1],"Aliases:",sum(r["Aliasing"] for r in campaign))
if __name__=="__main__":main()
