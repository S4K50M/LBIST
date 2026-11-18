"""Rename only SAIF instance hierarchy for the production FPGA wrappers.

No switching values are altered. Tokens and record counts are independently
checked; mapping manifests retain input/output hashes and exact transformations.
"""
from pathlib import Path
import re,hashlib,json
R=Path(__file__).resolve().parents[2];D=R/'Results/Final/FPGA_Analysis/power/activity'
def parse(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|(?:\\.|[^\s()])+|[()]',text)
    stack=[];root=None
    for t in tokens:
        if t=='(':
            node=[]
            if stack:stack[-1].append(node)
            else:root=node
            stack.append(node)
        elif t==')':stack.pop()
        else:stack[-1].append(t)
    assert not stack
    return root
def emit(n):return '('+' '.join(emit(x) if isinstance(x,list) else x for x in n)+')'
def pretty(n,depth=0):
    if n[0] not in ['SAIFILE','INSTANCE','NET']:return '  '*depth+emit(n)
    lead=[];children=[]
    for x in n:
        (children if isinstance(x,list) else lead).append(x)
    return '  '*depth+'('+' '.join(lead)+'\n'+'\n'.join(pretty(x,depth+1) for x in children)+'\n'+'  '*depth+')'
def instance(n,name):
    for child in n:
        if isinstance(child,list) and child[:2]==['INSTANCE',name]:return child
    raise ValueError(name)
def fingerprint(n):
    out=[]
    def walk(x):
        if isinstance(x,list):
            if x and x[0]=='NET':out.extend(emit(z)[emit(z).find(' '):] for z in x[1:])
            else:
                for z in x:walk(z)
    walk(n)
    return hashlib.sha256('\n'.join(sorted(out)).encode()).hexdigest(),len(out)
def collapse(parent,label):
    g=instance(parent,label);parent.remove(g)
    for item in g[2:]:
        if item[0]=='INSTANCE':item[1]=label+'.'+item[1];parent.append(item)
        elif item[0]=='NET':
            for net in item[1:]:net[0]=label+'.'+net[0]
            parent.append(item)
        else:raise ValueError(item[0])
def mapped(src,dst,select,new_name,generates=()):
    original=src.read_text();tree=parse(original);n=tree
    for label in select:n=instance(n,label)
    before=fingerprint(n)
    n[1]=new_name
    for g in generates:collapse(n,g)
    # Wrap the selected real design subtree in the actual routed top hierarchy.
    head=[x for x in tree if not (isinstance(x,list) and x and x[0]=='INSTANCE')]
    if new_name=='u_system':head.append(['INSTANCE','final_fpga_top',n])
    else:head.append(['INSTANCE','final_fpga_top',['INSTANCE','u_system',n]])
    output=pretty(head)+'\n';dst.write_text(output)
    after=fingerprint(parse(output));assert before==after,'Activity data altered'
    return dict(Source=str(src.relative_to(R)),Mapped=str(dst.relative_to(R)),
                SourceSHA256=hashlib.sha256(src.read_bytes()).hexdigest(),MappedSHA256=hashlib.sha256(dst.read_bytes()).hexdigest(),
                ActivityFingerprint=before[0],NetRecords=before[1],InstanceSelection='/'.join(select),
                Rename=new_name,CollapsedGenerates=list(generates),ActivityUnchanged=True)
def main():
    records=[]
    for a in range(5):
        records.append(mapped(D/f'approach_{a}.saif',D/f'mapped_approach_{a}.saif',
                              ['tb_final_activity','engine','system_copy'],'u_system',['scan_cpu','lbist']))
    if (D/'functional.saif').exists():
        for label,name,config in [('U_CORE','baseline.u_cpu','baseline'),('U_SCAN','scan_cpu.u_cpu','scan_enabled')]:
            records.append(mapped(D/'functional.saif',D/f'mapped_{config}.saif',['tb_final_functional_activity',label],name))
    (D.parent/'saif_mapping_manifest.json').write_text(json.dumps(records,indent=2))
    print('Mapped',len(records),'traces; switching records unchanged.')
if __name__=='__main__':main()
