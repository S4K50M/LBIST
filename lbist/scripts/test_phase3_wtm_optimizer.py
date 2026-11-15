"""Independent weighted-sum, ordering, scheduling, exposure and CLI checks."""
import json
import subprocess
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path
from phase3_wtm_optimizer import legal_betas,timing,regional_wtm,describe,optimize,period
class ScheduleTests(unittest.TestCase):
    def test_all_region_sums_and_constraints(self):
        for app in ['basic','swap','moving']:
            for length in [28,64,128,200]:
                for beta in legal_betas(app,length):
                    for pat in range(period(app,length,beta)):
                        a,b,g=timing(app,length,beta,pat,0)
                        self.assertEqual(a+b+g,length)
                        self.assertGreaterEqual(min(a,g),14)
                        # Independent chronological weighting, reversing Figure 6 IN/OUT order.
                        bits=[F(1,14)]*g+[F(1,2)]*b+[F(1,14)]*a
                        rate=sum((length-i)*v for i,v in enumerate(bits))/sum(range(1,length+1))
                        self.assertEqual(regional_wtm(length,a,b,g),rate)
    def test_swap_pattern_and_chain_parity(self):
        self.assertEqual(timing('swap',64,16,0,0),(16,16,32))
        self.assertEqual(timing('swap',64,16,1,0),(32,16,16))
        self.assertEqual(timing('swap',64,16,0,1),(32,16,16))
        self.assertNotEqual(regional_wtm(64,*timing('swap',64,16,0,0)),regional_wtm(64,*timing('swap',64,16,1,0)))
    def test_moving_all_positions_and_wrap(self):
        cycle=[timing('moving',64,16,p) for p in range(22)]
        self.assertEqual(cycle[0],(34,16,14))
        self.assertEqual(cycle[20],(14,16,34))
        self.assertEqual(cycle[21],cycle[0])
        self.assertEqual(timing('moving',64,16,0,0,5),cycle[5])
    def test_position_exposure(self):
        for app,reachable in [('basic',16),('swap',32),('moving',36)]:
            result=describe(app,64,16,4)
            for c in result['ExpectedExposure']:
                self.assertEqual(sum(map(F,c)),16)
                self.assertEqual(sum(F(v)>0 for v in c),reachable)
        self.assertTrue(all(F(v)==0 for v in describe('moving',64,0)['ExpectedExposure'][0]))
    def test_feasible_ranges_and_nearest(self):
        self.assertEqual(F(optimize('swap',64,F(1,10))['FeasibleMax']),F(43,224))
        with self.assertRaises(ValueError): optimize('swap',64,F(1,5))
        r=optimize('swap',64,F(3,10),nearest=True)
        self.assertFalse(r['TargetFeasible']);self.assertEqual(r['Beta'],18)
        self.assertEqual(r['Selection'],'nearest-feasible')
    def test_optimum_and_exact_cycle_average(self):
        for app in ['basic','swap','moving']:
            for target in [F(1,10),F(3,20),F(1,5),F(1,4),F(3,10)]:
                result=optimize(app,64,target,4,True)
                all_errors=[abs(F(describe(app,64,b)['EstimatedWTM'])-target) for b in legal_betas(app,64)]
                self.assertEqual(F(result['QuantizationErrorPP'])/100,min(all_errors))
                rows=result['TimingCycle']
                full=sum((regional_wtm(64,*t) for row in rows for t in row),F())/(len(rows)*4)
                self.assertEqual(full,F(result['EstimatedWTM']))
    def test_illegal_and_odd_configuration(self):
        with self.assertRaises(ValueError): legal_betas('swap',65)
        with self.assertRaises(ValueError): legal_betas('moving',1)
        with self.assertRaises(ValueError): timing('moving',64,37)
        with self.assertRaises(ValueError): timing('moving',64,16,0,0,21)
        self.assertEqual(sum(timing('moving',65,17)),65)
        for n in [0,17]:
            with self.assertRaises(ValueError): optimize('swap',64,F(1,10),n)
    def test_legacy_basic_optimizer_unchanged(self):
        from basic_wtm_optimizer import optimize as basic_optimize
        for t in [F(1,10),F(3,20),F(1,5),F(1,4),F(3,10)]:
            old=basic_optimize(64,t);new=optimize('basic',64,t)
            self.assertEqual(old['Beta'],new['Beta']);self.assertEqual(old['EstimatedWTM'],new['EstimatedWTM'])
    def test_cli(self):
        script=Path(__file__).with_name('phase3_wtm_optimizer.py')
        def run(*a):return subprocess.run([sys.executable,str(script),'--approach','swap','--chain-length','64',*a],capture_output=True,text=True)
        a=run('--target-percent','10');b=run('--target-fraction','1/10')
        self.assertEqual(a.returncode,0);self.assertEqual(a.stdout,b.stdout)
        self.assertNotEqual(run('--target-percent','20').returncode,0)
        self.assertEqual(run('--target-percent','20','--nearest').returncode,0)
if __name__=='__main__': unittest.main(verbosity=2)
