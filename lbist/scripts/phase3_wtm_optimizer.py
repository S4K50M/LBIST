"""Exact-rational schedule optimizer for Basic, Swap and Moving Control."""
import argparse
import json
from fractions import Fraction as F
from math import lcm
from functools import lru_cache
MIN_LOW = 14

def period(approach, length, beta):
    return {"basic":1, "swap":2, "moving":length-beta-2*MIN_LOW+1}[approach]

@lru_cache(maxsize=None)
def legal_betas(approach, length):
    if not isinstance(length,int) or not 28<=length<=4096:
        raise ValueError("length must be an integer in 28..4096")
    if approach=="basic": return list(range(length%2,length-28+1,2))
    if approach=="swap":
        if length%2: raise ValueError("Swap supports even lengths only")
        return list(range(length//2-14+1))
    if approach=="moving": return list(range(length-28+1))
    raise ValueError("unknown approach")

def timing(approach,length,beta,pattern=0,chain=0,initial=0):
    if beta not in legal_betas(approach,length): raise ValueError("illegal beta")
    if approach=="basic":
        a=g=(length-beta)//2
    elif approach=="swap":
        # Zero-based (p,c)=(0,0) is paper's odd vector / odd chain.
        a,g=(length//2-beta,length//2) if (pattern+chain)%2==0 else (length//2,length//2-beta)
    else:
        span=period(approach,length,beta)
        if not 0<=initial<span: raise ValueError("illegal initial moving position")
        g=MIN_LOW+(pattern+initial)%span
        a=length-beta-g
    assert a+beta+g==length and min(a,g)>=MIN_LOW
    return a,beta,g

def regional_wtm(length,a,b,g):
    if min(a,g)<14 or b<0 or a+b+g!=length: raise ValueError("invalid region lengths")
    tri=lambda n:n*(n+1)//2
    return (F(tri(a)+tri(length)-tri(a+b),14)+F(tri(a+b)-tri(a),2))/tri(length)

def describe(approach,length,beta,chains=4,initial=0):
    if not 1<=chains<=16: raise ValueError("chains must be 1..16")
    timings=[[timing(approach,length,beta,p,c,initial) for c in range(chains)]
             for p in range(period(approach,length,beta))]
    estimate=sum((regional_wtm(length,*t) for row in timings for t in row),F())/(len(timings)*chains)
    exposure=[]
    for c in range(chains):
        counts=[0]*length
        for row in timings:
            a,b,g=row[c]
            for k in range(a,a+b): counts[k]+=1 # physical k=0 at scan-in stage
        exposure.append([str(F(n,len(timings))) for n in counts])
    return {"Approach":approach,"ChainLength":length,"Beta":beta,"NumChains":chains,
            "MinLow":14,"SchedulePeriod":len(timings),"InitialPosition":initial,
            "EstimatedWTM":str(estimate),"TimingCycle":timings,"ExpectedExposure":exposure,
            "Validity":"paper-constrained","Ordering":"physical alpha/beta/gamma; chronological gamma/beta/alpha"}

def optimize(approach,length,target,chains=4,nearest=False):
    if not 1<=chains<=16: raise ValueError("chains must be 1..16")
    target=F(target)
    if not 0<=target<=1: raise ValueError("target must be in [0,1]")
    # Evaluate every pattern and chain of each candidate schedule, exactly.
    candidates=[]
    for beta in legal_betas(approach,length):
        cycle=period(approach,length,beta)
        estimate=sum((regional_wtm(length,*timing(approach,length,beta,p,c))
                      for p in range(cycle) for c in range(chains)),F())/(cycle*chains)
        candidates.append((abs(estimate-target),beta,estimate))
    low=min(v[2] for v in candidates); high=max(v[2] for v in candidates)
    feasible=low<=target<=high
    if not feasible and not nearest:
        raise ValueError(f"target outside feasible range {float(low)*100:.6f}%..{float(high)*100:.6f}%; use --nearest")
    error,beta,estimate=min(candidates)
    result=describe(approach,length,beta,chains)
    result.update(TargetWTM=str(target),TargetFeasible=feasible,
                  Selection="nearest-feasible" if not feasible else "in-range-quantized",
                  QuantizationErrorPP=str(error*100),FeasibleMin=str(low),FeasibleMax=str(high),
                  TieBreak="smaller beta")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approach',choices=['basic','swap','moving'],required=True)
    p.add_argument('--chain-length',type=int,required=True)
    p.add_argument('--chains',type=int,default=4)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--target-percent',type=F)
    group.add_argument('--target-fraction',type=F)
    p.add_argument('--nearest',action='store_true')
    args=p.parse_args()
    try:
        if not 1<=args.chains<=16: raise ValueError("chains must be 1..16")
        target=args.target_fraction if args.target_fraction is not None else args.target_percent/100
        result=optimize(args.approach,args.chain_length,target,args.chains,args.nearest)
    except ValueError as e: p.error(str(e))
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
