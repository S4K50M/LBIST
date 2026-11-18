"""Actual native timing sweep: never infer closure from successful routing."""
from pathlib import Path
import re,csv,json
R=Path(__file__).resolve().parents[2];O=R/'Results/Final/FPGA_Analysis/Timing_Closure'
def rows(p):return list(csv.DictReader(p.open())) if p.exists() else []
def write(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in data for k in row)) if data else ['Status']);w.writeheader();w.writerows(data)
def timing(p):
 text=p.read_text();m=re.search(r'WNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)',text,re.S)
 assert m,p
 n=list(map(float,m.groups()))
 get=lambda name:int(re.search(r'checking '+name+r' \((\d+)\)',text)[1])
 out=dict(WNS=n[0],TNS=n[1],SetupFails=int(n[2]),SetupEndpoints=int(n[3]),WHS=n[4],THS=n[5],HoldFails=int(n[6]),HoldEndpoints=int(n[7]),WPWS=n[8],PulseFails=int(n[10]),UnconstrainedInternal=get('unconstrained_internal_endpoints'),NoClock=get('no_clock'))
 unspecified=re.search(r'There are (\d+) input ports with no input delay specified',text)
 out['UnspecifiedInputDelay']=int(unspecified[1]) if unspecified else -1
 out['UnspecifiedOutputDelay']=get('no_output_delay')
 out['TimingClean']=all(out[k]>=0 for k in ['WNS','WHS','WPWS']) and all(out[k]==0 for k in ['TNS','THS','SetupFails','HoldFails','PulseFails','UnconstrainedInternal','NoClock','UnspecifiedInputDelay','UnspecifiedOutputDelay'])
 delays=re.findall(r'Data Path Delay:\s*([\d.]+)ns',text);out['FirstSetupPathNS']=delays[0] if delays else ''
 return out,text
def util(p,label):
 m=re.search(r'^\|\s*'+re.escape(label)+r'\s*\|\s*([\d.]+)',p.read_text(),re.M)
 return float(m[1]) if m else ''

def utilization_percent(p,label):
 for line in p.read_text().splitlines():
  cells=[s.strip() for s in line.split('|')]
  if len(cells)==8 and cells[1]==label:return float(cells[-2])
 return ''
def main():
 sweep=[];cross=[]
 folders=[('initial',p) for p in sorted((O/'sweep').glob('*/*'))]+[('physical_repair',p) for p in sorted((O/'closed').glob('*/*'))]
 for variant,folder in folders:
  cfg=rows(folder/'clock_configuration.csv')
  status=rows(folder/'status.csv')
  m=re.fullmatch(r'm(\d+)_d(\d+)',folder.parent.name)
  entry=dict(Variant=variant,Configuration=folder.name,Mult=int(m[1]),Divide=int(m[2]),FrequencyMHz=100*int(m[1])/int(m[2]),
             Implementation=next((r['Status'] for r in status if r['Stage']=='implementation'),'NOT_COMPLETE'))
  if variant=='physical_repair':
   log=O/f'close_{folder.name}_{folder.parent.name}.log'
   entry['Implementation']='PASS' if log.exists() and re.search(r'^FINAL PHYSICAL REPAIR FINISHED:',log.read_text(),re.M) else 'NOT_COMPLETE'
  entry['MMCMQuarterDutyLegal']=6<=int(m[1])<=12 and 4<=int(m[2])<=84 and int(m[2])%2==0
  entry['PhysicalInputHoldBuffers']=len(rows(folder/'hold_buffer_connectivity.csv')) if variant=='physical_repair' else 0
  entry['OrphanTrialBuffers']=6 if variant=='initial' and (folder/'irq_hold_buffers.csv').exists() else 0
  if (folder/'routed_timing.rpt').exists():
   values,text=timing(folder/'routed_timing.rpt');entry.update(values)
   entry['TimingClean']=bool(entry['TimingClean'] and entry['MMCMQuarterDutyLegal'] and entry['Implementation']=='PASS')
   # Anchor each clock-pair header and its immediate setup/hold rows. A
   # clock with NA paths must not consume the following clock's statistics.
   pattern=r'^(?:Path Group:[ \t]+([^\n]+)\n)?From Clock:[ \t]+(\S+)[ \t]*\n[ \t]*To Clock:[ \t]+(\S+)[ \t]*\n\s*Setup[ \t]*:[ \t]*(\d+)[ \t]+Failing Endpoints,[ \t]*Worst Slack[ \t]+([-\d.]+)ns[^\n]*\nHold[ \t]*:[ \t]*(\d+)[ \t]+Failing Endpoints,[ \t]*Worst Slack[ \t]+([-\d.]+)ns'
   for match in re.finditer(pattern,text,re.M):
    group,a,b,s,ws,h,wh=match.groups();cross.append(dict(Variant=variant,Configuration=folder.name,Mult=entry['Mult'],Divide=entry['Divide'],PathGroup=group or 'clock_pair',From=a,To=b,SetupFails=s,SetupWNS=ws,HoldFails=h,HoldWHS=wh))
   u=folder/'routed_utilization.rpt'
   for key,label in [('LUT','Slice LUTs'),('FF','Register as Flip Flop'),('Latches','Register as Latch'),('LUTRAM','LUT as Memory'),('BRAM36Equivalent','Block RAM Tile'),('DSP','DSPs'),('CARRY4','CARRY4'),('BUFG','BUFGCTRL'),('MMCM','MMCME2_ADV')]:entry[key]=util(u,label)
   entry['LUTUtilizationPercent']=utilization_percent(u,'Slice LUTs')
   entry['FFUtilizationPercent']=utilization_percent(u,'Register as Flip Flop')
  else:entry['TimingClean']='NOT_AVAILABLE'
  entry['Evidence']=str(folder.relative_to(R)).replace('\\','/');sweep.append(entry)
 write(O/'frequency_sweep.csv',sweep);write(O/'cross_phase_timing.csv',cross)
 for row in sweep:print(row['Configuration'],row['FrequencyMHz'],row['Implementation'],row.get('WNS',''),row.get('WHS',''),row['TimingClean'])
if __name__=='__main__':main()
