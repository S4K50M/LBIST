"""Adversarial verification against actual Phase 5A captures."""
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from phase5a_analysis import OUT, check_controller, check_core
from phase5a_trace import Phase5Trace, verify_preview
from render_waveform_previews import render_window

class CaptureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controller = Phase5Trace(OUT / "Controller/waveforms/controller_L64.vcd")
        cls.isolation = Phase5Trace(OUT / "Isolation/waveforms/core_isolation.vcd")
        cls.scan = Phase5Trace(OUT / "ShiftCapture/waveforms/core_shift_capture_P256.vcd")
        cls.prefix = "/tb_core_scan_isolation/engine"

    def test_controller(self):
        self.assertEqual(check_controller(self.controller, "/tb_lbist_test_controller", 64, 256)["Result"], "PASS")

    def test_complete_real_core_sequence(self):
        result = check_core(self.scan, "/tb_core_scan_shift_capture/engine")
        self.assertEqual((result["Shifts"], result["Captures"], result["Unloads"]), (16384, 256, 16384))

    def test_complete_isolation_trace(self):
        self.assertEqual(check_core(self.isolation, self.prefix)["Result"], "PASS")

    def test_protected_state_corruption_rejected(self):
        trace, prefix = self.isolation, self.prefix
        ack = next(t for t, v in trace.values(prefix, "isolation_ack") if v == "1")
        times = [t for t, v in trace.values(prefix, "clk") if v == "1" and t > ack]
        target = times[4]
        original = trace.value
        def corrupt(p, n, t, before=False):
            value = original(p, n, t, before)
            if n == "protected_state" and t == target:
                value = value[:-1] + ("0" if value[-1] == "1" else "1")
            return value
        with patch.object(trace, "value", corrupt):
            with self.assertRaises(AssertionError):
                check_core(trace, prefix)

    def test_external_write_corruption_rejected(self):
        trace = self.isolation
        original = trace.integer
        def corrupt(p, n, t, before=False):
            value = original(p, n, t, before)
            return 0 if n == "wr" and original(p, "isolation_ack", t) else value
        with patch.object(trace, "integer", corrupt):
            with self.assertRaises(AssertionError):
                check_core(trace, self.prefix)

    def test_serial_output_corruption_rejected(self):
        trace = self.isolation
        original = trace.integer
        def corrupt(p, n, t, before=False):
            value = original(p, n, t, before)
            return 1 - value if n == "scan_out" and original(p, "isolation_ack", t) else value
        with patch.object(trace, "integer", corrupt):
            with self.assertRaises(AssertionError):
                check_core(trace, self.prefix)

    def test_compressed_mixed_unknowns_remain_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mixed.vcd"
            path.write_text("$timescale 1ps $end\n$scope module unit $end\n$var wire 8 ! bus $end\n$upscope $end\n$enddefinitions $end\n#0\nb10xx !\n#1\nbx !\n")
            trace = Phase5Trace(path)
            self.assertEqual(trace.value("/unit", "bus", 0), "000010xx")
            self.assertEqual(trace.value("/unit", "bus", 1), "xxxxxxxx")
            with self.assertRaises(AssertionError):
                trace.integer("/unit", "bus", 0)

    def test_saved_preview_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scan.svg"
            prefix = self.prefix
            ack = next(t for t, v in self.isolation.values(prefix, "isolation_ack") if v == "1")
            render_window(self.isolation, prefix, ["clk", "scan_feedback"], ack, ack + 22000, path, "test")
            verify_preview(self.isolation, prefix, path)
            text = path.read_text()
            match = re.search(r"scan_feedback = ([01]),", text)
            self.assertIsNotNone(match)
            wrong = "0" if match[1] == "1" else "1"
            path.write_text(text[:match.start(1)] + wrong + text[match.end(1):])
            with self.assertRaises(AssertionError):
                verify_preview(self.isolation, prefix, path)

if __name__ == "__main__":
    unittest.main(verbosity=2)
