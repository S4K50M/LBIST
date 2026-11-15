"""Create reproducible parameter sweeps using the exact offline optimizer."""
import json
from pathlib import Path
from fractions import Fraction
from phase3_wtm_optimizer import optimize
ROOT=Path(__file__).resolve().parents[2]
def build():
    cases=[]
    def add(group,top,length,beta,chains=4,initial=0,negative=False,capture=False,patterns=1024):
        tag=f"{top}_L{length}_B{beta}_N{chains}" + (f"_I{initial}" if initial else "")
        generics=dict(CHAIN_LENGTH=length,BETA=beta,NUM_CHAINS=chains)
        if 'controller' in top: generics['INITIAL_POSITION']=initial
        if 'integration' in top: generics['PATTERNS']=patterns
        cases.append(dict(Group=group,Top=top,Case=tag,Generics=generics,
                          Negative=negative,Capture=capture,Length=length,Beta=beta,Chains=chains))
    for group,name in [('Swap','swap'),('Moving','moving')]:
        positives=([(64,0,4,0),(64,16,4,0),(64,18,4,0),(128,16,4,0),(200,32,4,0),(28,0,1,0),(64,16,3,0)] if name=='swap' else
                   [(64,0,4,0),(64,16,4,0),(64,36,4,0),(128,16,4,0),(200,32,4,0),(28,0,1,0),(65,17,4,0),(64,16,4,5)])
        for l,b,n,i in positives:
            add(group,'tb_'+name+'_controller',l,b,n,i,capture=(l==64 and b==16 and n==4 and i==0))
        invalid=[(65,16,4,0),(64,19,4,0),(64,65,4,0),(1,0,4,0),(64,16,17,0)] if name=='swap' else [(64,37,4,0),(64,65,4,0),(1,0,4,0),(64,16,4,21),(64,16,17,0)]
        for l,b,n,i in invalid: add(group,'tb_'+name+'_controller',l,b,n,i,negative=True)
        for l,b in [(64,16),(128,16),(200,32)]:
            add(group,'tb_'+name+'_integration',l,b,capture=l==64)
    for length in [64,128,200]:
        for target in [10,15,20,25,30]:
            configs={a:optimize(a,length,Fraction(target,100),4,True) for a in ['basic','swap','moving']}
            tag=f'tb_phase3_comparison_L{length}_T{target}'
            cases.append(dict(Group='Comparison',Top='tb_phase3_comparison',Case=tag,
                              Generics=dict(CHAIN_LENGTH=length,NUM_CHAINS=4,PATTERNS=1024,TARGET_PERCENT=target,
                              BASIC_BETA=configs['basic']['Beta'],SWAP_BETA=configs['swap']['Beta'],MOVING_BETA=configs['moving']['Beta']),
                              Negative=False,Capture=length==64 and target==20,Length=length,TargetPercent=target,Configurations=configs))
    for top in ['tb_lfsr_16','tb_phase_shifter','tb_plpf_optimized','tb_plpf_dynamic','tb_phase2_integration']:
        cases.append(dict(Group='Comparison',Top=top,Case='regression_'+top,Generics={},Negative=False,Capture=False,Regression=True))
    for l,b in [(64,0),(64,8),(64,16),(64,20),(64,28),(64,36),(28,0),(65,21),(64,1),(64,65),(1,0),(64,38)]:
        cases.append(dict(Group='Comparison',Top='tb_basic_controller',Case=f'regression_basic_unit_L{l}_B{b}',
                          Generics=dict(CHAIN_LENGTH=l,BETA=b),Negative=(l,b) in [(64,1),(64,65),(1,0),(64,38)],Capture=False,Regression=True))
    for b in [0,8,16,20,28,36]:
        cases.append(dict(Group='Comparison',Top='tb_basic_integration',Case=f'regression_basic_integration_B{b}',
                          Generics=dict(CHAIN_LENGTH=64,BETA=b),Negative=False,Capture=False,Regression=True))
    return cases
def write():
    dest=ROOT/'Results/Phase3/Comparison/work'
    dest.mkdir(parents=True,exist_ok=True)
    cases=build()
    (dest/'experiment_plan.json').write_text(json.dumps(cases,indent=2))
    lines=['set phase3_cases {}']
    for v in cases:
        generics=' '.join(f"{k}={value}" for k,value in v['Generics'].items())
        lines.append('lappend phase3_cases [list '+ ' '.join([v['Group'],v['Top'],v['Case'],'[list '+generics+']',
                     str(int(v['Negative'])),str(int(v['Capture'])),str(int(v.get('Regression',False)))])+']')
    (dest/'experiment_plan.tcl').write_text('\n'.join(lines)+'\n')
    print(f"Calculated {len(cases)} simulation cases from exact schedule optimization.")
if __name__=='__main__': write()
