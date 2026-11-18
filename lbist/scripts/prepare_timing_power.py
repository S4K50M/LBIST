"""Use newly simulated activity at the selected clock; never rescale old SAIF."""
from pathlib import Path
import sys,json,re,copy,hashlib
from map_final_saif import mapped,parse,instance,pretty,fingerprint
R=Path(__file__).resolve().parents[2];O=R/'Results/Final/FPGA_Analysis/Timing_Closure'
m,d=map(int,sys.argv[1:]);tag=f'm{m}_d{d}';folder=O/'activity'/tag
records=[]
def add_identity_aliases(entry,config):
 # The physical hold buffers are Boolean identities. Their inputs and outputs
 # have the same RTL activity; expose only proven connected input aliases.
 # This is an explicit alias duplication, never an invented switching rate.
 proof=list(__import__('csv').DictReader((O/'closed'/tag/config/'hold_buffer_connectivity.csv').open()))
 assert all(p['Function']=='identity_LUT1_INIT_2' and p['ConnectivityChecked']=='PASS' for p in proof)
 path=R/entry['Mapped'];tree=parse(path.read_text());top=instance(tree,'final_fpga_top');system=instance(top,'u_system')
 node=system if config=='full_lbist' else instance(system,'baseline.u_cpu' if config=='baseline' else 'scan_cpu.u_cpu')
 original=fingerprint(node)
 signals={net[0].replace('\\',''):net for block in node[2:] if block[0]=='NET' for net in block[1:]}
 aliases=[];missing=[]
 names={'external_test_mode':'test_mode','external_scan_enable':'scan_enable','external_capture_enable':'capture_enable','external_scan_in':'scan_in','external_phase':'test_phase'}
 for port in sorted({p['Port'] for p in proof}):
  source=port if port in signals else names.get(port,port)
  if source not in signals:missing.append(port);continue
  net=copy.deepcopy(signals[source]);net[0]=port.replace('[','\\[').replace(']','\\]');aliases.append(net)
 if aliases:top.append(['NET']+aliases)
 assert fingerprint(node)==original
 path.write_text(pretty(tree)+'\n');entry['MappedSHA256']=hashlib.sha256(path.read_bytes()).hexdigest()
 entry['PhysicalIdentityBufferAliases']=len(aliases);entry['UnmappedBufferedInputs']=missing;entry['OriginalActivityUnchanged']=True
 return entry
for a in range(5):
 src=folder/f'approach_{a}.saif'
 duration=int(re.search(r'\(DURATION\s+(\d+)\)',src.read_text())[1])
 expected=660540001*d/(2*m)
 assert abs(duration-expected)<=1,(duration,expected)
 entry=mapped(src,folder/f'mapped_approach_{a}.saif',['tb_final_activity','engine','system_copy'],'u_system',['scan_cpu','lbist'])
 entry.update(DurationPS=duration,ClockMHz=100*m/d,Patterns=256,ActualFreshCapture=True);records.append(add_identity_aliases(entry,'full_lbist'))
for label,name,config in [('U_CORE','baseline.u_cpu','baseline'),('U_SCAN','scan_cpu.u_cpu','scan_enabled')]:
 records.append(add_identity_aliases(mapped(folder/'functional.saif',folder/f'mapped_{config}.saif',['tb_final_functional_activity',label],name),config))
(folder/'mapping_manifest.json').write_text(json.dumps(records,indent=2))
print('Mapped seven fresh activity traces at',100*m/d,'MHz; original 50 MHz SAIF untouched.')
