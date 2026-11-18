"""Extract only actual Vivado power values, preserving precision and coverage."""
from pathlib import Path
import re,csv
from audit_final_evidence import write
R=Path(__file__).resolve().parents[2];P=R/'Results/Final/FPGA_Analysis'
NAMES=['Direct','Constant n=3','Basic','Swap','Moving']
def cell(text,label,default=''):
    m=re.search(r'^\|\s*'+re.escape(label)+r'\s*\|\s*([^|]+)\|',text,re.M)
    return m[1].strip() if m else default
def collect(tag,config,approach):
    path=P/'power'/tag/'power.rpt'
    if not path.exists():return dict(Approach=approach,Configuration=config,Status='NOT_AVAILABLE')
    text=path.read_text();match=cell(text,'Design Nets Matched')
    numbers=re.search(r'(\d+)\s*/\s*(\d+)',match)
    matched=int(numbers[1]) if numbers else 0;total=int(numbers[2]) if numbers else 0
    pct=100*matched/total if total else 0
    def number(label,missing='0.000'):
        raw=cell(text,label,missing)
        # Preserve '<0.001' instead of treating a bound as zero or a precise value.
        return raw
    return dict(Approach=approach,Configuration=config,TotalW=number('Total On-Chip Power (W)'),
                StaticW=number('Device Static (W)'),DynamicW=number('Dynamic (W)'),
                ClockW=number('Clocks'),LogicW=number('Slice Logic'),SignalsW=number('Signals'),
                BRAMW=number('Block RAM'),DSPW=number('DSPs'),MMCMW=number('MMCM'),
                MatchedNets=matched,DesignNets=total,AnnotationPercent=pct,
                VivadoConfidence=cell(text,'Confidence Level'),
                Status='PARTIAL_RTL_SAIF_ESTIMATE' if pct>=25 else 'LOW_MAPPING_ASSUMPTION_DOMINATED',
                TimingClosure='FAIL',CPUClockMHz=50,AmbientC=25,Process='typical',
                Boundary='OOC processor+common clocks; no physical IO/external memory',
                Report=str(path.relative_to(R)).replace('\\','/'))
def main():
    values=[collect(f'approach_{i}','full_lbist',name) for i,name in enumerate(NAMES)]
    write('FPGA_Analysis/power_comparison.csv',values)
    refs=[collect(c,c,'Functional lwsw') for c in ['baseline','scan_enabled']]
    write('FPGA_Analysis/power/functional_comparison.csv',refs)
    provenance=[];subsystem=[]
    for i,name in enumerate(NAMES):
        folder=P/'power'/f'approach_{i}'
        switch=(folder/'switching.rpt').read_text() if (folder/'switching.rpt').exists() else ''
        # The S/P/D source tags are printed by Vivado itself: simulation,
        # propagation and default. Count them separately rather than calling
        # propagated nets directly annotated.
        for boundary,prefix in [('Whole design',''),('IF_RF_native_hierarchy','u_system/scan_cpu.u_cpu/PIPESTAGE_IF_RF/'),
                                ('Router','u_system/lbist.u_router/'),('Controller','u_system/lbist.u_ctrl/'),('MISR','u_system/lbist.u_response/')]:
            counts={'S':0,'P':0,'D':0,'C':0,'U':0}
            for line in switch.splitlines():
                if not line.startswith(prefix):continue
                m=re.search(r'toggle rate = .*?\(([A-Z])\)',line)
                if m:counts[m[1]]=counts.get(m[1],0)+1
            provenance.append(dict(Approach=name,Boundary=boundary,Simulation=counts['S'],Propagated=counts['P'],
                                    Default=counts['D'],Other=sum(v for k,v in counts.items() if k not in ['S','P','D']),
                                    Total=sum(counts.values())))
        detail=folder/'power_details.rpt'
        if detail.exists():
            text=detail.read_text()
            subsystem.append(dict(Approach=name,Boundary='Routed PIPESTAGE_IF_RF hierarchy (includes absorbed decode/comb logic)',
                                  DynamicW=cell(text,'PIPESTAGE_IF_RF','NOT_REPORTED'),WholeC_AssumptionDominatedDynamicW=values[i].get('DynamicW',''),
                                  MMCMW=values[i].get('MMCMW',''),ResolutionW='0.001',
                                  Status='PARTIAL_RTL_SAIF_AND_PROPAGATION; no reliable whole-processor saving claim'))
    if provenance:write('FPGA_Analysis/power/annotation_by_boundary.csv',provenance)
    if subsystem:write('FPGA_Analysis/power/subsystem_comparison.csv',subsystem)
    print('Extracted',len(values)+len(refs),'native estimates; annotation quality retained.')
if __name__=='__main__':main()
