"""Verify final native case evidence and record source/activity provenance."""
from pathlib import Path
import csv,re,hashlib,json,subprocess
from audit_final_evidence import write
from build_phase6a import model
from misr_golden import responses
from phase5a_trace import Phase5Trace
from phase6a_results import check_trace
R=Path(__file__).resolve().parents[2];O=R/'Results/Final'
def rows(p):return list(csv.DictReader(p.open()))
def main():
    records=[]
    for group in ['Essential','Activity','FunctionalActivity','FaultDemo']:
        for p in sorted((O/'Verification'/group/'reports').glob('*.csv')):
            if p.stem.endswith('_samples'):continue
            row=rows(p)[0];assert row['Result']=='PASS',p
            duration=int(row['CompletionTime'].split()[0]);assert duration<100_000_000_000
            text=(O/'Verification'/group/'logs'/(p.stem+'.log')).read_text()
            assert not re.search(r'\[FAIL\]|Fatal:|ERROR:',text),p
            if row['Testbench'] in ['tb_core_fault_regression','tb_final_functional_activity']:
                assert text.count('Failure:')==1 and 'cMIPS BREAKPOINT at PC=00000038' in text
                samples=rows(p.with_name(p.stem+'_samples.csv'))
                assert len(samples)>=100 and all(s['Result']=='PASS' for s in samples)
                if p.stem=='functional_stalls':assert any(s['IF_RF_ld']=='1' for s in samples)
                assert re.findall(r'(?im)^([0-9a-f]{8})\s*$',text)==[f'{v&0xffffffff:08x}' for v in range(-10,0)]
            else:assert 'Failure:' not in text
            if group in ['Activity','FaultDemo']:
                a=int(p.stem[-1]) if group=='Activity' else 2
                fid=0 if group=='Activity' else 1;beta=16 if a==3 else 20
                predicted,activity=model(a,beta,fid)
                captures=re.findall(r'\[CAPTURE\] (\d+),([0-9a-fA-F]+),([0-9a-fA-F]+),([0-9a-fA-F]+),PASS',text)
                assert len(captures)==256
                assert [int(t[0]) for t in captures]==list(range(1,257))
                assert [t[1].upper() for t in captures]==predicted
                assert all(t[1]==t[2]==t[3] for t in captures)
                sg=re.findall(r'\[SIGNATURE\] (\d+),(\d+),([0-9a-fA-F]+)',text)
                assert len(sg)==256 and [int(s[2],16) for s in sg]==responses(predicted)
                trace=Phase5Trace(O/'Verification'/group/'waveforms'/(p.stem+'.vcd'))
                prefix='/'+row['Testbench']+'/engine'
                golden=responses(model(a,beta,0)[0])[-1]
                check_trace(trace,prefix,golden)
            records.append(dict(Case=row['Case'],Group=group,CompletionPS=duration,Result='PASS',
                                Log=str((O/'Verification'/group/'logs'/(p.stem+'.log')).relative_to(R)).replace('\\','/')))
    assert sum(r['Group']=='Essential' for r in records)==13
    assert sum(r['Group']=='Activity' for r in records)==5
    assert sum(r['Group']=='FunctionalActivity' for r in records)==1
    assert sum(r['Group']=='FaultDemo' for r in records)==1
    write('Verification/final_native_audit.csv',records)
    saifs=[]
    for a in range(5):
        p=O/f'FPGA_Analysis/power/activity/approach_{a}.saif';text=p.read_text()
        duration=int(re.search(r'\(DURATION\s+(\d+)\)',text)[1]);assert duration==660540001
        assert '(TC 66054)' in text
        saifs.append(dict(Approach=a,DurationPS=duration,Patterns=256,CPUClockMHz=50,
                           StartPS=610000,EndPS=661150001,SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),Result='PASS'))
    write('FPGA_Analysis/power/activity_windows.csv',saifs)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True,stderr=subprocess.PIPE).strip()
    files=list((R/'lbist/final').glob('*'))+[p for p in (R/'lbist/scripts').glob('*final*') if p.is_file()]+list((R/'lbist/tb').glob('*final*'))
    manifest=[dict(File=str(p.relative_to(R)).replace('\\','/'),SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),HistoricalBaseline=head) for p in sorted(files)]
    write('source_manifest.csv',manifest)
    print(f'PASS: {len(records)} final native cases, five equal activity windows, {len(manifest)} final source hashes.')
if __name__=='__main__':main()
