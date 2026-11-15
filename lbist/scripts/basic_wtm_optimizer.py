"""Offline Basic Control optimizer; exact rational arithmetic, no on-chip logic."""
import argparse
import json
from fractions import Fraction

MIN_LOW = 14

def configurations(length):
    if not isinstance(length, int) or length < 2 * MIN_LOW:
        raise ValueError("chain length must be >=28")
    return [( (length-beta)//2, beta, (length-beta)//2 )
            for beta in range(length % 2, length-2*MIN_LOW+1, 2)]

def estimated_wtm(length, alpha, beta, gamma):
    if alpha != gamma or alpha + beta + gamma != length or min(alpha, gamma) < MIN_LOW or beta < 0:
        raise ValueError("illegal paper-compliant Basic timing")
    triangle = lambda n: n*(n+1)//2
    # Primary reference: complete weighted sums in Eq. 3, not beta/L alone.
    weights = (triangle(alpha), triangle(alpha+beta)-triangle(alpha),
               triangle(length)-triangle(alpha+beta))
    weighted = (Fraction(weights[0]+weights[2],14) + Fraction(weights[1],2))/triangle(length)
    simplified = Fraction(1,14) + (Fraction(1,2)-Fraction(1,14))*Fraction(beta,length)
    assert weighted == simplified
    return weighted

def optimize(length, target, nearest=False):
    target = Fraction(target)
    if not 0 <= target <= 1:
        raise ValueError("WTM fraction must lie in [0,1]")
    choices = [(a,b,g,estimated_wtm(length,a,b,g)) for a,b,g in configurations(length)]
    low,high = choices[0][3],choices[-1][3]
    outside = not low <= target <= high
    if outside and not nearest:
        raise ValueError(f"target outside feasible range [{float(low)*100:.9g}%, {float(high)*100:.9g}%]; use --nearest to select an endpoint")
    a,b,g,rate = min(choices,key=lambda c:(abs(c[3]-target),c[1]))
    return {"ChainLength":length,"Alpha":a,"Beta":b,"Gamma":g,
            "TargetWTM":str(target),"EstimatedWTM":str(rate),
            "ErrorPP":str(abs(rate-target)*100),"FeasibleMin":str(low),
            "FeasibleMax":str(high),"OutsideRange":outside,
            "Classification":"paper-compliant","TieBreak":"smaller beta"}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chain-length',type=int,required=True)
    targets=parser.add_mutually_exclusive_group(required=True)
    targets.add_argument('--target-fraction',type=Fraction,help='e.g. 1/5 or 0.2')
    targets.add_argument('--target-percent',type=Fraction,help='e.g. 20 means 20%%')
    parser.add_argument('--nearest',action='store_true',help='explicitly allow nearest endpoint for an out-of-range target')
    args=parser.parse_args(argv)
    target=args.target_fraction if args.target_fraction is not None else args.target_percent/100
    try: result=optimize(args.chain_length,target,args.nearest)
    except ValueError as error: parser.error(str(error))
    print(json.dumps(result,indent=2))
    print(f"Estimated WTM: {float(Fraction(result['EstimatedWTM']))*100:.9f}%; absolute error: {float(Fraction(result['ErrorPP'])):.9f} percentage points")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
