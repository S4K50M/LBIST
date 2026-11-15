"""Independent exact-sum and CLI tests for the offline optimizer."""
import json
import subprocess
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path
from basic_wtm_optimizer import configurations, estimated_wtm, optimize

class OptimizerTests(unittest.TestCase):
    def test_exact_weighted_sum_and_legal_enumeration(self):
        for length in range(28,130):
            for a,b,g in configurations(length):
                self.assertEqual(a,g)
                self.assertGreaterEqual(a,14)
                rates=[F(1,14)]*a+[F(1,2)]*b+[F(1,14)]*g
                independent=sum((i+1)*v for i,v in enumerate(rates))/sum(range(1,length+1))
                self.assertEqual(estimated_wtm(length,a,b,g),independent)
    def test_target_and_global_optimum(self):
        for target in [F(1,14),F(1,10),F(1,5),F(3,10)]:
            result=optimize(64,target)
            errors=[abs(estimated_wtm(64,*c)-target) for c in configurations(64)]
            self.assertEqual(F(result['ErrorPP'])/100,min(errors))
    def test_tie_chooses_smaller_beta(self):
        midpoint=(estimated_wtm(64,32,0,32)+estimated_wtm(64,31,2,31))/2
        self.assertEqual(optimize(64,midpoint)['Beta'],0)
    def test_bad_lengths_and_timings(self):
        for length in [0,1,27,-1]:
            with self.assertRaises(ValueError): configurations(length)
        for timing in [(31,1,32),(0,65,0),(13,38,13)]:
            with self.assertRaises(ValueError): estimated_wtm(64,*timing)
    def test_out_of_range(self):
        for value in [F(0),F(1),F(-1)]:
            with self.assertRaises(ValueError): optimize(64,value)
        self.assertTrue(optimize(64,F(1),True)['OutsideRange'])
        self.assertEqual(optimize(64,F(1),True)['Beta'],36)
    def test_cli_units_and_rejection(self):
        script=Path(__file__).with_name('basic_wtm_optimizer.py')
        def run(*args): return subprocess.run([sys.executable,str(script),'--chain-length','64',*args],capture_output=True,text=True)
        a=run('--target-percent','20'); b=run('--target-fraction','1/5')
        self.assertEqual(a.returncode,0); self.assertEqual(a.stdout,b.stdout)
        self.assertNotEqual(run('--target-percent','90').returncode,0)
        self.assertEqual(run('--target-percent','90','--nearest').returncode,0)

if __name__=='__main__': unittest.main(verbosity=2)
