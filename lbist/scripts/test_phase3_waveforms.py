"""Test the temporal checker using actual captures and intentionally corrupted reads."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from phase3_trace import Trace
from phase3_waveform_analysis import check_trace,verify_preview
ROOT=Path(__file__).resolve().parents[2]
class WaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.swap=Trace(ROOT/'Results/Phase3/Swap/waveforms/tb_swap_integration_L64_B16_N4.vcd')
        cls.moving=Trace(ROOT/'Results/Phase3/Moving/waveforms/tb_moving_integration_L64_B16_N4.vcd')
    def test_real_swap_boundaries(self):
        result=check_trace(self.swap,'/tb_swap_integration/engine',3,64,16)
        t=result['Events']['first_switch'];prefix=result['Prefix']
        self.assertEqual(self.swap.integer(prefix,'shift_count_v',t,True),31)
        self.assertEqual(self.swap.integer(prefix,'shift_count_v',t),32)
        self.assertEqual(self.swap.integer(prefix,'mode_0',t,True),0)
        self.assertEqual(self.swap.integer(prefix,'mode_0',t),3)
    def test_real_moving_wrap_and_exposure(self):
        result=check_trace(self.moving,'/tb_moving_integration/engine',4,64,16)
        t=result['Events']['moving_wrapped'];prefix=result['Prefix']
        self.assertEqual(self.moving.integer(prefix,'moving_position_v',t,True),20)
        self.assertEqual(self.moving.integer(prefix,'moving_position_v',t),0)
    def corrupted(self,name):
        original=self.swap.integer
        def read(prefix,signal,t,before=False):
            value=original(prefix,signal,t,before)
            return value+1 if signal==name and t>2000 else value
        return read
    def test_counter_corruption_fails(self):
        with patch.object(self.swap,'integer',self.corrupted('shift_count_v')):
            with self.assertRaises(AssertionError):check_trace(self.swap,'/tb_swap_integration/engine',3,64,16)
    def test_mode_corruption_fails(self):
        with patch.object(self.swap,'integer',self.corrupted('mode_0')):
            with self.assertRaises(AssertionError):check_trace(self.swap,'/tb_swap_integration/engine',3,64,16)
    def test_scan_data_corruption_fails(self):
        with patch.object(self.swap,'integer',self.corrupted('chain_flat')):
            with self.assertRaises(AssertionError):check_trace(self.swap,'/tb_swap_integration/engine',3,64,16)
    def test_saved_preview_corruption_fails(self):
        import tempfile
        from render_waveform_previews import render_window
        prefix='/tb_swap_integration/engine'
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder)/'boundary.svg'
            render_window(self.swap,prefix,['clk','shift_count_v','mode_0'],55000,75000,destination,'test')
            self.assertGreater(verify_preview(self.swap,prefix,destination)['IntervalsChecked'],0)
            saved=destination.read_text()
            self.assertIn('mode_0 = 00,',saved)
            destination.write_text(saved.replace('mode_0 = 00,','mode_0 = 11,',1))
            with self.assertRaises(AssertionError):verify_preview(self.swap,prefix,destination)
    def test_preview_cannot_exceed_recorded_time(self):
        from render_waveform_previews import render_window
        with self.assertRaises(AssertionError):
            render_window(self.swap,'/tb_swap_integration/engine',['clk'],0,self.swap.end+1,Path('unused.svg'),'bad')
if __name__=='__main__':unittest.main(verbosity=2)
