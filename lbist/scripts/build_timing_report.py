"""Consolidate the new clock revision; the original 50 MHz reports stay intact."""
from pathlib import Path
import sys,re,csv,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from summarize_timing_closure import main as summarize,rows,write,timing,util,R,O
import summarize_final_power as power_reader
def table(data,keys):
 def val(x):
  if isinstance(x,float):return f'{x:.4f}' if x!=int(x) else str(int(x))
  if isinstance(x,str) and re.fullmatch(r'-?\d+\.\d+',x):return f'{float(x):.6f}'.rstrip('0').rstrip('.')
  return str(x)
 return '| '+' | '.join(keys)+' |\n| '+' | '.join('---' for _ in keys)+' |\n'+'\n'.join('| '+' | '.join(val(r.get(k,'')) for k in keys)+' |' for r in data)
def figure(fig,name):
 out=O/'figures';out.mkdir(exist_ok=True)
 fig.tight_layout()
 for ext in ['svg','png','pdf']:fig.savefig(out/(name+'.'+ext),dpi=170,bbox_inches='tight')
 plt.close(fig)

def prose(text):
 # Keep commands, URLs and inline identifiers exact while spacing prose.
 out=[];code=False
 for line in text.splitlines():
  if line.startswith('```'):code=not code;out.append(line);continue
  if code or line.startswith('|'):out.append(line);continue
  parts=re.split(r'(`[^`]+`|https?://\S+)',line)
  for i in range(0,len(parts),2):
   s=parts[i]
   s=re.sub(r'\b(original|Original|historical|Historical|earlier|Earlier|at|divide|through|from|only|for|nominal|all|one|uses|use|with|than|and|remain|remains|is|of|in|per|minimum|Vivado|UG953|UG903|Timing|UNISIM|approximately|reported|fault|phase|the|a)(?=\d)',r'\1 ',s)
   s=re.sub(r'(?<=\d)(MHz|GHz|ns|ps|ms|cycles|patterns|captures|setup|W|V|°C|bits|scan|fault|duty|phase)\b',r' \1',s)
   s=re.sub(r'(?<=\d)%duty',r'% duty',s)
   s=re.sub(r'(?<=°)(phase|duty)\b',r' \1',s)
   s=s.replace(',25 ', ', 25 ').replace('at610','at 610').replace('duration660','duration 660').replace('least1','least 1')
   s=re.sub(r'\b(was|stays|multipliers|dividers|legal|blanket|its|Thus|At|small|unsupported|reference)(?=\d)',r'\1 ',s)
   s=s.replace('A75%', 'A 75%').replace('large-divider5/', 'large-divider 5/')
   parts[i]=s
  out.append(''.join(parts))
 return '\n'.join(out)+'\n'
def main():
 m,d=map(int,sys.argv[1:]);tag=f'm{m}_d{d}';frequency=100*m/d;period=10*d/m
 summarize();sweep=rows(O/'frequency_sweep.csv')
 cross=[r for r in rows(O/'cross_phase_timing.csv') if r['Variant']=='physical_repair' and int(r['Mult'])==m and int(r['Divide'])==d and r['PathGroup']=='clock_pair' and (r['From'],r['To']) in [('c0','c0'),('c1','c0'),('c0','c1')]]
 assert len(cross)==9,'Missing same-clock or cross-phase evidence'
 selected=[r for r in sweep if r['Variant']=='physical_repair' and int(r['Mult'])==m and int(r['Divide'])==d]
 assert len(selected)==3 and all(r['Implementation']=='PASS' for r in selected),'Complete all three implementations first'
 selected.sort(key=lambda r:['baseline','scan_enabled','full_lbist'].index(r['Configuration']))
 clean=all(r['TimingClean']=='True' for r in selected)
 write(O/'selected_synthesis_timing.csv',selected)
 overhead=[]
 for a,b,label in [(0,1,'Scan/isolation vs original'),(0,2,'Full LBIST vs original'),(1,2,'LBIST addition vs scan')]:
  overhead.append(dict(Comparison=label,ClockMHz=frequency,LUTDelta=float(selected[b]['LUT'])-float(selected[a]['LUT']),
   LUTPercent=100*(float(selected[b]['LUT'])/float(selected[a]['LUT'])-1),FFDelta=float(selected[b]['FF'])-float(selected[a]['FF']),
   FFPercent=100*(float(selected[b]['FF'])/float(selected[a]['FF'])-1)))
 write(O/'area_overhead.csv',overhead)
 native=rows(O/'verification_summary.csv');assert len(native)==9 and all(r['Result']=='PASS' for r in native)
 assert re.search(r'^TIMING NATIVE WAVEFORM AUDIT: 6/6 PASS$',(O/'waveform_audit.log').read_text(),re.M),'Native waveform audit incomplete'
 status=rows(O/'power'/tag/'status.csv');assert len(status)==7 and all(r['Result']=='PASS' for r in status)
 power_reader.P=O
 names=['Direct','Constant n=3','Basic','Swap','Moving']
 power=[power_reader.collect(f'{tag}/approach_{a}','full_lbist',name) for a,name in enumerate(names)]
 refs=[power_reader.collect(f'{tag}/{c}',c,'Functional lwsw') for c in ['baseline','scan_enabled']]
 for row in power+refs:row.update(CPUClockMHz=frequency,TimingClosure='PASS' if clean else 'FAIL')
 write(O/'power_comparison.csv',power);write(O/'functional_power.csv',refs)
 metrics=rows(O/'fresh_approach_metrics.csv');combined=[]
 for metric,p in zip(metrics,power):
  assert metric['Approach']==p['Approach']
  combined.append(dict(Approach=p['Approach'],WTM=float(metric['MeasuredWTM']),DynamicW=p['DynamicW'],TotalW=p['TotalW'],
   CommonLUT=selected[2]['LUT'],CommonFF=selected[2]['FF'],WNS=selected[2]['WNS'],WHS=selected[2]['WHS'],
   AnnotationPercent=p['AnnotationPercent'],Confidence=p['VivadoConfidence'],Status=p['Status'],ClockMHz=frequency))
 write(O/'approach_comparison.csv',combined)
 annotation=[]
 for a,name in enumerate(names):
  text=(O/'power'/tag/f'approach_{a}'/'register_switching.rpt').read_text()
  codes=re.findall(r'toggle rate = .*?\(([A-Z])\)',text)
  annotation.append(dict(Approach=name,ReportedRegisterQNetRows=len(codes),SimulationRows=codes.count('S'),PropagatedRows=codes.count('P'),DefaultRows=codes.count('D'),OtherRows=sum(c not in 'SPD' for c in codes)))
 write(O/'register_activity_sources.csv',annotation)
 plt.rcParams.update({'font.size':9,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
 fig,ax=plt.subplots(figsize=(8,4))
 for config in ['baseline','scan_enabled','full_lbist']:
  rs=[r for r in sweep if r['Configuration']==config and r['MMCMQuarterDutyLegal']=='True' and r['Implementation']=='PASS' and r['Variant']=='physical_repair']
  ax.plot([float(r['FrequencyMHz']) for r in rs],[float(r['WNS']) for r in rs],'o',label=config)
 ax.axhline(0,color='black',lw=.8);ax.set(xlabel='Actual MMCM CPU frequency (MHz)',ylabel='Routed setup slack (ns)',title='Native results after physical input hold repair');ax.legend();figure(fig,'frequency_sweep')
 fig,axes=plt.subplots(1,2,figsize=(9,4))
 for ax,key in zip(axes,['LUT','FF']):
  bars=ax.bar(['Original','Scan/isolation','Full LBIST'],[float(r[key]) for r in selected],color=['#8b9dab','#388ba7','#ca8a3f'])
  ax.bar_label(bars,fmt='%.0f');ax.set(ylabel=key,title=f'{frequency:.6f} MHz, routed')
 figure(fig,'area_comparison')
 fig,ax=plt.subplots(figsize=(8,4))
 values=[float(p['DynamicW'])*1000 for p in power]
 bars=ax.bar(names,values,color='#388ba7');ax.errorbar(range(5),values,yerr=.5,fmt='none',color='#444',capsize=3)
 ax.bar_label(bars,fmt='%.0f');ax.set(ylabel='Estimated dynamic power (mW)',title='Common routed hardware; partial RTL SAIF\nError bars indicate report rounding, not uncertainty');figure(fig,'dynamic_power')
 fig,ax=plt.subplots(figsize=(8,4))
 for i,row in enumerate(combined):
  ax.scatter(row['WTM'],float(row['DynamicW'])*1000)
  ax.annotate(row['Approach'],(row['WTM'],float(row['DynamicW'])*1000),xytext=(4,10 if i==2 else -15 if i==4 else 3),textcoords='offset points',fontsize=8)
 ax.set(xlabel='Fresh measured SHIFT-only WTM (%)',ylabel='Estimated C dynamic power (mW)',title='Assumption-dominated estimate; no measured power-saving claim');figure(fig,'wtm_power')
 state='PASS: constrained OOC setup/hold/pulse and unconstrained-path checks' if clean else 'FAIL: required timing checks still fail; no valid operating frequency claimed'
 clause=f'{frequency:.9f} MHz is the highest tested common timing-clean OOC point' if clean else 'No common timing-clean operating point has been established'
 readme=f'''# Final FPGA timing revision

**{state}.** {clause}. This is an out-of-context processor result under the documented virtual-interface contract, not a board-qualified maximum or an exhaustive search over all MMCM ratios/place-and-route seeds. The original50MHz results remain in the parent directories; their report and clock sources are frozen in `original_50mhz_sources/`.

## What failed and what changed

The original50MHz full-LBIST design had WNS−76.315ns, TNS−7796.277ns, WHS−2.726ns and1,278setup-failing endpoints. Its worst data path was96.283ns, crossing long original processor combinational logic into HI storage. At50MHz, cross-phase c1→c0 and c0→c1 paths had only5ns available and also failed. The worst original hold path was irq[0]→MM_int_req_reg[0]/D: using c0 as the external I/O reference included negative MMCM compensation source latency in the external launch time.

The board reference stays100MHz. The clock wrapper now supports integer VCO multipliers6–12 with DIVCLK=1, and even common output dividers4–84. clk remains50%duty; phi1 remains270°/25%duty, phi2 remains0°/25%duty and phi3 remains90°/25%duty. Default generics still reproduce the historical50MHz design; the revision explicitly sets M={m}, D={d}, VCO={100*m}MHz, CPU period={period}ns.

An important rejected experiment: divide100 at a1GHz VCO and divide120 at a600MHz VCO do not preserve legal25%duty counters. UNISIM warns about unreachable duty cycles/phase delay, even though ideal STA clock reports list the requested waveforms. A75%-low count must fit the output counter and the270°phase delay must fit its6-bit count. Even dividers through84 satisfy these bounds. Thus5MHz cannot be generated by this unchanged direct-MMCM, quarter-duty architecture at the minimum600MHz VCO. These attempted results are retained but marked `MMCMQuarterDutyLegal=False`, and never count as timing-clean hardware. The legal800MHz VCO configurations avoid clipping and pass the actual UNISIM phase test.

The external OOC contract uses a virtual CPU clock at the generated CPU period, with0.5ns minimum/2ns maximum input and output delays. It models an external synchronous provider at the CPU phase origin without misusing MMCM compensation latency. All actual processor clocks remain related and timed. No asynchronous groups or multicycle exceptions are used. The only false path is asynchronous reset-button assertion to CLR/PRE/RST; release uses the existing two-clock synchronizer. Automatic device/MMCM jitter and phase uncertainty replace the blanket0.1ns override, which caused Timing38-195 under-budget warnings on virtual-clock paths. Full applied XDC and native clocks reports are included per implementation.

Remaining external-input hold violations could not be detoured on unlocated OOC port segments. The final ECO inserts LUT1 identity delays only on actual failing input paths. Each original leaf sink is disconnected from its own hierarchy-local net and reconnected with an explicit hierarchical connection. Connectivity is checked for every sink, and LUT INIT=2 implements O=I0. No flip-flop, processor instruction, scan chain, capture schedule or LBIST architecture is changed. Necessary physical delay cells are counted in routed utilization; DONT_TOUCH applies only to these hold delays. Failed early buffer-connection attempts left orphan cells, which are explicitly removed before final analysis and are not counted as production overhead. The final netlists and timing reports, not a list of requested ECO cells, establish whether repair succeeded.

## Frequency sweep

{table(sweep,['Variant','Configuration','FrequencyMHz','MMCMQuarterDutyLegal','WNS','WHS','SetupFails','HoldFails','TimingClean'])}

![Sweep](figures/frequency_sweep.png)

`frequency_sweep.csv` retains successful routing separately from timing closure. `cross_phase_timing.csv` records setup and hold for each clock pair. A point is accepted only with WNS≥0, TNS=0, WHS≥0, THS=0, no setup/hold/pulse failures, and no unintended unconstrained endpoints/ports. The intentionally false-pathed asynchronous reset is the only missing-input-delay exception. Small positive margins are reported as measured; no additional board margin or global maximum-frequency proof is inferred.

{table(cross,['Configuration','From','To','SetupWNS','HoldWHS','SetupFails','HoldFails'])}

## Matched final implementations

{table(selected,['Configuration','LUT','FF','LUTRAM','BRAM36Equivalent','DSP','CARRY4','Latches','BUFG','MMCM'])}

{table(selected,['Configuration','FrequencyMHz','WNS','TNS','WHS','THS','SetupFails','HoldFails','TimingClean'])}

{table(selected,['Configuration','LUTUtilizationPercent','FFUtilizationPercent','FirstSetupPathNS','PhysicalInputHoldBuffers'])}

{table(overhead,['Comparison','LUTDelta','LUTPercent','FFDelta','FFPercent'])}

![Area](figures/area_comparison.png)

All three final implementations use the same part, clock ratio, related phases, I/O contract and automatic uncertainty policy. All are synthesized from actual original/scan/full-LBIST processor sources with runtime instruction/data/test interfaces. Fault muxes and debug buses remain excluded. Physical hold repair uses the same demand-driven identity-buffer procedure. Post-implementation LUT/FF counts include all required repair cells; their per-port connectivity evidence is in `closed/{tag}/<configuration>/hold_buffer_connectivity.csv`. Historical BRAM-to-FF inference differences remain part of the existing helper implementation, not an ideal scan-mux cost. Original50MHz utilization is never substituted in these new-frequency tables.

Vivado still warns that unlocated OOC ports lack HD.PARTPIN_LOCS and the source lacks a board clock pin location. External port segments are not fully routed, so their real timing is not established by this experiment. Internal related-clock paths are analyzed; input/output timing depends on the stated virtual interface and partial-route model. These warnings prevent a board-level timing-closure or guaranteed operating-frequency claim. No package-pin feasibility or bitstream is claimed.

## Functional verification and activity

{table(native,['Case','Group','ClockMHz','CompletionPS','Result'])}

The nine accepted fresh cases cover the actual MMCM waveform, original/production-scan lwsw execution, injected stalls, all five production LBIST streams and Basic fault1 from the unchanged original universe. Each of the five256-pattern streams is checked against the independent response/signature/activity model, including all64scan bits, capture/unload ordering, isolation, reset-only restart and MISR sampling. The exact expected breakpoint and ten printed values are required for functional completion. No generic assertion waiver is used. Every accepted simulation is below100ms; watchdogs stay below that limit.

Native Vivado reopening verified all six new WDB/WCFG pairs: five production approaches and one injected-fault case. Every displayed signal resolves in its recorded database; the layouts use relative database paths. Functional verification uses state/output traces and its own SAIF, rather than a new native WDB. WDB/VCD/SAIF files are local generated artifacts and can be recreated using the verification command.

Simulation-only variants scale the existing CPU-phase fixtures and CLOCK_PER constant; original processor RTL is unchanged. The legacy simulation PLL splits fractional-picosecond half-ticks so its phases do not drift from the main clock at XSim's1ps resolution. The hardware board_clk remains100MHz and is independently tested through the real UNISIM MMCM. Generated-source manifests record the timing-only changes. Early failures due to Windows path parsing, an exit timestamp parser expecting integer nanoseconds, and rejected MMCM settings remain in `attempts/`/execution logs and supply no accepted PASS result.

The payload stays33,024cycles, so payload time is{33024*period/1e6:.9f}ms at this clock. The original16-fault full campaign remains historical50MHz logical evidence; it is not presented as a newly rerun campaign at this frequency. Fresh per-cycle switching measurements reproduce the original five approach streams. No additional fault site is introduced.

## Updated estimated power

{table(combined,['Approach','WTM','DynamicW','TotalW','CommonLUT','CommonFF','WNS','WHS','AnnotationPercent','Confidence','Status'])}

![Power](figures/dynamic_power.png)

![WTM and power](figures/wtm_power.png)

The same routed programmable C hardware serves every mode; mode changes do not change area. These are fresh selected-clock SAIF captures, not the old50MHz SAIF with a new clock constraint. All five use256patterns and the same actual measurement window: start at610×({period}/20)ns in SHIFT through completed UNLOAD, duration660540001×({period}/20)ps (rounded to simulator precision). Mapping manifests retain raw-file hashes, actual durations, original switching-record fingerprints and any additional physical identity-buffer input aliases. Aliases copy actual observed input activity, never invented rates. Unmatched lists and register-Q source-tag reports are included; their denominators are distinct from native whole-design net coverage and are not combined into an inflated percentage.

{table(power,['Approach','ClockW','LogicW','SignalsW','BRAMW','DSPW','MMCMW','MatchedNets','DesignNets','AnnotationPercent'])}

{table(refs,['Configuration','DynamicW','TotalW','MatchedNets','DesignNets','AnnotationPercent','Status'])}

{table(annotation,['Approach','ReportedRegisterQNetRows','SimulationRows','PropagatedRows','DefaultRows','OtherRows'])}

Overall power confidence and partial annotation remain explicit. Unmatched synthesis-generated logic, optimized-away debug nets and uninitialized processor nodes prevent complete RTL-to-route annotation; native propagation/defaults supply missing activity. The estimates are assumption-dominated where labeled. The register-Q report provides additional annotation context without changing the whole-design match percentage. No reliable experimentally demonstrated power ranking or physical savings is inferred from small rounded wattage differences. Reporting resolution is0.001W; independently rounded components need not sum exactly.

The previous whole-design SAIF matching figure was approximately13.92%. The new routed C netlist matches{power[0]['MatchedNets']}/{power[0]['DesignNets']} nets ({power[0]['AnnotationPercent']:.4f}%). Hierarchy normalization, generated-instance names and checked identity-buffer aliases were reviewed, but direct matching has not materially improved. The new result is retained as measured. Register-Q simulation/propagation counts use a different denominator and do not replace the native whole-design percentage. Most of the reported dynamic power is MMCM power, which further limits conclusions about the filter modes.

Conditions remain typical process,25°C ambient, nominal1.0V Vccint/Vccbram and1.8V Vccaux, with consistent generic Vivado thermal defaults. This is neither a calibrated Basys3 thermal model nor board measurement. MMCM VCO and CPU frequency differ from the original50MHz experiment, so differences across revisions are not evidence of PLPF energy savings. RTL SAIF omits routed glitches; caches/external memory/peripherals/package I/O/regulator power are outside the boundary.

## Reproduce

Run PowerShell from the repository root. Use Vivado2025.1.1 with installed xc7a35tcpg236-1 support; normal Vivado user-cache write access is required. No paid-only target or physical board is needed. Native project/checkpoint caches are outside OneDrive under `%TEMP%/vl405_timing*`.

```powershell
$vivado = 'E:/2025.1.1/Vivado/bin/vivado.bat'
# Repeat for baseline, scan_enabled and full_lbist:
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_timing_closure.tcl -tclargs full_lbist {m} {d}
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/close_timing_io.tcl -tclargs full_lbist {m} {d}
python lbist/scripts/prepare_timing_verification.py {m} {d}
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_timing_verification.tcl -tclargs {m} {d}
python lbist/scripts/audit_timing_verification.py {m} {d}
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/verify_timing_waveforms.tcl -tclargs {m} {d}
python lbist/scripts/prepare_timing_power.py {m} {d}
& $vivado -mode batch -nojournal -nolog -source lbist/scripts/run_timing_power.tcl -tclargs {m} {d}
python lbist/scripts/build_timing_report.py {m} {d}
python lbist/scripts/build_final_pdf.py
```

Redirect native stdout/stderr to a log within this revision when reproducing. The sweep can be repeated with other legal integer M/D values. Inspect actual setup, hold, cross-phase and unconstrained-path results; a successful command or synthesis result is not a PASS for timing. Source defaults and archived files preserve the original50MHz reproduction. Earlier project files are protected by the revision preservation audit; the report/PDF and clock-configuration files requested for update are excluded from that unchanged-file claim.

The complete selected-point flow is also available as `powershell -File lbist/scripts/run_timing_revision.ps1`. It runs only this revision, not historical campaigns. Early trial checkpoints had the documented orphan cells and uncertainty override; final physical repair removes those cells and reloads the common final constraints. The current clean runner omits those trial artifacts. Placement history and tool runs can change small slack/resource results; every reproduction must be accepted from its own final native reports, especially with the reported1ps minimum hold margin.

## Sources and limitations

- AMD [MMCME2_BASE, UG9532025.1](https://docs.amd.com/r/2025.1-English/ug953-vivado-7series-libraries/MMCME2_BASE), [Artix-7 DS181](https://docs.amd.com/v/u/en-US/ds181_Artix_7_Data_Sheet), and the installed MMCME2_ADV.vhd model's duty/phase counter checks establish supported parameters. Integer attributes alone do not guarantee a requested duty/phase is attainable.
- AMD [Virtual Clocks, UG9032025.1](https://docs.amd.com/r/2025.1-English/ug903-vivado-using-constraints/Virtual-Clocks) supports a separate I/O reference without changing the internal clock tree. This project's virtual contract is an explicit environmental assumption.
- AMD [connect_net](https://docs.amd.com/r/2025.1-English/ug835-vivado-tcl-commands/connect_net) and [disconnect_net](https://docs.amd.com/r/2025.1-English/ug835-vivado-tcl-commands/disconnect_net) document hierarchical ECO behavior. Connectivity must be checked because a failed hierarchical edit can return warnings rather than terminate Tcl.

The scope remains one64-bit IF/RF chain, eight capture sites with both polarities,256patterns, real processor capture and safe MISR completion. No whole-processor75% coverage, measured physical power saving, extra scan chain or board deployment is claimed.
'''
 (O/'README.md').write_text(prose(readme),encoding='utf-8')
 final=R/'Results/Final/Final_Report.md';text=final.read_text(encoding='utf-8')
 text=re.sub(r'<!-- TIMING_REVISION_BEGIN -->.*?<!-- TIMING_REVISION_END -->\n*','',text,flags=re.S)
 text=re.sub(r'^\*\*Timing revision:\*\*[^\n]*\n*','',text,flags=re.M)
 note=f'**Timing revision:** {state}. The latest analysis at {frequency:.9f} MHz is documented in [Timing_Closure](FPGA_Analysis/Timing_Closure/README.md). Earlier50MHz tables below remain labeled historical evidence.\n\n'
 text=text.replace('\n\n','\n\n'+prose(note),1)
 text=text.replace('The full 256-pattern processor experiments finish at 661.6002 us.',f'The original 50 MHz, 256-pattern processor experiments finish at 661.6002 us. The fresh clock-revision experiments finish at {int(metrics[0]["CompletionPS"])/1e9:.9f} ms at {frequency:.9f} MHz; their nine-case summary is included in the timing revision below.')
 text=text.replace('timing failure and partial activity annotation must accompany any area/power figures.','the historical 50 MHz timing failure, current narrow OOC timing margins, external-interface assumptions and partial activity annotation must accompany the corresponding area/power figures.')
 text=text.replace('## 17. FPGA Implementation, Area Overhead and Power Estimation\n','## 17. FPGA Implementation, Area Overhead and Power Estimation\n\n**Historical 50 MHz baseline:** The following original tables are preserved. The timing revision later in this section contains the current matched implementations.\n',1) if '**Historical 50 MHz baseline:**' not in text else text
 marker='### Final timing-closure revision'
 if marker in text:text=text[:text.index(marker)]+text[text.index('## 18.',text.index(marker)):]
 section=f'''{marker}

{clause}. Board reference100MHz; M={m}, common divider={d}, VCO={100*m}MHz; period={period}ns. Related quarter-duty phases remain unchanged. A virtual CPU I/O reference corrects the old external launch-latency model. Actual failing input hold paths are repaired with checked physical identity LUT delays; original processor/LBIST RTL is unchanged. Automatic MMCM/device uncertainty is used, with no false paths added beyond asynchronous reset assertion.

{table(selected,['Configuration','LUT','FF','Latches','BRAM36Equivalent','DSP'])}

{table(selected,['Configuration','FrequencyMHz','WNS','TNS','WHS','THS','SetupFails','HoldFails','TimingClean'])}

{table(overhead,['Comparison','LUTPercent','FFPercent'])}

![Updated area](FPGA_Analysis/Timing_Closure/figures/area_comparison.png)

The initial large-divider5/10MHz attempts were rejected by real MMCM duty/phase limits, despite ideal clock reports. The corrected legal sweep, cross-phase results, all failed attempts and exact clock attributes are retained in the [revision report](FPGA_Analysis/Timing_Closure/README.md). No frequency is inferred from1/(20ns−WNS). This is the highest tested common OOC point when all three rows are timing-clean, not a global or board-qualified maximum. Vivado warns about unlocated OOC ports without HD.PARTPIN_LOCS: external segments are not fully routed, and real external-interface timing is not established. The scan-enabled hold margin is only0.001ns. These results do not qualify a board implementation or supply additional timing margin.

Nine fresh simulations passed at this clock: real UNISIM phase/duty verification, original/scan lwsw with and without stalls, all five complete production streams and the original Basic fault1. Independent checking confirms all256captures, each prefix signature and measured activity counts. Original50MHz fault-campaign data remains historical; no expanded fault universe or new whole-processor coverage claim is introduced. Payload time is{33024*period/1e6:.9f}ms for33,024cycles. Updated execution times and activity windows are recorded separately.

{table(combined,['Approach','WTM','DynamicW','CommonLUT','CommonFF','AnnotationPercent','Confidence'])}

![Updated estimated power](FPGA_Analysis/Timing_Closure/figures/dynamic_power.png)

![Fresh WTM versus estimated power](FPGA_Analysis/Timing_Closure/figures/wtm_power.png)

Each power case uses fresh selected-clock activity on the same routed C netlist, not a50MHz SAIF reused with a new timing constraint. Partial matching and propagation/default assumptions remain visible; small0.001W report differences do not establish physical savings or a reliable ranking. Supply/ambient/process assumptions are consistent. All native utilization, timing, power, unmatched-net and register-Q annotation reports are available in Timing_Closure. Clock-only source changes, physical repair cells, unsupported5MHz quarter-duty generation and OOC interface assumptions are fully documented there.

'''
 text=text.replace('## 18.',prose(section)+'\n## 18.',1)
 final.write_text(text,encoding='utf-8')
 parent=R/'Results/Final/FPGA_Analysis/README.md';s=parent.read_text(encoding='utf-8')
 s=re.sub(r'<!-- TIMING_NOTE_BEGIN -->.*?<!-- TIMING_NOTE_END -->\n*','',s,flags=re.S)
 s=re.sub(r'^\*\*Latest timing revision:\*\*[^\n]*\n*','',s,flags=re.M)
 parent.write_text(prose(f'**Latest timing revision:** {state}; see [Timing_Closure](Timing_Closure/README.md) for the matched {frequency:.9f} MHz results. The tables below are the retained original 50 MHz baseline.\n')+'\n'+s,encoding='utf-8')
 source_files=[R/'lbist/final/final_clock_tree.vhd',R/'lbist/final/final_fpga_top.vhd']+list((R/'lbist/scripts').glob('*timing*'))+[R/'lbist/tb/tb_timing_clock_tree.vhd']
 write(O/'source_manifest.csv',[dict(File=str(p.relative_to(R)).replace('\\','/'),SHA256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in source_files if p.is_file()])
 (O/'selection.json').write_text(json.dumps(dict(Mult=m,Divide=d,FrequencyMHz=frequency,PeriodNS=period,AllThreeTimingClean=clean,Selection=clause),indent=2))
 print('Timing revision report generated:',state)
if __name__=='__main__':main()
