"""Adversarial checks of actual captured scan data; run after capture generation."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from phase4_analysis import check_storage,core_trace,OUT,Trace
from phase3_waveform_analysis import verify_preview
from render_waveform_previews import render_window
class ScanCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.unit=Trace(OUT/'IF_RF/waveforms/scan_unit_seed12345.vcd')
        cls.plpf=Trace(OUT/'PLPF_Integration/waveforms/real_plpf_B20_P1024.vcd')
        cls.core=Trace(OUT/'Core_Integration/waveforms/core_scan_lwsw.vcd')
    def test_register_trace(self):
        self.assertEqual(check_storage(self.unit,'tb_reg_IF_RF_scan')['EnabledScanShifts'],16577)
    def test_real_plpf_and_unload_trace(self):
        self.assertEqual(check_storage(self.plpf,'tb_if_rf_plpf_integration',True)['EnabledScanShifts'],65600)
    def test_processor_disabled_trace(self):
        self.assertEqual(core_trace(self.core)['Result'],'PASS')
    def test_bad_feedback_is_rejected(self):
        original=self.unit.integer
        def corrupt(prefix,name,t,before=False):
            value=original(prefix,name,t,before)
            return 1-value if name=='scan_feedback' and t>1000 else value
        with patch.object(self.unit,'integer',corrupt):
            with self.assertRaises(AssertionError):check_storage(self.unit,'tb_reg_IF_RF_scan')
    def test_bad_scan_output_is_rejected(self):
        original=self.unit.integer
        def corrupt(prefix,name,t,before=False):
            value=original(prefix,name,t,before)
            return 1-value if name=='scan_out' and t>1000 else value
        with patch.object(self.unit,'integer',corrupt):
            with self.assertRaises(AssertionError):check_storage(self.unit,'tb_reg_IF_RF_scan')
    def test_saved_preview_corruption_is_rejected(self):
        prefix='/tb_reg_IF_RF_scan'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sample.svg'
            render_window(self.unit,prefix,['clk','scan_feedback'],10000,20000,path,'test')
            verify_preview(self.unit,prefix,path)
            saved=path.read_text()
            self.assertIn('scan_feedback = 1,',saved)
            path.write_text(saved.replace('scan_feedback = 1,','scan_feedback = 0,',1))
            with self.assertRaises(AssertionError):verify_preview(self.unit,prefix,path)
if __name__=='__main__':unittest.main(verbosity=2)
