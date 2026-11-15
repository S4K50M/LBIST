"""Aggregate only executed, self-checked XSim logs into reproducible Phase 3 reports."""
import argparse
import csv
import hashlib
import json
import re
from fractions import Fraction as F
from pathlib import Path
from phase3_wtm_optimizer import describe,timing,regional_wtm
ROOT=Path(__file__).resolve().parents[2]
APPS={0:'direct',1:'low',2:'basic',3:'swap',4:'moving'}

def write_csv(path,rows,columns=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        columns=columns or (list(rows[0]) if rows else ['Result'])
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def collect(require_all=False,figures=True):
    plan=json.loads((ROOT/'Results/Phase3/Comparison/work/experiment_plan.json').read_text())
    simulations=[];metrics=[];diversity=[];exposures=[];waves=[];schedules=[]
    for case in plan:
        group=ROOT/'Results/Phase3'/case['Group']; file=group/'reports/cases'/(case['Case']+'.csv')
        record=dict(Case=case['Case'],Group=case['Group'],Testbench=case['Top'],
                    Regression=case.get('Regression',False),ExpectedNegative=case['Negative'],
                    Result='NOT RUN',CompletionTime='NA')
        if not file.exists():
            simulations.append(record)
            continue
        with file.open() as f: status=next(csv.DictReader(f))
        record.update(Result=status['Result'],CompletionTime=status['CompletionTime'])
        log=(group/'logs'/(case['Case']+'.log')).read_text()
        if status['Result']=='PASS':
            if case['Negative']:
                assert '[CONFIG_ERROR]' in log and '[TB_COMPLETE]' not in log and '[FAIL]' not in log,case['Case']
            else:
                assert '[TB_COMPLETE] '+case['Top'] in log and not re.search(r'\[FAIL\]|Failure:|Fatal:|ERROR:',log),case['Case']
                assert int(status['CompletionTime'].split()[0])<100_000_000_000,case['Case']
        simulations.append(record)
        if status['Result']!='PASS' or case['Negative']:continue
        if case['Capture']:
            folder=group/'waveforms'
            waves.append(dict(Case=case['Case'],Testbench=case['Top'],Beta=case.get('Beta','NA'),
                              CompletionTime=status['CompletionTime'],WDBBytes=status['WDBBytes'],
                              VCDWindow='0..12000 ns',Result='PASS'))
        if case.get('Regression'):continue
        for match in re.finditer(r'\[METRIC\] ([^\r\n]+)',log):
            values=match.group(1).split(',')
            assert len(values)==13,(case['Case'],values)
            app,length,beta,chains,patterns,shifts,serial_count,weighted,ff_count,distinct_sum,distinct_tuple,cycle=map(int,values[:12])
            duration=values[12]
            assert patterns>=256 and shifts==patterns*length and chains==4
            measured=F(weighted,chains*patterns*length*(length+1)//2)
            serial=F(serial_count,chains*(shifts-1))
            ff=F(ff_count,chains*shifts*length)
            name=APPS[app];target=None;feasible='NA';selection='reference';feasible_min=feasible_max='NA'
            if app>=2:
                config=describe(name,length,beta,chains)
                estimated=F(config['EstimatedWTM'])
                rates=[sum((regional_wtm(length,*t) for t in row),F())/chains for row in config['TimingCycle']]
                q,rem=divmod(patterns,len(rates))
                finite=(q*sum(rates,F())+sum(rates[:rem],F()))/patterns
                schedules.append(dict(Case=case['Case'],**case.get('Configurations',{}).get(name,config)))
                if 'Configurations' in case:
                    optimized=case['Configurations'][name];target=F(optimized['TargetWTM'])
                    feasible=optimized['TargetFeasible'];selection=optimized['Selection']
                    feasible_min=float(F(optimized['FeasibleMin']));feasible_max=float(F(optimized['FeasibleMax']))
            else:estimated=F(1,2) if app==0 else F(1,14);finite=estimated
            error=abs(measured-estimated)*100
            assert error<=2,(case['Case'],name,'Measured/estimated WTM error > 2 pp',float(error))
            assert distinct_sum<=patterns*chains and distinct_tuple<=patterns
            row=dict(Case=case['Case'],Approach=name,ChainLength=length,Beta=beta,NumChains=chains,
                     TargetWTM='NA' if target is None else float(target),TargetFeasible=feasible,Selection=selection,
                     FeasibleMinWTM=feasible_min,FeasibleMaxWTM=feasible_max,
                     EstimatedWTM=float(estimated),FiniteScheduleEstimatedWTM=float(finite),MeasuredWTM=float(measured),
                     TargetQuantizationErrorPP='NA' if target is None else float(abs(estimated-target)*100),
                     TargetErrorPP='NA' if target is None else float(abs(measured-target)*100),SimulationErrorPP=float(error),
                     SerialToggleRate=float(serial),ActualChainToggleFraction=float(ff),
                     SerialTransitions=serial_count,SerialOpportunities=chains*(shifts-1),
                     WeightedTransitions=weighted,WTMDenominator=chains*patterns*length*(length+1)//2,
                     FFChanges=ff_count,FFOpportunities=chains*shifts*length,
                     ShiftsPerChain=shifts,TotalEnabledChainShifts=shifts*chains,Patterns=patterns,SchedulePeriod=cycle,
                     ScheduleRemainderPatterns=patterns%cycle,DistinctChainPatternsSum=distinct_sum,
                     DistinctPatternTuples=distinct_tuple,SimTime=duration,Result='PASS')
            metrics.append(row)
        app_params={int(v.split(',')[0]):v.split(',') for v in re.findall(r'\[METRIC\] ([^\r\n]+)',log)}
        for values in re.findall(r'\[DIVERSITY\] ([^\r\n]+)',log):
            app,chain,count,patterns=map(int,values.split(','));params=app_params[app]
            diversity.append(dict(Case=case['Case'],Approach=APPS[app],ChainLength=int(params[1]),Beta=int(params[2]),
                                  Chain=chain,DistinctPatterns=count,Patterns=patterns,
                                  Meaning='stimulus diversity; not fault coverage'))
        for values in re.findall(r'\[EXPOSURE\] ([^\r\n]+)',log):
            app,chain,k,count,patterns=map(int,values.split(','));params=app_params[app]
            length,beta=int(params[1]),int(params[2]);name=APPS[app]
            if app==0:expected=patterns;expected_cycle=F(1)
            elif app==1:expected=0;expected_cycle=F(0)
            else:
                config=next(v for v in schedules if v['Case']==case['Case'] and v['Approach']==name)
                cycle=config['TimingCycle'];q,rem=divmod(patterns,len(cycle))
                flags=[int(row[chain][0]<=k<row[chain][0]+beta) for row in cycle]
                expected=q*sum(flags)+sum(flags[:rem]);expected_cycle=F(sum(flags),len(cycle))
            assert count==expected,(case['Case'],name,chain,k,'exposure mismatch')
            exposures.append(dict(Case=case['Case'],Approach=name,ChainLength=length,Beta=beta,Chain=chain,
                                  PhysicalPosition=k,UnfilteredPatterns=count,Patterns=patterns,
                                  Exposure=float(F(count,patterns)),ExpectedFiniteExposure=float(F(expected,patterns)),
                                  ExpectedCycleExposure=float(expected_cycle),Reachable=expected_cycle>0,Result='PASS'))
    out=ROOT/'Results/Phase3/Comparison/reports'
    write_csv(out/'phase3_simulation_summary.csv',simulations)
    compare=[v for v in metrics if v['Case'].startswith('tb_phase3_comparison')]
    write_csv(out/'phase3_wtm_comparison.csv',compare)
    write_csv(out/'phase3_pattern_diversity.csv',diversity)
    write_csv(out/'phase3_position_exposure.csv',exposures)
    (out/'phase3_configuration_schedules.json').write_text(json.dumps(schedules,indent=2))
    for group in ['Swap','Moving']:
        write_csv(ROOT/f'Results/Phase3/{group}/reports/{group.lower()}_verification_summary.csv',[v for v in simulations if v['Group']==group])
        write_csv(ROOT/f'Results/Phase3/{group}/reports/{group.lower()}_wtm_summary.csv',[v for v in metrics if v['Case'].startswith('tb_'+group.lower())])
    for group in ['Swap','Moving','Comparison']:
        write_csv(ROOT/f'Results/Phase3/{group}/waveforms/waveform_summary.csv',
                  [v for v in waves if any(c['Case']==v['Case'] and c['Group']==group for c in plan)],
                  ['Case','Testbench','Beta','CompletionTime','WDBBytes','VCDWindow','Result'])
    if require_all:
        assert len(simulations)==69,len(simulations)
        assert all(v['Result']=='PASS' for v in simulations),[v for v in simulations if v['Result']!='PASS']
        assert len(compare)==75,len(compare)
    if figures and compare:make_figures(compare,exposures,diversity)
    print('Collected',sum(v['Result']=='PASS' for v in simulations),'PASS /',len(simulations),'planned cases;',len(metrics),'measured approach records.')
    return simulations,metrics

def make_figures(rows,exposures,diversity):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    folder=ROOT/'Results/Phase3/Comparison/figures';folder.mkdir(exist_ok=True)
    colors={'basic':'#1976b9','swap':'#d97c16','moving':'#348248'}
    def save(fig,name):
        fig.tight_layout();fig.savefig(folder/(name+'.svg'));fig.savefig(folder/(name+'.png'),dpi=160);plt.close(fig)
    chosen=sorted([r for r in rows if r['ChainLength']==64 and r['Case'].endswith('_T20')],key=lambda r:list(APPS.values()).index(r['Approach']))
    fig,ax=plt.subplots(figsize=(10,5));xx=np.arange(len(chosen))
    ax.bar(xx-.18,[r['EstimatedWTM']*100 for r in chosen],.36,label='Schedule estimate')
    ax.bar(xx+.18,[r['MeasuredWTM']*100 for r in chosen],.36,label='XSim measured')
    ax.set_xticks(xx);ax.set_xticklabels([r['Approach']+(' (nearest)' if r['Selection']=='nearest-feasible' else '') for r in chosen])
    ax.set(ylabel='Normalized scan-in WTM (%)',title='64-bit / four-chain comparison; requested controlled target 20%')
    ax.legend();save(fig,'wtm_comparison')
    for metric,label,name in [('MeasuredWTM','Measured WTM (%)','requested_vs_measured_wtm'),
                              ('TargetErrorPP','Absolute target error (percentage points)','wtm_target_error'),
                              ('ActualChainToggleFraction','Actual scan FF switching (%)','ff_switching_vs_target')]:
        fig,axes=plt.subplots(1,3,figsize=(15,4.5))
        for ax,length in zip(axes,[64,128,200]):
            for approach in colors:
                values=sorted([r for r in rows if r['ChainLength']==length and r['Approach']==approach],key=lambda r:r['TargetWTM'])
                x=[r['TargetWTM']*100 for r in values]
                y=[r[metric]*(1 if metric=='TargetErrorPP' else 100) for r in values]
                ax.plot(x,y,'o-',color=colors[approach],label=approach)
                for r,a,b in zip(values,x,y):
                    if r['Selection']=='nearest-feasible':ax.plot(a,b,'x',markersize=12,color='black')
            if metric=='MeasuredWTM':ax.plot([10,30],[10,30],':',color='gray',label='ideal target')
            ax.set(xlabel='Requested WTM (%)',ylabel=label,title=f'L={length}, N=4');ax.grid(alpha=.2)
        axes[0].legend(fontsize=8);fig.suptitle('Black x = target outside feasible range; explicitly nearest-feasible')
        save(fig,name)
    fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True)
    for ax,app in zip(axes,['basic','swap','moving']):
        values=[v for v in exposures if v['Case']=='tb_phase3_comparison_L64_T20' and v['Approach']==app]
        data=np.zeros((4,64))
        for v in values:data[v['Chain'],v['PhysicalPosition']]=v['Exposure']
        image=ax.imshow(data,vmin=0,vmax=1,aspect='auto',interpolation='nearest',cmap='viridis')
        ax.set(ylabel=app+' chain',yticks=range(4))
    axes[-1].set_xlabel('Physical scan FF index (0 = scan input); 14-bit low regions restrict reach')
    # Reserve a separate colorbar axis; later layout changes must not overlap data.
    fig.subplots_adjust(left=.09,right=.83,bottom=.11,top=.91,hspace=.3)
    color_axis=fig.add_axes([.86,.15,.022,.70])
    fig.colorbar(image,cax=color_axis,label='Measured fraction of patterns receiving n=1')
    fig.suptitle('Observed n=1 exposure: L=64, four chains, controlled request 20%')
    fig.savefig(folder/'position_exposure.svg');fig.savefig(folder/'position_exposure.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    ax.bar([r['Approach'] for r in chosen],[r['DistinctPatternTuples'] for r in chosen],color=['#777','#999','#1976b9','#d97c16','#348248'])
    ax.set(ylabel='Observed distinct four-chain pattern tuples / 1024',title='Stimulus diversity at L=64, controlled request 20%; not fault coverage')
    save(fig,'distinct_pattern_counts')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--require-all',action='store_true');p.add_argument('--no-figures',action='store_true')
    args=p.parse_args();collect(args.require_all,not args.no_figures)
