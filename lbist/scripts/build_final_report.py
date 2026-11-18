"""Consolidate existing measurements and native final reports, without rerunning history."""
from pathlib import Path
import csv,re,shutil,statistics,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from audit_final_evidence import write
from phase5a_trace import Phase5Trace

R=Path(__file__).resolve().parents[2];O=R/'Results/Final';F=O/'figures';P=O/'FPGA_Analysis'
NAMES=['Direct','Constant n=3','Basic','Swap','Moving']
def rows(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig'))) if path.exists() else []
def prior(name):return rows(R/'Results/Phase6A/reports'/('phase6a_'+name+'.csv'))
def table(rs,columns):
    def fmt(v):return (str(int(v)) if v.is_integer() else f'{v:.4f}') if isinstance(v,float) else str(v)
    labels={'EstimatedDynamicW':'Dynamic (W)','CommonLUT':'Shared LUT','CommonFF':'Shared FF','RoutedWNS':'WNS (ns)',
            'FirstDirectMin':'First direct min','FirstDirectMax':'First direct max','FirstDirectMean':'Mean (detected)',
            'PatternsTo75':'Patterns to 75%','PayloadCyclesTo75':'Cycles to 75%','FullTestCycles':'Full cycles',
            'SetupFailingEndpoints':'Setup fails','FirstSetupPathDelayNS':'Path (ns)','TimingClosure':'Closure',
            'LUTOverheadPercent':'LUT overhead (%)','FFOverheadPercent':'FF overhead (%)','LUTDelta':'LUT delta','FFDelta':'FF delta',
            'WithinTolerance':'Within 0.5 pp','WNS_NS':'WNS (ns)','TNS_NS':'TNS (ns)','WHS_NS':'WHS (ns)'}
    return '| '+' | '.join(labels.get(k,k) for k in columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(k,'')) for k in columns)+' |' for r in rs)
def save(fig,name,folder=F):
    folder.mkdir(parents=True,exist_ok=True);fig.tight_layout()
    for ext in ['svg','png','pdf']:fig.savefig(folder/(name+'.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)
def util(path,label):
    if not path.exists():return ''
    m=re.search(r'^\|\s*'+re.escape(label)+r'\s*\|\s*([\d.]+)',path.read_text(),re.M)
    if not m:return ''
    value=float(m[1]);return int(value) if value.is_integer() else value
def fpga():
    resources=[];timing=[]
    for config in ['baseline','scan_enabled','full_lbist']:
        folder=P/config
        routed=folder/'routed_utilization.rpt'
        u=routed if routed.exists() else folder/'synthesis_utilization.rpt'
        r=dict(Configuration=config,Part='xc7a35tcpg236-1',Stage='Routed' if routed.exists() else 'Synthesized',
               LUT=util(u,'Slice LUTs') if routed.exists() else util(u,'Slice LUTs*'),FF=util(u,'Register as Flip Flop'),Latches=util(u,'Register as Latch'),
               LUTRAM=util(u,'LUT as Memory'),BRAM36Equivalent=util(u,'Block RAM Tile'),DSP=util(u,'DSPs'),
               Carry=util(u,'CARRY4'),BUFG=util(u,'BUFGCTRL'),MMCM=util(u,'MMCME2_ADV'))
        # Primitive table has an extra count column but still starts with the count.
        if r['LUT']!='':r['LUTPercent']=100*r['LUT']/20800;r['FFPercent']=100*r['FF']/41600
        resources.append(r)
        t=folder/'routed_timing.rpt'
        if not t.exists():t=folder/'synthesis_timing.rpt'
        text=t.read_text() if t.exists() else ''
        m=re.search(r'WNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)',text,re.S)
        delays=re.findall(r'Data Path Delay:\s*([\d.]+)ns',text)
        timing.append(dict(Configuration=config,Stage='Routed' if (folder/'routed_timing.rpt').exists() else 'Synthesized',
                           CPUPeriodNS=20,BoardPeriodNS=10,WNS_NS=m[1] if m else '',TNS_NS=m[2] if m else '',
                           SetupFailingEndpoints=m[3] if m else '',WHS_NS=m[5] if m else '',THS_NS=m[6] if m else '',
                           FirstSetupPathDelayNS=delays[0] if delays else '',
                           TimingClosure='FAIL' if m and (float(m[1])<0 or float(m[5])<0) else 'PASS' if m else 'NOT_AVAILABLE',
                           FmaxMHz='NOT_JUSTIFIED_MULTIPHASE'))
    write('FPGA_Analysis/synthesis_summary.csv',resources);write('FPGA_Analysis/timing_summary.csv',timing)
    execution=[]
    power_status=rows(P/'power/status.csv')
    for i,config in enumerate(['baseline','scan_enabled','full_lbist']):
        raw=rows(P/config/'status.csv')
        for stage in ['synthesis','implementation']:
            entry=next((r for r in raw if r['Stage']==stage),{})
            execution.append(dict(Configuration=config,Stage=stage,Status=entry.get('Status','NOT_AVAILABLE'),Evidence=f'{config}/status.csv'))
        entries=[r for r in power_status if r['Configuration']==config]
        execution.append(dict(Configuration=config,Stage='final own-SAIF power exports',Status='PASS' if len(entries)==(5 if i==2 else 1) and all(r['Status']=='PASS' for r in entries) else 'INCOMPLETE',Evidence='power/status.csv'))
        execution.append(dict(Configuration=config,Stage='routed timing closure',Status=timing[i]['TimingClosure'],Evidence=f'{config}/routed_timing.rpt'))
        source=O/(config+'_fpga.log')
        if source.exists():shutil.copy2(source,P/config/'execution.log')
    write('FPGA_Analysis/execution_summary.csv',execution)
    overhead=[]
    for a,b,label in [(0,1,'Scan/isolation vs baseline'),(0,2,'Complete LBIST vs baseline'),(1,2,'LBIST addition vs scan/isolation')]:
        if all(resources[k].get('LUT')!='' for k in [a,b]):
            overhead.append(dict(Comparison=label,LUTDelta=resources[b]['LUT']-resources[a]['LUT'],
                                  LUTOverheadPercent=100*(resources[b]['LUT']-resources[a]['LUT'])/resources[a]['LUT'],
                                  FFDelta=resources[b]['FF']-resources[a]['FF'],
                                  FFOverheadPercent=100*(resources[b]['FF']-resources[a]['FF'])/resources[a]['FF'],
                                  Stage=resources[b]['Stage']))
    if overhead:write('FPGA_Analysis/area_overhead.csv',overhead)
    fig,ax=plt.subplots(figsize=(7.3,4))
    for off,key,color in [(-.18,'LUT','#176c91'),(.18,'FF','#ce7b22')]:
        vals=[r[key] if r[key]!='' else float('nan') for r in resources]
        bars=ax.bar([i+off for i in range(3)],vals,.36,label=key,color=color);ax.bar_label(bars,fmt='%.0f',fontsize=8)
    ax.set_xticks(range(3),['A: original','B: scan/isolation','C: complete LBIST']);ax.set_ylabel('Used FPGA resources');ax.legend()
    save(fig,'area_comparison',P/'figures')
    return resources,timing,overhead

def architecture():
    fig,ax=plt.subplots(figsize=(12,6.7));ax.set(xlim=(0,12),ylim=(0,7));ax.axis('off')
    def box(x,y,w,h,text,color='#e5f1f5'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',fc=color,ec='#284758',lw=1.4))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10)
    def arrow(x,y,u,v,label=''):
        ax.annotate('',(u,v),(x,y),arrowprops=dict(arrowstyle='->',lw=1.4,color='#284758'))
        if label:ax.text((x+u)/2,(y+v)/2+.15,label,ha='center',fontsize=8)
    box(.2,5.4,2.1,1,'Host\nstart / pause / abort\napproach / golden')
    box(3.1,5.4,3,1,'Test controller\n64 SHIFT / CAPTURE / 64 UNLOAD')
    box(7.1,5.4,4.3,1,'Isolation handshake + protected core state\nPC, RF/EX, EX/MM, MM/WB, GPR, CP0')
    box(.2,3,2.1,1.3,'16-bit LFSR\n+ combinational\nphase shifter')
    box(3.1,3,3,1.3,'Programmable pattern router\nDirect / n=3 / Basic / Swap / Moving\ndynamic PLPF + Q(0) feedback')
    box(7.1,3,4.3,1.3,'Actual IF/RF scan register: 64 bits\nPCincd_q[31:0] + RF_instr[31:0]\nscan-in Q(0)  →  Q(63) scan-out','#e8f1df')
    box(7.1,.5,4.3,1.3,'Real capture cone\naligned scan-loaded PC operand → +4\nheld instruction ROM → IF/RF')
    box(3.1,.5,3,1.3,'16-bit safe MISR + comparator\nvalid only after complete test\nMATCH / fault_detected')
    box(.2,.5,2.1,1.3,'Common MMCM\n50 MHz clk, phi1, phi2\n100 MHz input')
    arrow(2.3,5.9,3.1,5.9);arrow(6.1,5.9,7.1,5.9,'TM / ACK')
    arrow(2.3,3.65,3.1,3.65);arrow(6.1,3.65,7.1,3.65,'serial input')
    arrow(7.1,3.15,6.1,3.15,'Q(0) feedback')
    arrow(9.25,1.8,9.25,3,'CAPTURE')
    arrow(7.1,3.2,6.1,1.55,'real scan-out / UNLOAD')
    arrow(4.6,5.4,4.6,4.3,'phase / enable')
    ax.text(6,.03,'Production boundary excludes fault-injection muxes, debug buses, testbenches and external memory/peripherals.',ha='center',fontsize=9)
    save(fig,'architecture')

def waveforms():
    trace=Phase5Trace(R/'Results/Phase6A/Faults/waveforms/c2_f0.vcd');prefix='/tb_phase6a_fault_comparison/engine'
    events=[(t,v) for t,v in trace.values(prefix,'capture_enable') if v=='1']
    cap=events[0][0]+20000 # accepted capture edge lies within next CPU period
    begin=max(0,cap-85000);end=cap+105000
    names=['clk','test_phase','scan_enable','mode_select','capture_enable','misr_enable','scan_out','signature','signature_valid']
    fig,axes=plt.subplots(len(names),1,figsize=(11,6.5),sharex=True)
    for ax,name in zip(axes,names):
        code,width=trace.signals[prefix+'/'+name]
        ev=[(begin,trace.value(prefix,name,begin))]+[(t,v) for t,v in trace.values(prefix,name) if begin<t<end]+[(end,trace.value(prefix,name,end))]
        if width==1:
            ax.step([t/1000 for t,v in ev],[int(v,2) if set(v)<={'0','1'} else .5 for t,v in ev],where='post',color='#176c91');ax.set_ylim(-.2,1.2);ax.set_yticks([0,1])
        else:
            for (a,v),(b,_) in zip(ev,ev[1:]):
                ax.plot([a/1000,b/1000],[.5,.5],color='#176c91',lw=5)
                if b-a>8000:ax.text((a+b)/2000,.53,format(int(v,2),'X') if set(v)<={'0','1'} else 'X',ha='center',fontsize=8)
            ax.set_ylim(0,1);ax.set_yticks([])
        ax.set_ylabel(name,rotation=0,ha='right',va='center',fontsize=9);ax.grid(axis='x',alpha=.2)
    axes[0].set_title('Actual XSim waveform: Basic, first SHIFT → CAPTURE → UNLOAD (buses in hex)')
    axes[-1].set_xlabel('Recorded simulation time (ns)');save(fig,'scan_capture_unload')
    shutil.copy2(R/'Results/Phase6A/Router/waveforms/safety_case_1_zoom.svg',F/'misr_abort.svg')
    safety=Phase5Trace(R/'Results/Phase6A/Router/waveforms/safety.vcd');prefix='/tb_phase6a_misr_safety'
    begin=next(t for t,v in safety.values(prefix,'scenario') if int(v,2)==1)
    end=next(t for t,v in safety.values(prefix,'scenario') if t>begin)
    names=['rst','phase','ce','unload','done','err','q','valid','match','detected']
    fig,axes=plt.subplots(len(names),1,figsize=(10,6.5),sharex=True)
    for ax,name in zip(axes,names):
        code,width=safety.signals[prefix+'/'+name]
        ev=[(begin,safety.value(prefix,name,begin))]+[(t,v) for t,v in safety.values(prefix,name) if begin<t<end]+[(end,safety.value(prefix,name,end-1))]
        if width==1:
            ax.step([t/1000 for t,v in ev],[int(v,2) for t,v in ev],where='post',color='#176c91');ax.set_yticks([0,1]);ax.set_ylim(-.2,1.2)
        else:
            for (a,v),(b,_) in zip(ev,ev[1:]):
                ax.plot([a/1000,b/1000],[.5,.5],color='#176c91',lw=4)
                if b-a>1500:ax.text((a+b)/2000,.53,format(int(v,2),'X'),ha='center',fontsize=8)
            ax.set_ylim(0,1);ax.set_yticks([])
        ax.set_ylabel(name,rotation=0,ha='right',va='center',fontsize=9);ax.grid(axis='x',alpha=.2)
    axes[0].set_title('Actual XSim safety trace: abort during SHIFT suppresses valid and MATCH')
    axes[-1].set_xlabel('Recorded simulation time (ns)');save(fig,'misr_abort_trace')

def main():
    F.mkdir(parents=True,exist_ok=True);(O/'tables').mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    wtm=prior('wtm_comparison');fault=prior('fault_campaign');coverage=prior('fault_coverage');gold=prior('golden_signatures')
    primary=[];latency=[]
    for cid in range(5):
        w=next(r for r in wtm if int(r['Config'])==cid);fc=[r for r in fault if int(r['Config'])==cid]
        g=next(r for r in gold if int(r['Config'])==cid)
        det=[r for r in fc if r['DirectDetected']=='True'];ds=[int(r['FirstDirect']) for r in det]
        ms=[int(r['FirstMISR']) for r in fc if r['FirstMISR']]
        primary.append(dict(Approach=NAMES[cid],Beta=w['Beta'] if cid>1 else 'fixed',EstimatedWTM=float(w['EstimatedWTM']),
            MeasuredWTM=float(w['MeasuredWTM']),SerialToggleRate=w['SerialToggleRate'],ScanFFSwitching=w['ScanFFSwitching'],
            DirectDetected=len(det),MISRDetected=sum(r['MISRDetected']=='True' for r in fc),EligibleFaults=16,
            CoveragePercent=100*sum(r['MISRDetected']=='True' for r in fc)/16,Golden=g['Signature'],Actual=g['ActualSignature'],
            Aliases=sum(r['Aliasing']=='True' for r in fc),Patterns=256,SHIFT=16384,CAPTURE=256,UNLOAD=16384,PayloadCycles=33024,
            CompleteSimulationUS=661.6002))
        latency.append(dict(Approach=NAMES[cid],Detected=len(det),Undetected=16-len(det),FirstDirectMin=min(ds),
                            FirstDirectMax=max(ds),FirstDirectMean=statistics.mean(ds),FirstPrefixMISRMin=min(ms),
                            FirstPrefixMISRMax=max(ms),PatternsTo75=4,PayloadCyclesTo75=516,FullTestCycles=33024))
    write('final_experimental_comparison.csv',primary);write('tables/detection_latency_summary.csv',latency)
    for name in ['feasibility','matched_comparisons','fault_inventory','fault_campaign','fault_coverage','golden_signatures','misr_aliasing','test_cycles','thresholds']:
        write('tables/'+name+'.csv',prior(name))
    fig,ax=plt.subplots(figsize=(8,4));bars=ax.bar(NAMES,[r['MeasuredWTM'] for r in primary],color=['#7c8c99','#8fb58b','#176c91','#ce7b22','#8a619a'])
    ax.bar_label(bars,fmt='%.2f%%');ax.set(ylabel='Weighted scan-FF transition metric (%)',ylim=(0,57));save(fig,'wtm_comparison')
    fig,ax=plt.subplots(figsize=(7.8,4))
    for cid in range(5):
        rs=[r for r in coverage if int(r['Config'])==cid]
        ax.plot([int(r['Patterns']) for r in rs],[float(r['MISRCoverage']) for r in rs],marker=['o','s','^','D','x'][cid],label=NAMES[cid],alpha=.7)
    ax.set(xscale='log',xlabel='Completed patterns (log scale)',ylabel='Coverage of original 16 faults (%)',ylim=(0,100));ax.legend(ncol=3,fontsize=8);save(fig,'fault_coverage')
    fig,ax=plt.subplots(figsize=(7.8,4))
    for a,color in [('basic','#176c91'),('swap','#ce7b22'),('moving','#8a619a')]:
        rs=[r for r in prior('feasibility') if r['Approach']==a and r['Feasible']=='True']
        ax.plot([float(r['Target']) for r in rs],[float(r['MeasuredWTM']) for r in rs],'o-',label=a.title(),color=color)
    ax.plot([9,21],[9,21],'k--',label='Requested = measured');ax.set(xlabel='Requested WTM (%)',ylabel='Measured WTM (%)');ax.legend();save(fig,'target_vs_measured')
    architecture();waveforms();res,timing,overhead=fpga()
    power=rows(P/'power_comparison.csv')
    for i,r in enumerate(primary):
        p=next((p for p in power if p.get('Approach')==r['Approach']),{})
        r.update(EstimatedDynamicW=p.get('DynamicW',''),CommonRouterLUT=res[2]['LUT'],CommonRouterFF=res[2]['FF'],
                 RoutedWNS_NS=timing[2]['WNS_NS'],PowerStatus=p.get('Status','NOT_AVAILABLE'))
    write('FPGA_Analysis/approach_comparison.csv',primary)
    if power and all(p.get('DynamicW','') for p in power):
        fig,ax=plt.subplots(figsize=(8,4));bars=ax.bar([p['Approach'] for p in power],[float(p['DynamicW'])*1000 for p in power],color='#176c91')
        ax.errorbar(range(5),[float(p['DynamicW'])*1000 for p in power],yerr=.5,fmt='none',color='#444',capsize=3)
        ax.bar_label(bars,fmt='%.0f');ax.set(ylabel='Vivado estimated dynamic power (mW)',title='Assumption-dominated whole-C estimates; ±0.5 mW rounding');save(fig,'dynamic_power',P/'figures')
        fig,ax=plt.subplots(figsize=(7.8,4))
        for i,(w,p) in enumerate(zip(primary,power)):
            ax.errorbar(w['MeasuredWTM'],float(p['DynamicW'])*1000,yerr=.5,fmt='o',capsize=3)
            ax.annotate(w['Approach'],(w['MeasuredWTM'],float(p['DynamicW'])*1000),fontsize=8,xytext=(5,12 if i==2 else -17 if i==4 else 3),textcoords='offset points')
        ax.set(xlabel='Measured SHIFT-only WTM (%)',ylabel='Estimated C dynamic power (mW)',ylim=(122,125.5),
               title='Assumption-dominated estimate\nError bars show rounding; model uncertainty is unquantified');save(fig,'wtm_vs_power',P/'figures')
    render_report(primary,latency,res,timing,overhead,power)
    print('Final measured tables, figures and report generated.')

def render_report(primary,latency,res,timing,overhead,power):
    verification=rows(O/'Verification/Essential/reports/tb_lfsr_16.csv')
    essentials=[r for p in (O/'Verification/Essential/reports').glob('*.csv') if not p.stem.endswith('_samples') for r in rows(p)]
    activities=[r for p in (O/'Verification/Activity/reports').glob('*.csv') for r in rows(p)]
    archived=rows(O/'Verification/archived_campaign_audit.csv');waves=rows(O/'Verification/archived_waveform_audit.csv');preserved=rows(O/'Verification/preservation_audit.csv')
    status=[dict(Category='Fresh essential XSim',Passed=sum(r['Result']=='PASS' for r in essentials),Total=len(essentials)),
            dict(Category='Fresh production equivalence/activity',Passed=sum(r['Result']=='PASS' for r in activities),Total=len(activities)),
            dict(Category='Fresh original/production-scan functional activity',Passed=sum(r['Result']=='PASS' for r in rows(O/'Verification/FunctionalActivity/reports/functional_activity.csv')),Total=1),
            dict(Category='Fresh representative original-universe fault',Passed=sum(r['Result']=='PASS' for r in rows(O/'Verification/FaultDemo/reports/basic_fault_1.csv')),Total=1),
            dict(Category='Fresh native WDB/WCFG pairs reopened',Passed=6 if (O/'native_waveform_audit.log').exists() and 'FINAL NATIVE WAVEFORM AUDIT: 6/6 PASS' in (O/'native_waveform_audit.log').read_text() else 0,Total=6),
            dict(Category='Archived processor experiments independently rechecked',Passed=len(archived),Total=204),
            dict(Category='Archived waveform figures rechecked against VCD',Passed=len(waves),Total=45),
            dict(Category='Earlier files unchanged by SHA-256',Passed=sum(r['Result']=='PASS' for r in preserved),Total=len(preserved))]
    write('Verification/verification_summary.csv',status)
    concise=[dict(Approach=r['Approach'],Beta=r['Beta'],WTM=f"{r['MeasuredWTM']:.4f}%",Coverage=f"{r['MISRDetected']}/16",Golden=r['Golden'],Aliases=r['Aliases'],Patterns=r['Patterns'],Cycles=r['PayloadCycles']) for r in primary]
    area=[dict(Configuration=r['Configuration'],LUT=r['LUT'],FF=r['FF'],Latches=r['Latches'],BRAM=r['BRAM36Equivalent'],DSP=r['DSP'],Stage=r['Stage']) for r in res]
    target=[dict(Approach=r['Approach'].title(),Target=r['Target'],Beta=r['Beta'],Estimate=f"{float(r['EstimatedWTM']):.4f}",Measured=f"{float(r['MeasuredWTM']):.4f}" if r['MeasuredWTM']!='NOT_RUN' else 'NOT_RUN (infeasible)',WithinTolerance=r['MeasuredMatched']) for r in prior('feasibility') if r['Approach'] in ['basic','swap','moving']]
    combined=[dict(Approach=r['Approach'],WTM=f"{r['MeasuredWTM']:.4f}%",EstimatedDynamicW=r.get('EstimatedDynamicW',''),CommonLUT=r['CommonRouterLUT'],CommonFF=r['CommonRouterFF'],RoutedWNS=r['RoutedWNS_NS']) for r in primary]
    subsystem=rows(P/'power/subsystem_comparison.csv')
    report=f'''# VL405: Scan-Based Low-Switching LBIST for cMIPS32

**Final submission report — repository S4K50M/LBIST.** Historical implementation baseline: commit `2c9b90c` (Phase 6A). Target: Basys 3 Artix-7 `xc7a35tcpg236-1`; tool: AMD Vivado/XSim 2025.1.1. All numerical experiment results below are derived from retained native logs/CSVs. FPGA figures use the final native reports, with analysis stage explicitly identified.

## 1. Abstract

This project implements and verifies a programmable pseudorandom scan-test system around one 64-bit IF/RF pipeline register in cMIPS32. A 16-bit LFSR, combinational phase shifter and dynamic PLPF supply Direct, constant n=3, Basic, Swap and Moving approaches. Processor isolation protects architectural state while a controller performs 64 SHIFT, one CAPTURE and 64 UNLOAD edges per pattern. A completion-safe 16-bit MISR compresses actual serial responses. With 256 patterns, every initial approach detects 12 of the same 16 capture-input stuck-at faults, with no observed final-signature alias. Measured SHIFT WTM spans 7.0665%–50.1154%. These are simulation switching metrics; the FPGA power study is a separate tool estimate. The results establish this limited capture-cone experiment, not whole-processor fault coverage or measured physical power savings.

## 2. Introduction and problem statement

Scan shifting can cause sustained internal transitions. Filtering pseudorandom stimulus offers a controllable activity tradeoff, but it must preserve scan ordering, functional behavior, capture timing and response integrity. The project asks whether the existing filter/control approaches can operate on real cMIPS pipeline storage with reproducible results and safe error handling. The submission freezes the verified Phase 6A architecture. It adds production integration wrappers, final verification, reporting and FPGA analysis; no additional scan chain or fault site is introduced.

## 3. Reference paper and proposed methodology

Kato, Wang, Sato, Kajihara and Wen [1] motivate programmable scan-in activity using modified pseudorandom patterns. This project evaluates that principle on cMIPS. It reuses the established Basic/Swap/Moving schedules and independently checks every applied scan bit. The RTL uses counters and combinational decoders; it does not claim the paper's exact gate structure, silicon area, TEG measurements or general fault-coverage results. This report's measured values come from the repository's own experiment evidence.

## 4. cMIPS32 architecture

cMIPS is a five-stage VHDL processor: instruction fetch, register fetch, execute, memory and writeback [2]. Pipeline boundaries are `reg_IF_RF`, `reg_RF_EX`, `reg_EX_MM` and `reg_MM_WB` in `cMIPS/vhdl/pipestages.vhd`. The original functional core, exception/control logic and register storage are preserved. `docs/scan_register_inventory.csv` records widths, resets, types and scan decisions. Boolean/enumerated state needs deliberate encoding; it is not silently flattened into the implemented chain. The remaining 656 pipeline candidate bits are unscanned.

## 5. LBIST system architecture

![Production architecture](figures/architecture.png)

`final_processor_system.vhd` selects original core (A), scan/isolation core (B), or the complete programmable LBIST core (C). C instantiates the verified controller, router, `core_scan_test` and safe MISR. Real scan Q(0) feeds the filter and Q(63) supplies the analyzer. Approach and golden signature are external configuration inputs held stable throughout a test. Test mode remains a real runtime control. Fault injection and wide debug probes are absent from production C; observation outputs on the core are open.

## 6. LFSR and phase shifter

The polynomial is x^16+x^15+x^13+x^4+1. State bit i denotes sequence position j+i; output is state(0), and feedback is state(15) XOR state(13) XOR state(4) XOR state(0). Reset seeds AAAA; zero/unknown seed protection is retained. The period bench checks all 65,535 unique nonzero states, sequence recurrence, bit balance, pause, resume and reset. The phase shifter exposes state(0), state(1), state(2) as current/next/next-next without extra cycles. The integrated experiment uses one scan chain; historical multi-chain standalone tests do not imply multiple processor scan chains.

## 7. PLPF design and WTM control

The dynamic PLPF is combinational. Mode 11 passes the current LFSR bit (n=1). Mode 01 combines two consecutive bits and real scan-input-stage feedback (n=2). Mode 00 similarly uses three bits (n=3). For feedback zero, the selected bits are ANDed; for feedback one they are ORed. Invalid mode holds feedback and raises invalid status. There is no extra shift for mode changes.

Measured WTM = 100 × sum over 256 patterns, 64 SHIFT edges and physical stages k of (k+1) × [Q_k changes], divided by 256 × 64 × 2080. Input-stage weight is 1 and output-stage weight is 64. CAPTURE and UNLOAD transitions are excluded from this metric. Serial toggle rate and unweighted scan-FF switching are separate CSV columns. Theoretical WTM is an optimization estimate, not an assertion that a finite deterministic sequence reaches an arbitrary requested target.

## 8. Basic, Swap and Moving controllers

Basic beta=20 uses physical regions alpha/beta/gamma=22/20/22. Physical order is scan-in → alpha → beta → gamma → scan-out; chronological injection reverses it. Swap beta=16 alternates gamma=32 and 16 on successive captured patterns. Moving beta=20 uses gamma=14+p mod 17 and alpha=64−20−gamma. The minimum 14-cell filtered ends restrict the reachable unfiltered region. The offline optimizer chooses legal integer lengths; it is not on-chip optimization hardware.

Swap and Moving have separate SHIFT and UNLOAD scheduling instances. Both process schedule p; only the next SHIFT uses p+1. This avoids double-advancing the schedule during disposable unload shifts. LFSR state advances on every accepted SHIFT or UNLOAD, and holds during CAPTURE/pause. C's shared runtime router uses beta=20 and Swap beta=16 for all five modes; changing runtime mode does not change synthesized area.

## 9. Scan-chain insertion

Only IF/RF is replaced by verified `reg_IF_RF_scan`: 32 PC-increment bits plus 32 instruction bits. The combined word is PCincd_q & RF_instr, with serial insertion at bit0, output at bit63 and MSB-first unload. Scan disabled reproduces original load/reset behavior. The unit bench checks all 64 positions, feedback, reset, load/hold and scan priority. Native original-versus-scan processor regression compares internal pipeline values and functional buses under lwsw and memory stalls.

## 10. Processor test-mode isolation

Entry waits for idle external fabric and synchronized phase acknowledgements. The isolation boundary holds PC, downstream pipeline registers, general registers, exception/CP0 storage and side effects. Memory and register write attempts are monitored; committed writes remain suppressed. Only a legal CAPTURE updates IF/RF. Tests perturb interrupts, waits, errors, readiness, pause and attempted early exit. Exit is reset-only; arbitrary resume from destructively shifted IF/RF state is unsupported. Autonomous external peripherals are outside the protected core boundary.

## 11. MISR response compression

The analyzer polynomial is x^16+x^12+x^5+1 (mask 1021), seed zero. Each UNLOAD edge uses actual pre-shift scan_out. The last response bit updates the signature before comparison settles. Phase 6A validity requires DONE phase 101, successful controller completion, 256 captures, 16,384 response bits, 256 complete unload words, matching controller pattern count and no sticky stream/controller error. MATCH and fault_detected stay low until signature_valid. A completed faulty stream is valid and may mismatch; abort/incomplete streams cannot claim MATCH. Eight safety scenarios cover normal/faulty completion, abort in each active phase, missing response, illegal restart and reset. Historical unsafe Phase 5B files remain unchanged for provenance and are not used in production C.

![Abort does not produce a valid signature](figures/misr_abort_trace.png)

## 12. Fault-injection methodology

The primary universe contains eight sites × SA0/SA1: increment_operand bits 2,3,16,31 before the original +4 adder, and instruction_input bits 0,1,16,31 before IF/RF capture. Fault muxes act only during legal CAPTURE. Injection is on real capture inputs, not scan-output corruption. Upper response is the aligned scan-loaded operand plus4 through the original processor adder; lower response is actual held-ROM instruction 1460FFFA at PC 2C. Other processor logic remains held. This small cone is not the full datapath, ALU or instruction-set universe. Detected IDs are 1–8,10,11,14,16; IDs 9,12,13,15 have the already-held instruction polarity and are not excited. `tables/fault_inventory.csv` supplies exact sites and activation paths.

## 13. Verification and experimental setup

All accepted simulations remain below 100 ms simulated time. The full 256-pattern processor experiments finish at 661.6002 us. Original Phase 1–6A artifacts are retained. Finalization rechecks the archived 204 experiments against independent stimulus/response/MISR/activity models, rather than rewriting historical campaigns. Fresh native tests exercise generator/filter/controllers, scan, isolation, safe analyzer/router, functional equivalence, and production C against the verified reference. The production fixture checks functional ports, real scan interface and analyzer outputs at all CPU phases, while recording its own switching activity.

{table(status,['Category','Passed','Total'])}

The expected original `RF_STOP_SIMULATION` assertion at breakpoint PC00000038 terminates lwsw. It counts as success only with matching differential state, the exact breakpoint and ten printed values FFFFFFF6…FFFFFFFF. Other failures are rejected. The old incomplete sixteen-replica Moving native attempt is excluded; its smaller retries provide complete accepted records. Fresh script errors, if any, remain in execution logs and are not relabeled as simulation passes. See `Verification/` and `final_verification_summary.md`.

## 14. WTM results

{table(concise,['Approach','Beta','WTM','Coverage','Golden','Aliases','Patterns','Cycles'])}

![Measured WTM](figures/wtm_comparison.png)

![Requested and measured WTM](figures/target_vs_measured.png)

{table(target,['Approach','Target','Beta','Estimate','Measured','WithinTolerance'])}

Target 10% optimizer configurations achieve 9.4148–9.4866%: close to one another but outside the declared ±0.5 percentage-point target tolerance. At 15%, Basic/Swap/Moving achieve 14.6669/15.0168/14.8169%, respectively. Swap20% is infeasible with the legal L64 bounds; nearest beta18 estimates19.1964%. Moving beta19 is the optimizer-selected20% candidate and measures19.1090%; the separately tested beta20 calibration measures19.8701%. Neither is relabeled. All exact feasibility and pairwise match decisions are retained in `tables/feasibility.csv` and `tables/matched_comparisons.csv`.

## 15. Fault-coverage results

![Original fault coverage](figures/fault_coverage.png)

All five initial approaches reach 75% of the 16 eligible capture-input faults after four complete patterns. All retain 12/16 direct and final-MISR detections at256 patterns. No final alias is observed in these deterministic experiments. Four unexcited faults produce equal direct responses and equal signatures; they are not aliases. A 16-bit signature still has a finite alias risk for other responses and workloads; zero observed aliases is not proof of zero alias probability. The complete80 primary faulty signatures, first direct/prefix-MISR detection indices and outcomes are retained in the campaign/aliasing CSVs. Additional measured target profiles are secondary evidence and preserve the same denominator.

## 16. Test-time analysis

{table(latency,['Approach','Detected','Undetected','FirstDirectMin','FirstDirectMax','FirstDirectMean','PatternsTo75','PayloadCyclesTo75','FullTestCycles'])}

Each test executes256 × (64+1+64)=33,024 payload cycles:16,384SHIFT,256CAPTURE,16,384UNLOAD. The native experiment has33,080 rising edges, including3paused and53other setup/handshake/exit/reset/restart overhead edges. Completion is200ps after its final falling edge. Payload time at50MHz is660.48us; the full bench duration is661.6002us. The power window separately spans610ns–661150.001ns, covering the complete payload plus the three pauses and excluding reset/restart. Threshold516cycles is an observed coverage prefix; the actual runs still execute all256patterns. The architecture uses non-overlapped unloading, so it does not claim an overlapped test-time improvement.

## 17. FPGA Implementation, Area Overhead and Power Estimation

### Comparable hardware and implementation boundary

Vivado's installed part database confirms `xc7a35tcpg236-1`. Native synthesis obtains the Artix-7 license; no paid-only device or IP is selected. Configurations share source versions, flattened/rebuilt out-of-context synthesis, default optimization/place/phys-opt/route settings and common clock/reset infrastructure. A instantiates original `core`; B instantiates `core_scan_test` with an external tester interface; C adds the runtime router, generator, controller and safe MISR. Functional instruction/data ports remain unconstrained runtime inputs so valid processor hardware is retained. Debug ports are open, and neither `core_scan_fault` nor testbench logic is included. No artificial KEEP/preservation bus is added.

The processor's parallel bus exceeds Basys3's106 available I/O pins. These are therefore **out-of-context placed-and-routed processor configurations**, with virtual ports and no IBUF/OBUF or board bitstream. Counts include the real core and common MMCM/reset infrastructure, but exclude external caches/ROM/RAM/I/O peripherals and physical package I/O loading. They are not whole-board utilization or power. The Basys3 device is the implementation target; a board is not required.

### Clock and interface constraints

One100MHz primary drives one MMCM (1GHzVCO) generating related50MHz processor phases. Relative to clk rising at0ns, phi1 is high15–20ns and phi2 high0–5ns; phi3 high5–10ns is unused by the core and may prune. Auto-derived generated clocks maintain the true phase relationship. No asynchronous grouping is applied between these clocks. The virtual external interface assumes2ns maximum and0.5ns minimum input/output delays relative to main clk; uncertainty is0.1ns. Reset assertion paths to asynchronous control pins are false-pathed, with synchronous two-cycle release. These are documented interface assumptions, not Basys board memory timing. Native clocks/check_timing/interaction reports expose remaining limitations; multiphase paths can have less than20ns available.

### Area and timing

{table(area,['Configuration','LUT','FF','Latches','BRAM','DSP','Stage'])}

![Area](FPGA_Analysis/figures/area_comparison.png)

{table(overhead,['Comparison','LUTDelta','LUTOverheadPercent','FFDelta','FFOverheadPercent','Stage'])}

Overhead=(configuration−reference)/reference×100, separately for LUT andFF. The B→C row is incremental LBIST overhead; A→B isolates scan/isolation overhead. Full resource counts include LUTRAM, carry, BRAM, DSP and clock primitives in `synthesis_summary.csv`; LUT/FF utilization uses20,800/41,600available. Primitive versus packed LUT counts can differ after physical optimization, so report_utilization is the area-table authority. There is no single meaningful FPGA utilization percentage across unlike resources.

Baseline maps two RAMB18 primitives (one36Kb equivalent); B/C map noBRAM and use moreFFs. Thus the large FF increase includes a storage-inference change in the existing isolation-helper implementation, not simply64scan muxes. Wide observation ports are open and no debug bus is retained, but source coding/inference side effects are not eliminated by a memory refactor. These are the actual existing-implementation costs. They should not be interpreted as a technology-independent or memory-inference-neutral scan overhead.

{table(timing,['Configuration','Stage','WNS_NS','TNS_NS','WHS_NS','SetupFailingEndpoints','FirstSetupPathDelayNS','TimingClosure'])}

All reported50MHz timing violations are retained. Successful synthesis, placement or routing does not imply timing closure. A maximum achievable frequency is not inferred from20ns minusWNS because the worst path may cross phase-related clocks. No board operation or maximum frequency is established. Working RTL is preserved rather than altered to repair timing for this submission.

### Switching capture and estimated power

The five LBIST approaches share **one implemented C netlist**. Each approach's exact production wrapper is simulated with its own real switching activity, fixed clock/pattern count/window and the same test environment. The router's unselected scheduling lanes use the same fixed production generics in every trace. A hierarchy-only SAIF mapping preserves all switching records and maps production instances to routed u_system. MMCM/clock activity derives from timing constraints. RTL SAIF does not include routed glitches or establish gate-level timing behavior.

Actual C annotation is1,963/14,106design nets (13.9161%) in each mode; Vivado reports Medium overall confidence. Remaining nets use propagation/default activity. Unknown-state warnings also occur on unused or uninitialized processor logic. The whole-C watt values below are therefore **assumption-dominated diagnostic estimates**, not a reliable whole-processor power-saving measurement. A andB have separate actual lwsw SAIF captures over100–1670ns; their partial mapping is21.5681% and13.9894%, respectively. Their dynamic estimates are0.187W and0.163W. Because storage inference and annotation differ, that difference is not evidence that adding scan lowers physical power. Vectorless initial reports remain separately labeled historical run artifacts.

{table(combined,['Approach','WTM','EstimatedDynamicW','CommonLUT','CommonFF','RoutedWNS'])}

{table(power,['Approach','TotalW','StaticW','DynamicW','ClockW','LogicW','SignalsW','BRAMW','DSPW','MMCMW']) if power else 'Per-mode native power analysis is not yet available; see execution status and raw reports.'}

![Estimated dynamic power with rounding resolution](FPGA_Analysis/figures/dynamic_power.png)

![WTM versus estimated power](FPGA_Analysis/figures/wtm_vs_power.png)

Error bars indicate only the0.001W report rounding (±0.0005W), not model confidence bounds. Separate static/dynamic/total values are independently rounded and may not sum exactly. The commonMMCM alone estimates0.106W, dwarfing the reported differences. No statistically or physically established power improvement is claimed from the0.001W mode differences.

As a limited fallback, the detailed reports retain the **same routed IF/RF hierarchy** across modes, including any synthesis-absorbed decode/comb logic. Direct reports0.002W; other per-mode rows are not printed at the native report's hierarchy resolution and are explicitly marked unavailable. Router/controller/MISR source-tag counts and unmatched nets are retained separately; they are not extrapolated into missing watt values. Reliable finer subsystem power ranking and reliable whole-processor activity analysis remain unresolved limitations, rather than fabricated results. `power/subsystem_comparison.csv` and `power/annotation_by_boundary.csv` preserve that boundary and availability.

WTM weights SHIFT transitions in64scanFFs. Vivado power includes clocks, processor logic, routing and other resources across SHIFT/CAPTURE/UNLOAD. WTM reduction therefore cannot be equated to total FPGA dynamic-power reduction. Power uses the selected part's default nominal supply assumptions and documented25°C ambient/typical process settings when accepted by Vivado. It is an **estimated on-chip power study**, not physical board measurement. Timing failure at the requested frequency further limits interpreting these estimates as an operable hardware point. `FPGA_Analysis/README.md` records exact mapping, confidence and run status.

All runs accept25°C ambient and typical process. Native supplies include1.0V Vccint/Vccbram and1.8V Vccaux. Generic Vivado thermal defaults (medium board/heatsink,250LFM airflow) are consistent across runs and are not a calibrated Basys3 thermal model. External memory, package I/O and regulator/board losses are excluded. Initial reporting-call failures were repaired using saved checkpoints; all final seven SAIF power exports and five detailed exports completed. The C synthesis log's obsolete CONFIGURATION generic warning is retained: actual elaboration binds DESIGN_CONFIG=2 and the post-route hierarchy check confirms the production router. The reproducible script uses the corrected generic name.

## 18. Discussion and limitations

The strongest result is reproducible control of scan switching with preserved capture ordering and safe completion handling on real cMIPS storage. The small fault universe saturates quickly and cannot distinguish coverage quality among the five approaches. It says little about random-pattern-resistant faults or broader datapath observability. The held instruction limits excitation, and only64of720pipeline candidate bits are scanned. Other architectural state remains protected, not tested. A reset is required after destructive testing. Target quantization and finite sequence effects make measured WTM differ from theoretical targets. FPGA overhead depends on this virtual processor boundary and synthesis settings; timing failure and partial activity annotation must accompany any area/power figures. No75% whole-processor coverage, measured energy savings, silicon measurement, post-route functional equivalence or successful board deployment is claimed.

## 19. Conclusion

The final submission preserves the verified Phase6A LBIST architecture and consolidates native evidence, reproducible essential demonstrations and an explicit FPGA evaluation boundary. The primary256-pattern original16-fault comparison achieves12detections per approach without observed final aliases, while measured scan WTM varies with filter/control choice. Safe MISR completion prevents aborted or incomplete streams from reporting MATCH. The available FPGA reports establish actual resource/timing/power estimates at their stated stages and limitations. Broader scan insertion, fault universes and physical measurement are deferred beyond this completed experimental scope.

## 20. References

1. T. Kato, S. Wang, Y. Sato, S. Kajihara and X. Wen, “A Flexible Scan-in Power Control Method in Logic BIST and Its Evaluation with TEG Chips,” IEEE Transactions on Emerging Topics in Computing,8(3),591–601,2020. [DOI10.1109/TETC.2017.2767070](https://doi.org/10.1109/TETC.2017.2767070); [author repository record](https://kyutech.repo.nii.ac.jp/records/6935). Paper results are distinct from this project's measurements.
2. R. A. Hexsel, cMIPS VHDL processor and documentation, supplied GPLv3 sources, `cMIPS/docs/cMIPS.pdf` and `cMIPS/vhdl/`.
3. Digilent, [Basys3 reference manual](https://digilent.com/reference/_media/basys3%3A%20basys3_rm.pdf) and [official master XDC](https://github.com/Digilent/digilent-xdc/blob/master/Basys-3-Master.xdc). Used for target/100MHz oscillator reference, not as an applied pinout in the virtual-I/O flow.
4. AMD Vivado2025.1.1 installed command help and native utilization/timing/power/switching reports under `FPGA_Analysis/`; `device_probe.log` records tool/part availability.
5. Repository experimental records, `Results/Phase1` (where present), `Results/Phase2`, `Results/Phase3`, `Results/Phase4`, `Results/Phase5A`, `Results/Phase5B`, `Results/Phase5C`, `Results/Phase6A`, and final read-only audits. Earlier result directories remain authoritative historical evidence.

## Reproduction and evidence index

See [README](README.md), [demo guide](DEMO.md), [final verification summary](final_verification_summary.md), [FPGA study](FPGA_Analysis/README.md), [primary comparison CSV](final_experimental_comparison.csv), and [source provenance](source_manifest.csv). Full per-fault tables are in `tables/`. Relevant actual waveform excerpts are [capture/unload](figures/scan_capture_unload.png) and [abort suppression](figures/misr_abort.svg); the latter is copied unchanged from its VCD-verified historical figure. Native WDB/VCD/SAIF/checkpoints are local regenerable artifacts rather than required Git payloads.
'''
    # Repair compact technical tokens for comfortable reading without changing identifiers.
    for a,b in [('16,384SHIFT','16,384 SHIFT'),('16,384UNLOAD','16,384 UNLOAD'),('256CAPTURE','256 CAPTURE'),
                ('64of720','64 of 720'),('No75%','No 75%'),('noBRAM','no BRAM'),('moreFFs','more FFs'),('64scan','64 scan'),
                ('one36Kb','one 36 Kb'),('commonMMCM','common MMCM')]:report=report.replace(a,b)
    # Add spacing between quantities and ordinary prose units/words. Identifiers
    # inside backticks, hashes, paths and signature literals are left untouched.
    for word in ['patterns','cycles','SHIFT','CAPTURE','UNLOAD','paused','other','edges','scanFFs','scan','initial','first','detections','pattern','fault','faults','eligible','available','design','rows','source','mode','original','processor','comparison','mm','ns','ps','us','ms','MHz','GHz','LUT','FF','W','V','C','LFM']:
        report=re.sub(r'(?<=\d)('+word+r')\b',r' \1',report)
    for word in ['executes','has','including','and','is','at','spans','Threshold','all','the','over','are','only','with','use','in','detects','every','same','after','of','to','No','contains','each','one','two','just','than','count','universe','target','beta','alpha','gamma','include','includes','estimates','measures','Swap','selected','logical']:
        report=re.sub(r'\b('+word+r')(?=\d)',r'\1 ',report)
    for a,b in [('andB','and B'),('andFF','and FF'),('1GHzVCO','1 GHz VCO'),("Basys3's106","Basys3's 106"),('Vccint/Vccbram','Vccint / Vccbram'),('board/heatsink,250','board/heatsink, 250')]:report=report.replace(a,b)
    (O/'Final_Report.md').write_text(report,encoding='utf-8')
    summary='# Final verification summary\n\n'+table(status,['Category','Passed','Total'])+'\n\nCounts above are read from actual result files. Archived campaign checks compare all 256 captures, every prefix signature, routing configuration, sequence counts, isolation evidence and measured activity against independent models. Fresh native case CSVs and logs are under Verification/Essential and Verification/Activity. The original intentional WAIT breakpoint assertion is accepted only with the exact PC, differential state and expected output sequence. Simulated time is bounded below 100 ms; the longest archived processor run is 661.6002 us.\n\nThe FPGA timing report is separate: a passing behavioral simulation does not establish timing closure. No historical result is overwritten.\n'
    (O/'final_verification_summary.md').write_text(summary,encoding='utf-8')
    (O/'final_synthesis_summary.md').write_text('# Final FPGA synthesis and implementation summary\n\n'+table(area,['Configuration','LUT','FF','Latches','BRAM','DSP','Stage'])+'\n\n'+table(timing,['Configuration','Stage','WNS_NS','TNS_NS','WHS_NS','TimingClosure'])+'\n\n'+table(overhead,['Comparison','LUTOverheadPercent','FFOverheadPercent','Stage'])+'\n\nActual native report_utilization counts; same Artix-7 part, virtual processor boundary, MMCM and constraints. No fault mux/debug hardware. See FPGA_Analysis/README.md for assumptions, execution status and power limitations.\n',encoding='utf-8')

if __name__=='__main__':main()
