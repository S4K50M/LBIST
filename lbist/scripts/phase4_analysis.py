"""Phase 4 real-log metrics and independently checked captured transitions."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from fractions import Fraction
from phase3_trace import Trace
from render_waveform_previews import render_window
from phase3_waveform_analysis import verify_preview
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Results/Phase4'
def write(name,rows):
    target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['Result']);w.writeheader();w.writerows(rows)
def check_storage(trace,top,plpf=False):
    prefix='/'+top
    read=lambda name,t,pre=False:trace.integer(prefix,name,t,pre)
    rises=[t for t,v in trace.values(prefix,'clk') if v=='1']
    reset_times=[t for t,v in trace.values(prefix,'rst') if v=='0']
    initialized=False;j=shifts=captures=0
    state=0xAAAA
    for t in sorted(set(rises+reset_times)):
        if read('rst',t)==0:
            assert read('q',t)==0 and read('scan_out',t)==0 and read('scan_feedback',t)==0
            initialized=True;j=0;state=0xAAAA
            continue
        if not initialized:continue
        old=read('q',t,True);enable=read('scan_enable',t,True)
        assert read('scan_out',t,True)==old>>63
        assert read('scan_feedback',t,True)==old&1
        if plpf:
            assert read('state',t,True)==state and read('shift_count_v',t,True)==j%64
            mode=3 if 22<=j%64<42 else 0
            assert read('mode_select',t,True)==mode
            bits=[(state>>k)&1 for k in range(3)]
            for name,bit in zip(['c','f1','f2'],bits):assert read(name,t,True)==bit
            expected_bit=bits[0] if mode==3 or bits[0]==bits[1]==bits[2] else old&1
            assert read('scan_in',t,True)==expected_bit
        if enable:
            expected=((old<<1)|read('scan_in',t,True))&((1<<64)-1)
            shifts+=1
            if plpf:
                feedback=sum((state>>k)&1 for k in [0,4,13,15])%2
                state=(state>>1)|(feedback<<15);j+=1
        elif read('ld',t,True)==0:
            expected=(read('pc_d',t,True)<<32)|read('instr',t,True);captures+=1
        else:expected=old
        assert read('q',t)==expected,(top,t,'storage ordering/capture/hold')
        assert read('scan_out',t)==expected>>63 and read('scan_feedback',t)==expected&1
        if plpf:
            assert read('state',t)==state and read('shift_count_v',t)==j%64
            assert read('pattern_done',t)==int(bool(enable and j%64==0))
            assert read('mode_select',t)==(3 if 22<=j%64<42 else 0)
    legal=set(rises+reset_times)
    # Every actual storage change must occur at an enabled clock or async reset.
    for t,value in trace.values(prefix,'q'):
        if t and t not in legal:raise AssertionError((top,t,'unexpected off-edge state update'))
    assert shifts>=256*64 and captures>0
    return dict(Testbench=top,EnabledScanShifts=shifts,FunctionalLoads=captures,Result='PASS')

def core_trace(trace):
    prefix='/tb_core_scan_regression'
    mapping={'i_addr':'scan_i_addr','d_addr':'scan_d_addr','wr':'scan_wr','cpu_i_aVal':'scan_i_aval',
             'cpu_d_aVal':'scan_d_aval','cpu_data':'scan_data','cpu_xfer':'scan_xfer','busFree':'scan_busfree'}
    times={t for t,v in trace.values(prefix,'clk') if v=='1'}
    known=0
    for t in sorted(times):
        if trace.value(prefix,'cpu_reset',t)!='1':continue
        # Compare stable pre-edge values; unknown unreset legacy data is preserved.
        for original,scan in mapping.items():
            assert trace.value(prefix,original,t,True)==trace.value(prefix,scan,t,True),(original,t)
        for name in ['RF_PCincd','RF_instruction','IF_RF_ld','EX_A','EX_B','WB_C','WB_wreg','MM_wrmem','PC']:
            a=trace.value(prefix+'/U_CORE',name,t,True)
            b=trace.value(prefix+'/U_SCAN',name,t,True)
            assert a==b,(name,t)
        q=(trace.integer(prefix+'/U_SCAN','RF_PCincd',t,True)<<32)|trace.integer(prefix+'/U_SCAN','RF_instruction',t,True)
        assert trace.integer(prefix,'scan_out',t,True)==q>>63
        assert trace.integer(prefix,'scan_feedback',t,True)==q&1
        assert trace.integer(prefix,'scan_enable',t,True)==0
        known+=1
    assert known>=50
    return dict(Testbench='tb_core_scan_regression',EnabledScanShifts=0,FunctionalLoads=known,Result='PASS')

def waves():
    validations=[];previews=[];sources=[];events=[]
    configs=[('IF_RF','scan_unit_seed12345','tb_reg_IF_RF_scan'),
             ('PLPF_Integration','real_plpf_B20_P1024','tb_if_rf_plpf_integration'),
             ('Core_Integration','core_scan_lwsw','tb_core_scan_regression')]
    for group,tag,top in configs:
        folder=OUT/group/'waveforms';path=folder/(tag+'.vcd')
        trace=Trace(path);prefix='/'+top
        if top=='tb_core_scan_regression':
            validations.append(core_trace(trace))
            names=['clk','cpu_reset','scan_enable','i_addr','scan_i_addr','d_addr','scan_d_addr','wr','scan_wr','cpu_data','scan_data','equivalent','scan_in','scan_out','scan_feedback']
            render_window(trace,prefix,names,0,trace.end,folder/(tag+'_overview.svg'),'cMIPS scan-disabled differential execution')
            previews.append(verify_preview(trace,prefix,folder/(tag+'_overview.svg')))
            # Also expose the actual IF/RF pipeline storage, separately from external ports.
            for inst in ['U_CORE','U_SCAN']:
                image=folder/(tag+'_'+inst.lower()+'_pipeline.svg')
                render_window(trace,prefix+'/'+inst,['PC','IF_RF_ld','RF_PCincd','RF_instruction','WB_C','WB_wreg','MM_wrmem'],0,trace.end,image,inst+' - actual pipeline and write controls')
                previews.append(verify_preview(trace,prefix+'/'+inst,image))
        else:
            plpf=group=='PLPF_Integration'
            validations.append(check_storage(trace,top,plpf))
            names=['clk','rst','ld','scan_enable','scan_in','scan_out','scan_feedback','pc_d','instr','q']
            if plpf:names+=['shift_count_v','state','c','f1','f2','mode_select','active_mode','pattern_done']
            event_map=({1:'scan_loading',2:'pause',3:'resume',4:'functional_capture',5:'captured_unload'} if plpf else
                       {1:'asynchronous_reset',2:'functional_load',3:'functional_hold',4:'enter_scan',6:'serial_shift_and_scan_out',9:'functional_capture',10:'captured_unload',12:'reset_during_scan'})
            marks=[]
            for t,value in trace.values(prefix,'event_id'):
                code=int(value,2)
                if code in event_map:
                    label=event_map[code]
                    rising=[at for at,v in trace.values(prefix,'clk') if v=='1' and at>=t]
                    if label in {'functional_capture','functional_load','functional_hold','captured_unload','serial_shift_and_scan_out'}:
                        # Annotate the actual edge, rather than the stimulus setup marker.
                        t=next(at for at in rising if trace.integer(prefix,'rst',at,True)==1)
                    if label in {'asynchronous_reset','reset_during_scan'}:
                        drops=[at for at,v in trace.values(prefix,'rst') if v=='0']
                        t=drops[0] if label=='asynchronous_reset' else next(at for at in drops if at>=t)
                    marks.append((t,label))
            if not plpf:
                start=next(t for t,label in marks if label=='serial_shift_and_scan_out')
                edge=next(at for at,v in trace.values(prefix,'scan_out') if at>start)
                marks.append((edge,'scan_out'))
            if plpf:
                feedback=next(at for at,v in trace.values(prefix,'scan_feedback') if at>1000 and v=='1')
                marks.append((feedback,'real_ff_feedback'))
                for before,after,label in [(0,3,'first_mode_switch'),(3,0,'second_mode_switch')]:
                    found=[t for t,v in trace.values(prefix,'mode_select') if t and trace.integer(prefix,'mode_select',t,True)==before and trace.integer(prefix,'mode_select',t)==after]
                    assert found;marks.append((found[0],label))
                done=[t for t,v in trace.values(prefix,'pattern_done') if v=='1'];assert done;marks.append((done[0],'pattern_completion'))
            for t,label in marks:
                image=folder/(tag+'_'+label+'.svg')
                start=max(0,t-10000);end=min(trace.end,t+12000)
                render_window(trace,prefix,names,start,end,image,tag+' - '+label.replace('_',' '),[(t,label.replace('_',' ')+' (actual event)')])
                previews.append(verify_preview(trace,prefix,image))
                events.append(dict(Case=tag,Event=label,TimePS=t,Result='PASS'))
            overview_end=min(trace.end,1000000 if not plpf else 145000)
            image=folder/(tag+'_overview.svg')
            render_window(trace,prefix,names,0,overview_end,image,tag+' - captured overview')
            previews.append(verify_preview(trace,prefix,image))
        sources.append(dict(Case=tag,Source=path.relative_to(ROOT).as_posix(),SHA256=hashlib.sha256(path.read_bytes()).hexdigest(),EndPS=trace.end))
    write('phase4_waveform_validation.csv',validations)
    write('phase4_preview_validation.csv',previews)
    write('phase4_waveform_sources.csv',sources)
    write('phase4_waveform_events.csv',events)
    print('Phase 4 captured behavior and',len(previews),'saved SVGs: PASS')

def collect(require_all=False):
    statuses=[];metrics=[]
    for group in ['IF_RF','PLPF_Integration','Core_Integration']:
        for p in sorted((OUT/group/'reports').glob('*.csv')):
            if p.name.endswith('_samples.csv'):continue
            row=next(csv.DictReader(p.open()))
            if 'Testbench' not in row or 'ExpectedNegative' not in row:continue
            statuses.append(row)
            if row['Result']=='PASS':
                assert 0<=int(row['CompletionTime'].split()[0])<100_000_000_000,'simulation exceeded 100 ms'
            if row['Result']!='PASS' or row['ExpectedNegative']=='1':continue
            log=(OUT/group/'logs'/(row['Case']+'.log')).read_text()
            for match in re.finditer(r'\[SCAN_METRIC\] PLPF,([^\r\n]+)',log):
                patterns,shifts,serial,weighted,ff,expected,measured=match.group(1).split(',')
                patterns,shifts,serial,weighted,ff=map(int,[patterns,shifts,serial,weighted,ff])
                actual=weighted/(patterns*2080);reported_expected=float(expected)
                beta=int(re.search(r'_B([0-9]+)_',row['Case']).group(1))
                expected=float(Fraction(1,14)+Fraction(beta,64)*(Fraction(1,2)-Fraction(1,14)))
                assert abs(reported_expected-expected)<1e-6
                assert actual==float(measured) or abs(actual-float(measured))<1e-6
                assert abs(actual-expected)<.02 and shifts==patterns*64
                metrics.append(dict(Case=row['Case'],ChainWidth=64,NumChains=1,Beta=beta,Patterns=patterns,EnabledShifts=shifts,ExpectedWTM=expected,MeasuredWTM=actual,
                                    ErrorPP=abs(actual-expected)*100,SerialToggleRate=serial/(shifts-1),FFSwitchingFraction=ff/(shifts*64),
                                    SerialTransitions=serial,WeightedTransitions=weighted,FFChanges=ff,CaptureUnload='PASS',Result='PASS'))
    planned=[
        ('IF_RF','scan_unit_seed12345','tb_reg_IF_RF_scan',0),
        ('IF_RF','scan_unit_seed67890','tb_reg_IF_RF_scan',0),
        ('IF_RF','scan_unit_invalid_patterns','tb_reg_IF_RF_scan',1),
        *[('PLPF_Integration',case,'tb_if_rf_plpf_integration',int('invalid' in case)) for case in
          ['real_plpf_B20_P1024','real_plpf_B0_P256','real_plpf_B16_P256','real_plpf_B36_P256','real_plpf_invalid_beta']],
        ('Core_Integration','core_scan_lwsw','tb_core_scan_regression',0),
        ('Core_Integration','core_scan_stalls','tb_core_scan_regression',0),
        *[('Core_Integration','regression_'+top,top,0) for top in
          ['tb_lfsr_16','tb_phase_shifter','tb_plpf_optimized','tb_plpf_dynamic','tb_phase2_integration',
           'tb_basic_controller','tb_basic_integration','tb_swap_controller','tb_moving_controller','tb_swap_integration','tb_moving_integration']],
        ('Core_Integration','baseline_lwsw','tb_cMIPS',0)]
    present={r['Case'] for r in statuses}
    for group,case,top,negative in planned:
        if case not in present:
            statuses.append(dict(Case=case,Testbench=top,Group=group,ExpectedNegative=str(negative),Result='NOT_RUN',CompletionTime='NA',Capture='0',WDBBytes='0'))
    core_rows=[]
    for row in statuses:
        if row['Case'] not in ['core_scan_lwsw','core_scan_stalls','baseline_lwsw'] or row['Result']!='PASS':continue
        text=(OUT/'Core_Integration/logs'/(row['Case']+'.log')).read_text()
        reference=(ROOT/'Results/Baseline/simulate.log').read_text()
        outputs=lambda value:re.findall(r'(?im)^([0-9a-f]{8})\s*$',value)
        assert outputs(text)==outputs(reference)==[format(v&0xffffffff,'08x') for v in range(-10,0)],'lwsw output mismatch'
        assert 'cMIPS BREAKPOINT at PC=00000038' in text
        duration_ns=int(row['CompletionTime'].split()[0])//1000
        if row['Case']!='core_scan_stalls':assert duration_ns==1670
        assert 1<=text.count('Failure:')<=2 and '[FAIL]' not in text and 'SIMULATION ABORTED' not in text
        samples=[]
        if row['Case'].startswith('core_scan_'):
            samples=list(csv.DictReader((OUT/'Core_Integration/reports'/(row['Case']+'_samples.csv')).open()))
            assert len(samples)>=100 and all(v['Result']=='PASS' for v in samples)
            if row['Case']=='core_scan_stalls':assert any(v['IF_RF_ld']=='1' for v in samples)
        core_rows.append(dict(Case=row['Case'],Result='PASS',CompletionNS=duration_ns,ScanEnabled=False,PipelineSamples=len(samples),
                              StallSamples=sum(v['IF_RF_ld']=='1' for v in samples),OutputWords=len(outputs(text)),
                              BaselineOutputMatch='PASS',ExitPC='00000038',FunctionalEquivalence='PASS' if samples else 'baseline reproduced',
                              ProcessorScanIsolation='INCOMPLETE; scan-disabled functional test only'))
    write('phase4_core_regression.csv',core_rows)
    for row in statuses:
        primary=row['Group'] in ['IF_RF','PLPF_Integration'] or row['Testbench']=='tb_core_scan_regression'
        row.update(ScanWidth=64 if primary else 'NA',EnabledScanShifts='NA',MainPatterns='NA',
                   ScanEnableBehavior='NOT_RUN' if row['Result']=='NOT_RUN' else 'configuration rejection' if row['ExpectedNegative']=='1' else 'prior-phase regression',
                   FunctionalEquivalence='NA',CaptureUnload='NA')
        if row['Result']!='PASS' or row['ExpectedNegative']=='1':continue
        text=(OUT/row['Group']/'logs'/(row['Case']+'.log')).read_text()
        if row['Group']=='IF_RF':
            match=re.search(r'\[SCAN_METRIC\] UNIT,([0-9]+),([0-9]+)',text);assert match
            row.update(MainPatterns=int(match[1]),EnabledScanShifts=int(match[2]),ScanEnableBehavior='scan overrides load; pause with ld=1',
                       FunctionalEquivalence='PASS: original register compared',CaptureUnload='PASS')
        elif row['Group']=='PLPF_Integration':
            metric=next(m for m in metrics if m['Case']==row['Case'])
            row.update(MainPatterns=metric['Patterns'],EnabledScanShifts=metric['EnabledShifts']+64,ScanEnableBehavior='common enabled edge; capture does not advance generators',
                       FunctionalEquivalence='PASS: independent 64-bit reference',CaptureUnload='PASS')
        elif row['Testbench']=='tb_core_scan_regression':
            row.update(EnabledScanShifts=0,ScanEnableBehavior='disabled throughout processor test',FunctionalEquivalence='PASS: original core compared',
                       CaptureUnload='NOT_TESTED at processor level')
    write('phase4_verification_summary.csv',statuses)
    write('phase4_scan_metrics.csv',metrics)
    if require_all:
        assert len(statuses)==22,(len(statuses),'expected 8 scan/PLPF + 2 core + 12 prior regressions')
        assert all(r['Result']=='PASS' for r in statuses)
        assert len(metrics)==4
    print('Collected',sum(r['Result']=='PASS' for r in statuses),'PASS /',len(statuses),'planned cases;',len(metrics),'measured scan configurations.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--waves',action='store_true');p.add_argument('--require-all',action='store_true')
    args=p.parse_args();collect(args.require_all)
    if args.waves:waves()
