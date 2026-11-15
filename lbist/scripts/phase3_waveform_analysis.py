"""Independent transition-level verification and event-focused real-data previews."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from fractions import Fraction
from phase3_trace import Trace
from phase3_wtm_optimizer import timing,period

ROOT=Path(__file__).resolve().parents[2]
APP_NAMES={0:'direct',1:'low',2:'basic',3:'swap',4:'moving'}

def check_trace(trace,prefix,app,length,beta,chains=4):
    required=['clk','rst','scan_enable','shift_count_v','pattern_index','moving_position_v',
              'alpha_0','beta_v','gamma_0','mode_select','mode_0','mode_1','mode_2','mode_3','pattern_done']
    assert all(trace.has(prefix,n) for n in required),f"Missing signal under {prefix}"
    pos=pat=advances=0
    initialized=False
    masks=[set() for _ in range(chains)]
    completed_masks=[]; complete_times=[]
    source_sequence=[]; state=0xAAAA
    for j in range(65535):
        source_sequence.append(state&1)
        feedback=sum((state>>k)&1 for k in [0,4,13,15])%2
        state=(state>>1)|(feedback<<15)
    assert state==0xAAAA
    integration=trace.has(prefix,'chain_flat')
    source_bits=[[] for _ in range(chains)]
    def number(name,t,pre=False):return trace.integer(prefix,name,t,pre)
    def expected_modes(p,s):
        if app==0:return [3]*chains
        if app==1:return [0]*chains
        modes=[]
        for c in range(chains):
            a,b,g=timing(APP_NAMES[app],length,beta,p,c)
            modes.append(3 if g<=s<g+b else 0)
        return modes
    rising=[t for t,v in trace.values(prefix,'clk') if v=='1']
    enabled=0
    for t in rising:
        reset=number('rst',t,True)
        enable=number('scan_enable',t,True)
        if reset:
            pos=pat=advances=0; initialized=True
            assert number('shift_count_v',t)==0 and number('pattern_index',t)==0
            assert number('pattern_done',t)==0
            if integration:assert number('chain_flat',t)==0
            continue
        if not initialized: continue
        assert number('shift_count_v',t,True)==pos and number('pattern_index',t,True)==pat,(prefix,t,'pre counters')
        modes=expected_modes(pat,pos)
        for c,m in enumerate(modes):
            assert number(f'mode_{c}',t,True)==m,(prefix,t,'pre-edge mode',c)
        assert number('mode_select',t,True)==sum(m<<(2*c) for c,m in enumerate(modes))
        if integration:
            assert number('active_mode',t,True)==number('mode_select',t,True),(prefix,t,'active filter modes')
            assert number('mode_valid',t,True)==(1<<chains)-1,(prefix,t,'valid filter modes')
            old_chain=number('chain_flat',t,True)
            old_state=number('state',t,True)
            expected_scan=0
            for c in range(chains):
                src=[source_sequence[(advances+c*257+k)%65535] for k in range(3)]
                assert ((number('current_bits',t,True)>>c)&1)==src[0]
                assert ((number('future1_bits',t,True)>>c)&1)==src[1]
                assert ((number('future2_bits',t,True)>>c)&1)==src[2]
                past=(old_chain>>(c*length))&1
                assert ((number('past_bits',t,True)>>c)&1)==past
                value=src[0] if modes[c]==3 or src[0]==src[1]==src[2] else past
                expected_scan |= value<<c
                if enable:source_bits[c].append(src[0])
            assert number('scan_in',t,True)==expected_scan,(prefix,t,'scan input')
        old_pos=pos
        if enable:
            enabled+=1
            for c,m in enumerate(modes):
                if m==3:masks[c].add(length-1-pos)
            advances+=1
            pos+=1
            if pos==length:
                pos=0;pat+=1
                completed_masks.append([set(x) for x in masks]);complete_times.append(t)
                masks=[set() for _ in range(chains)]
        assert number('shift_count_v',t)==pos and number('pattern_index',t)==pat,(prefix,t,'post counters')
        assert number('pattern_done',t)==int(bool(enable and old_pos==length-1)),(prefix,t,'done boundary')
        post_modes=expected_modes(pat,pos)
        for c,m in enumerate(post_modes):assert number(f'mode_{c}',t)==m,(prefix,t,'post-edge mode',c)
        if app>=2:
            expected_regions=[timing(APP_NAMES[app],length,beta,pat,c) for c in range(chains)]
            assert number('alpha_debug',t)==sum(v[0]<<(16*c) for c,v in enumerate(expected_regions))
            assert number('gamma_debug',t)==sum(v[2]<<(16*c) for c,v in enumerate(expected_regions))
            a,b,g=expected_regions[0]
            assert number('alpha_0',t)==a and number('gamma_0',t)==g and number('beta_v',t)==b
        if app==4:assert number('moving_position_v',t)==pat%period('moving',length,beta)
        if integration:
            if enable:
                expected_chain=0
                mask=(1<<length)-1
                for c in range(chains):
                    word=(old_chain>>(c*length))&mask
                    expected_chain|=(((word<<1)&mask)|((expected_scan>>c)&1))<<(c*length)
                feedback=sum((old_state>>k)&1 for k in [0,4,13,15])%2
                assert number('state',t)==((old_state>>1)|(feedback<<15))
            else:expected_chain=old_chain;assert number('state',t)==old_state
            assert number('chain_flat',t)==expected_chain,(prefix,t,'every scan bit')
    assert completed_masks,'No complete patterns in portable trace'
    if integration:
        for a in range(chains):
            for b in range(a):
                assert source_bits[a]!=source_bits[b],'Chains were driven by identical captured source streams'
    if app==4 and beta>0:
        assert len(completed_masks)>=period('moving',length,beta),'VCD misses a complete movement cycle'
        reached=set.union(*(row[0] for row in completed_masks))
        assert reached==set(range(14,length-14)), 'Incorrect reachable physical positions'
    if app==3 and beta>0:
        assert len(completed_masks)>=2
        assert completed_masks[0][0]!=completed_masks[1][0]
        assert completed_masks[0][0]!=completed_masks[0][1]
        assert completed_masks[0][0]==completed_masks[1][1]
    events={}
    def transitions(name,old=None,new=None):
        found=[]
        for t,v in trace.values(prefix,name):
            if t==0:continue
            before=trace.value(prefix,name,t,True);after=trace.value(prefix,name,t)
            if not set(before+after)<={'0','1'}:continue
            a,b=int(before,2),int(after,2)
            if a!=b and (old is None or a==old) and (new is None or b==new):found.append(t)
        return found
    first=transitions('mode_0',0,3); second=transitions('mode_0',3,0)
    if first: events['first_switch']=first[0]
    if second: events['second_switch']=second[0]
    events['pattern_wrap']=complete_times[0]
    deassert=transitions('scan_enable',1,0)
    if deassert:
        events['pause_begin']=deassert[0]
        restored=[t for t in transitions('scan_enable',0,1) if t>deassert[0]]
        assert restored,'Pause has no resume';events['pause_end']=restored[0]
    if app==3:
        events['swap_flipped']=complete_times[0]
    if app==4:
        changes=transitions('moving_position_v')
        events['moving_advanced']=changes[0]
        wraps=transitions('moving_position_v',period('moving',length,beta)-1,0)
        assert wraps or period('moving',length,beta)==1
        if wraps:events['moving_wrapped']=wraps[0]
    # Every mode boundary must be a real clock edge. An annotation marks the
    # post-edge mode update, NOT a claim the same edge sampled the new mode.
    for key in ['first_switch','second_switch','pattern_wrap','swap_flipped','moving_advanced','moving_wrapped']:
        if key in events:assert events[key] in rising
    return dict(Prefix=prefix,Approach=APP_NAMES[app],EnabledShifts=enabled,CompletePatterns=len(completed_masks),
                Events=events,Masks=completed_masks,CompleteTimes=complete_times,
                Check='PASS',ChainLength=length,NumChains=chains,SourceVCD=trace.path.relative_to(ROOT).as_posix())

def verify_preview(trace,prefix,path):
    """Read the saved SVG intervals back and compare each with the source VCD."""
    import re
    import xml.etree.ElementTree as ET
    from bisect import bisect_right
    pattern=re.compile(r"^(.+)/([^/ ]+) = ([01xuzwhl-]+), ([0-9.]+)\.\.([0-9.]+) ns$",re.I)
    count=0; first=trace.end; last=0
    for element in ET.parse(path).getroot().iter():
        if element.tag.rsplit('}',1)[-1]!='title':continue
        match=pattern.fullmatch(element.text or '')
        assert match,'Unexpected waveform interval metadata'
        hierarchy,name,value,start,end=match.groups()
        assert hierarchy==prefix,(path,'wrong signal hierarchy')
        start=int(Fraction(start)*1000);end=int(Fraction(end)*1000)
        assert 0<=start<end<=trace.end,(path,'preview interval outside capture')
        width=trace.signals[prefix+'/'+name][1]
        value=value.lower()
        normalized=value.zfill(width) if set(value)<={'0','1'} else value if len(value)==width else value[0]*width
        assert trace.value(prefix,name,start)==normalized,(path,name,start,'saved preview value differs from VCD')
        code=trace.signals[prefix+'/'+name][0]
        following=bisect_right(trace.times[code],start)
        assert following==len(trace.times[code]) or trace.times[code][following]>=end,(path,name,'preview spans a real transition')
        count+=1;first=min(first,start);last=max(last,end)
    assert count>0,(path,'no source intervals in saved preview')
    return dict(File=Path(path).relative_to(ROOT).as_posix() if Path(path).is_relative_to(ROOT) else str(path),
                SourceVCD=trace.path.relative_to(ROOT).as_posix(),Prefix=prefix,IntervalsChecked=count,
                FirstTimePS=first,LastTimePS=last,Result='PASS')

def make_images(trace,info,folder,stem):
    from render_waveform_previews import render_window
    events=info['Events'];prefix=info['Prefix']
    control=['clk','rst','scan_enable','shift_count_v','pattern_index','mode_0','pattern_done','alpha_0','beta_v','gamma_0']
    if info['Approach']=='moving':control.insert(5,'moving_position_v')
    if info['Approach']=='swap':control[6:6]=['mode_1','mode_2','mode_3']
    source=['state','current_bits','future1_bits','future2_bits','active_mode','mode_valid','scan_in','past_bits','chain_flat']
    end=min(trace.end,info['CompleteTimes'][0]+12000)
    annotations=[(events[k],k.replace('_',' ')) for k in ['first_switch','second_switch'] if k in events][:2]
    render_window(trace,prefix,control,0,end,folder/(stem+'_overview.svg'),stem+' - complete pattern overview',annotations)
    if trace.has(prefix,'chain_flat'):
        render_window(trace,prefix,control+source,0,end,folder/(stem+'_integration.svg'),
                      stem+' - controller, source and scan-register feedback',annotations)
    for key in ['first_switch','second_switch','pattern_wrap']:
        if key not in events:continue
        t=events[key]
        markers=[(t,key.replace('_',' ')+' (post-edge)')]
        if key=='pattern_wrap':
            if 'swap_flipped' in events:markers.append((events['swap_flipped'],'Swap configuration flipped'))
            if 'moving_advanced' in events:markers.append((events['moving_advanced'],'Moving region advanced'))
        render_window(trace,prefix,control,max(0,t-10000),min(trace.end,t+10000),
                      folder/(stem+'_'+key+'.svg'),stem+' - '+key.replace('_',' '),markers)
    if 'pause_begin' in events:
        a,b=events['pause_begin'],events['pause_end']
        render_window(trace,prefix,control,max(0,a-8000),min(trace.end,b+8000),
                      folder/(stem+'_pause_resume.svg'),stem+' - actual scan pause/resume',[(a,'scan enable deasserted'),(b,'scan enable restored')])
    end=min(trace.end,info['CompleteTimes'][min(1,len(info['CompleteTimes'])-1)]+8000)
    render_window(trace,prefix,control,0,end,folder/(stem+'_consecutive_patterns.svg'),stem+' - consecutive patterns')
    if info['Approach']=='swap':
        render_window(trace,prefix,['clk','shift_count_v','pattern_index','mode_0','mode_1','mode_2','mode_3','pattern_done'],
                      0,end,folder/(stem+'_per_chain.svg'),stem+' - actual per-chain Swap variation')
    if 'moving_wrapped' in events:
        t=events['moving_wrapped']
        render_window(trace,prefix,control,max(0,t-10000),min(trace.end,t+10000),
                      folder/(stem+'_moving_wrap.svg'),stem+' - movement-range wrap',[(t,'moving region wrapped')])
    # A physical-position map comes only from observed pre-edge mode samples.
    if info['Approach'] in {'swap','moving'}:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        rows=info['Masks'][:min(24,len(info['Masks']))]
        length=info['ChainLength']
        if info['Approach']=='swap':
            # Source length is provided by mirror counter range via the full loaded masks.
            data=np.array([[int(k in row[c]) for k in range(length)] for row in rows[:2] for c in range(info['NumChains'])])
            labels=[f'pattern {p}, chain {c}' for p in range(2) for c in range(info['NumChains'])]
        else:
            data=np.array([[int(k in row[0]) for k in range(length)] for row in rows])
            labels=[str(p) for p in range(len(rows))]
        fig,ax=plt.subplots(figsize=(12,5))
        ax.imshow(data,aspect='auto',origin='upper',vmin=0,vmax=1,cmap='Blues',interpolation='nearest')
        ax.set(xlabel='Physical scan FF index (0 = scan input)',ylabel='Observed pattern / chain',title=stem+' - observed n=1 placement (blue)')
        ax.set_yticks(range(len(labels)));ax.set_yticklabels(labels,fontsize=8)
        fig.tight_layout()
        fig.savefig(folder/(stem+('_variation.svg' if info['Approach']=='swap' else '_progression.svg')))
        plt.close(fig)

def analyze_all(render=False):
    plan=json.loads((ROOT/'Results/Phase3/Comparison/work/experiment_plan.json').read_text())
    captures=[v for v in plan if v['Capture']]
    summaries=[];event_rows=[];preview_sources=[];preview_checks=[]
    for case in captures:
        folder=ROOT/'Results/Phase3'/case['Group']/'waveforms'
        import xml.etree.ElementTree as ET
        log=(folder/(case['Case']+'.log')).read_text()
        assert '[TB_COMPLETE] '+case['Top'] in log and '[FAIL]' not in log and 'Failure:' not in log
        layout=ET.parse(folder/(case['Case']+'.wcfg'))
        assert layout.find('.//db_ref').get('path')==case['Case']+'.wdb'
        assert (folder/(case['Case']+'.wdb')).stat().st_size>0
        trace=Trace(folder/(case['Case']+'.vcd'))
        specs=([(2,'basic_engine',case['Generics']['BASIC_BETA']),(3,'swap_engine',case['Generics']['SWAP_BETA']),(4,'moving_engine',case['Generics']['MOVING_BETA']),
                (0,'direct_engine',0),(1,'low_engine',0)] if case['Top']=='tb_phase3_comparison' else
               [(3 if case['Group']=='Swap' else 4,'engine',case['Beta'])])
        reports=[]
        for app,engine,beta in specs:
            prefix='/'+case['Top']+'/'+engine
            report=check_trace(trace,prefix,app,case['Length'],beta)
            reports.append(report)
            for label,t in report['Events'].items():
                def val(name,pre=False):return trace.integer(prefix,name,t,pre)
                event_rows.append(dict(Case=case['Case'],Prefix=prefix,Event=label,TimePS=t,
                                       PreCount=val('shift_count_v',True),PostCount=val('shift_count_v'),
                                       PreMode=format(val('mode_0',True),'02b'),PostMode=format(val('mode_0'),'02b'),
                                       PrePattern=val('pattern_index',True),PostPattern=val('pattern_index'),Result='PASS'))
            if render and not case['Top'].endswith('_controller') and app>=2:
                target_folder=ROOT/'Results/Phase3/Basic/waveforms' if app==2 else folder
                stem=APP_NAMES[app]+f'_beta{beta}'
                # Preserve primary beta16 images; comparison uses distinct stems for other schedules.
                if case['Top']=='tb_phase3_comparison' and app!=2:stem='comparison_'+stem
                make_images(trace,report,target_folder,stem)
                preview_sources.append(dict(Case=case['Case'],Stem=stem,Folder=target_folder.relative_to(ROOT).as_posix(),
                                            SourceVCD=trace.path.relative_to(ROOT).as_posix(),Prefix=prefix,
                                            SHA256=hashlib.sha256(trace.path.read_bytes()).hexdigest(),AvailableEndPS=trace.end))
        if render:
            from render_waveform_previews import render_window
            report=reports[0]
            names=['clk','rst','scan_enable','shift_count_v','pattern_index','moving_position_v','mode_0','mode_1','mode_2','mode_3','pattern_done','alpha_0','beta_v','gamma_0']
            render_window(trace,report['Prefix'],names,0,min(trace.end,report['CompleteTimes'][0]+12000),
                          folder/(case['Case']+'.svg'),case['Case']+' - '+report['Approach']+' overview')
        preview_checks.append(verify_preview(trace,reports[0]['Prefix'],folder/(case['Case']+'.svg')))
        summaries.append(dict(Case=case['Case'],Group=case['Group'],Testbench=case['Top'],
                              BehavioralResult='PASS',VCDSignals=len(trace.signals),VCDDurationNS=trace.end/1000,
                              CheckedPrefixes=len(reports),WDBExists=trace.path.with_suffix('.wdb').exists(),
                              WCFGExists=trace.path.with_suffix('.wcfg').exists()))
        print('VCD TEMPORAL CHECK: PASS --',case['Case'])
    out=ROOT/'Results/Phase3/Comparison/reports'
    def write(name,rows):
        with (out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('phase3_waveform_summary.csv',summaries)
    write('phase3_waveform_events.csv',event_rows)
    if not render:
        with (out/'phase3_preview_sources.csv').open() as f:
            preview_sources=list(csv.DictReader(f))
    cached={}
    for source in preview_sources:
        path=ROOT/source['SourceVCD']
        if path not in cached:cached[path]=Trace(path)
        trace=cached[path]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['SHA256'],'Preview source hash changed; rerender from current VCD'
        for preview in sorted((ROOT/source['Folder']).glob(source['Stem']+'_*.svg')):
            # These two-dimensional placement maps come from the already checked masks.
            if preview.stem.endswith(('_variation','_progression')):continue
            preview_checks.append(verify_preview(trace,source['Prefix'],preview))
    assert len(preview_checks)>=35,'Missing focused waveform previews'
    write('phase3_preview_validation.csv',preview_checks)
    if render:
        write('phase3_preview_sources.csv',preview_sources)
        # Report figures reuse these exact, independently checked VCD-derived views.
        import shutil
        figures=ROOT/'Results/Phase3/Comparison/figures'
        figures.mkdir(parents=True,exist_ok=True)
        for source,destination in [
            ('Swap/waveforms/swap_beta16_first_switch.svg','representative_mode_switch.svg'),
            ('Moving/waveforms/moving_beta16_progression.svg','moving_control_progression.svg')]:
            shutil.copyfile(ROOT/'Results/Phase3'/source,figures/destination)
    print('Verified',len(summaries),'captured testbenches,',len(event_rows),'actual event timestamps and',len(preview_checks),'saved waveform SVGs.')
    return summaries

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--verify-only',action='store_true')
    args=p.parse_args();analyze_all(args.render)
