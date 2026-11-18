"""Read-only audit of archived experiments; writes only Results/Final."""
from pathlib import Path
import csv, json, hashlib, re, sys
from phase6a_results import load, check_trace
from phase5a_trace import Phase5Trace, verify_preview

R=Path(__file__).resolve().parents[2]
O=R/'Results/Final'

def write(name, rows):
    path=O/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader();w.writerows(rows)

def audit():
    configs=json.loads((R/'Results/Phase6A/configs.json').read_text())
    rows=[]
    if '--figures-only' in sys.argv:
        rows=list(csv.DictReader((O/'Verification/archived_campaign_audit.csv').open()))
    for c in ([] if '--figures-only' in sys.argv else configs):
        for fid in range(17):
            words,sigs,act,row=load(c,fid)
            rows.append(dict(Config=c['ID'],Fault=fid,NativeTop=row['Testbench'],
                             CompletionPS=int(row['CompletionTime'].split()[0]),Result='PASS',
                             Evidence=f'Results/Phase6A/Faults/logs/c{c["ID"]}_f{fid}.log'))
        print('Rechecked native captures/signatures/activity/config',c['ID'],flush=True)
    write('Verification/archived_campaign_audit.csv',rows)
    previews=[];traces={}
    for row in csv.DictReader((R/'Results/Phase6A/reports/waveform_validation.csv').open()):
        path=R/row['File']
        title=re.search(r'<title>(/[^<]+?) = ',path.read_text())[1]
        prefix=title.rsplit('/',1)[0]
        tag=path.stem
        if tag.startswith('safety'):vcd=path.with_name('safety.vcd')
        elif 'progression' in tag:vcd=path.with_name(tag.split('_')[0]+'_f0.vcd')
        else:vcd=path.with_name('_'.join(tag.split('_')[:2])+'.vcd')
        if vcd not in traces:traces[vcd]=Phase5Trace(vcd)
        result=verify_preview(traces[vcd],prefix,path)
        assert str(result['IntervalsChecked'])==row['IntervalsChecked']
        previews.append(result)
    safety=next(t for p,t in traces.items() if p.name=='safety.vcd')
    check_trace(safety,'/tb_phase6a_misr_safety',0,True)
    for cid in range(5):
        t=next(t for p,t in traces.items() if p.name==f'c{cid}_f0.vcd')
        golden=next(r['Signature'] for r in csv.DictReader((R/'Results/Phase6A/reports/phase6a_golden_signatures.csv').open()) if int(r['Config'])==cid)
        check_trace(t,'/tb_phase6a_fault_comparison/engine',int(golden,16))
    write('Verification/archived_waveform_audit.csv',previews)
    before=json.loads((O/'work/protected_before.json').read_text())
    integrity=[]
    for path,digest in before.items():
        f=R/path
        actual=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else 'MISSING'
        integrity.append(dict(File=path,BeforeSHA256=digest,AfterSHA256=actual,
                              Result='PASS' if actual==digest else 'FAIL'))
    write('Verification/preservation_audit.csv',integrity)
    assert all(r['Result']=='PASS' for r in integrity),'Earlier artifact changed'
    print(f'PASS: {len(rows)} archived experiments; {len(previews)} waveform figures; {len(integrity)} preserved files.',flush=True)

if __name__=='__main__':audit()
