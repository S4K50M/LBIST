"""Independent check of fresh selected-clock processor data and original preservation."""
from pathlib import Path
import sys,csv,json,re,hashlib
from build_phase6a import model
from misr_golden import responses
from phase5a_trace import Phase5Trace
from phase6a_results import check_trace
from summarize_timing_closure import write
R=Path(__file__).resolve().parents[2];O=R/'Results/Final/FPGA_Analysis/Timing_Closure'
m,d=map(int,sys.argv[1:]);tag=f'm{m}_d{d}';base=O/'verification'/tag
cases=[];wtm=[]
for group in ['Clock','Functional','Activity','Fault']:
 for path in sorted((base/group/'reports').glob('*.csv')):
  if path.stem.endswith('_samples'):continue
  row=next(csv.DictReader(path.open()));assert row['Result']=='PASS',path
  text=(base/group/'logs'/(path.stem+'.log')).read_text()
  assert not re.search(r'\[FAIL\]|Fatal:|ERROR:',text)
  duration=int(row['CompletionTime'].split()[0]);assert duration<100_000_000_000
  if group=='Clock':assert 'actual UNISIM MMCM' in text and 'Warning:' not in text
  if group=='Functional':
   assert 'cMIPS BREAKPOINT at PC=00000038' in text and text.count('Failure:')==1
   assert re.findall(r'(?im)^([0-9a-f]{8})\s*$',text)==[f'{x&0xffffffff:08x}' for x in range(-10,0)]
   samples=list(csv.DictReader(path.with_name(path.stem+'_samples.csv').open()))
   assert len(samples)>=100 and all(s['Result']=='PASS' for s in samples)
   if path.stem.endswith('stalls'):assert any(s['IF_RF_ld']=='1' for s in samples)
  else:assert 'Failure:' not in text
  if group in ['Activity','Fault']:
   a=int(path.stem[-1]) if group=='Activity' else 2;fid=0 if group=='Activity' else 1;beta=16 if a==3 else 20
   words,expected=model(a,beta,fid);gold=responses(model(a,beta,0)[0])[-1]
   actual=re.findall(r'\[CAPTURE\] (\d+),([0-9a-f]+),([0-9a-f]+),([0-9a-f]+),PASS',text,re.I)
   assert len(actual)==256 and [int(x[0]) for x in actual]==list(range(1,257))
   assert [x[1].upper() for x in actual]==words and all(x[1]==x[2]==x[3] for x in actual)
   sigs=re.findall(r'\[SIGNATURE\] (\d+),(\d+),([0-9a-f]+)',text,re.I)
   assert [int(x[2],16) for x in sigs]==responses(words)
   assert '[SEQUENCE] 16384,256,16384,256' in text
   trace=Phase5Trace(base/group/'waveforms'/(path.stem+'.vcd'))
   check_trace(trace,'/'+row['Testbench']+'/engine',gold)
   activity=tuple(map(int,re.search(r'\[ACTIVITY\] (\d+),(\d+),(\d+)',text).groups()))
   assert activity==(round(expected['MeasuredWTM']*256*64*2080),round(expected['ScanFFSwitching']*256*64*64),round(expected['SerialToggleRate']*256*64))
   if group=='Activity':wtm.append(dict(Approach=['Direct','Constant n=3','Basic','Swap','Moving'][a],MeasuredWTM=100*activity[0]/(256*64*2080),Signature=f'{gold:04X}',Patterns=256,PayloadCycles=33024,ClockMHz=100*m/d,CompletionPS=duration))
  cases.append(dict(Case=path.stem,Group=group,ClockMHz=100*m/d,CompletionPS=duration,Result='PASS'))
assert len(cases)==9 and len(wtm)==5
write(O/'verification_summary.csv',cases);write(O/'fresh_approach_metrics.csv',wtm)
before=json.loads((O/'preserved_before.json').read_text());protected=[]
for name,digest in before.items():
 actual=hashlib.sha256((R/name).read_bytes()).hexdigest();assert actual==digest,name
 protected.append(dict(File=name,BeforeSHA256=digest,AfterSHA256=actual,Result='PASS'))
write(O/'preservation_audit.csv',protected)
print(f'PASS: nine fresh cases, five independently checked full streams, {len(protected)} preserved tracked files.')
