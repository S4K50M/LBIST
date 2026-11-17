"""Real-log reports and independent, transition-level Phase 5A verification."""
import argparse
import csv
import hashlib
import re
import struct
from pathlib import Path
from phase5a_trace import Phase5Trace, verify_preview
from render_waveform_previews import render_window

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Results/Phase5A"
PLAN = [
    ("Controller", "controller_L1", "tb_lbist_test_controller"),
    ("Controller", "controller_L2", "tb_lbist_test_controller"),
    ("Controller", "controller_L64", "tb_lbist_test_controller"),
    ("Isolation", "core_isolation", "tb_core_scan_isolation"),
    ("ShiftCapture", "core_shift_capture_P256", "tb_core_scan_shift_capture"),
    ("ShiftCapture", "core_shift_capture_P16", "tb_core_scan_shift_capture"),
    ("Isolation", "functional_lwsw", "tb_core_scan_test_regression"),
    ("Isolation", "functional_stalls", "tb_core_scan_test_regression"),
]

def write(name, rows):
    with (OUT / name).open("w", newline="") as f:
        fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else ["Result"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def collect(require_all=False):
    status, isolation, sequence, captures, functional = [], [], [], [], []
    expected_output = [format(v & 0xffffffff, "08x") for v in range(-10, 0)]
    for group, tag, top in PLAN:
        file = OUT / group / "reports" / (tag + ".csv")
        row = dict(Case=tag, Testbench=top, Group=group, Result="NOT_RUN", CompletionTime="NA", Capture=0, WDBBytes=0)
        if file.exists():
            row.update(next(csv.DictReader(file.open())))
        status.append(row)
        if row["Result"] != "PASS":
            continue
        log = (OUT / group / "logs" / (tag + ".log")).read_text()
        duration = int(row["CompletionTime"].split()[0])
        assert duration < 100_000_000_000
        assert "[FAIL]" not in log and "ERROR:" not in log and "Fatal:" not in log
        if tag.startswith("functional"):
            assert "cMIPS BREAKPOINT at PC=00000038" in log and log.count("Failure:") == 1
            assert re.findall(r"(?im)^([0-9a-f]{8})\s*$", log) == expected_output
            samples = list(csv.DictReader((OUT / group / "reports" / (tag + "_samples.csv")).open()))
            assert len(samples) >= 100 and all(v["Result"] == "PASS" for v in samples)
            assert duration == (1730000 if tag == "functional_stalls" else 1670000)
            if tag == "functional_stalls":
                assert any(v["IF_RF_ld"] == "1" for v in samples)
            functional.append(dict(Case=tag, PipelineSamples=len(samples), OutputWords=10, CompletionNS=duration // 1000, Result="PASS"))
            continue
        assert "[TB_COMPLETE] " + top in log and "Failure:" not in log
        values = re.findall(r"\[SEQUENCE\] ([0-9]+),([0-9]+),([0-9]+),([0-9]+)", log)
        assert len(values) == 1
        shifts, cycles, unloads, patterns = map(int, values[0])
        length = int(tag.rsplit("L", 1)[1]) if group == "Controller" else 64
        assert shifts == unloads == patterns * length and cycles == patterns
        sequence.append(dict(Case=tag, ChainLength=length, ShiftEdges=shifts, CaptureEdges=cycles, UnloadEdges=unloads,
                             Patterns=patterns, EnabledScanEdges=shifts + unloads,
                             TotalGeneratorAdvances="NA" if group == "Controller" else shifts + unloads,
                             CompletionPS=duration, Result="PASS"))
        if group == "Controller":
            continue
        values = re.findall(r"\[ISOLATION\] ([0-9,]+)", log)
        assert len(values) == 1
        width, changes, mem_attempt, mem_actual, reg_attempt, reg_actual = map(int, values[0].split(","))
        assert width > 4000 and changes == mem_actual == reg_actual == 0
        assert mem_attempt > 0 if tag.endswith("P16") else reg_attempt > 0
        isolation.append(dict(Case=tag, ObservedBits=width, ProtectedStateChanges=changes,
                              MemoryWriteAttempts=mem_attempt, ActualMemoryWrites=mem_actual,
                              RegisterWriteAttempts=reg_attempt, ActualRegisterWrites=reg_actual,
                              IRQ_NMI_BusErrors="injected; masked and state held", Exit="reset only", Result="PASS"))
        results = re.findall(r"\[CAPTURE\] ([0-9]+),([0-9a-fA-F]+),([0-9a-fA-F]+),([0-9a-fA-F]+),PASS", log)
        assert len(results) == patterns
        for index, actual, golden, unloaded in results:
            assert len(actual) == 16 and actual.lower() == golden.lower() == unloaded.lower()
            captures.append(dict(Case=tag, Pattern=int(index), Captured=actual.upper(), Expected=golden.upper(),
                                 SerialUnloaded=unloaded.upper(), Result="PASS"))
    write("phase5a_verification_summary.csv", status)
    write("phase5a_isolation_summary.csv", isolation)
    write("phase5a_scan_sequence.csv", sequence)
    write("phase5a_capture_unload.csv", captures)
    write("phase5a_functional_regression.csv", functional)
    if require_all:
        assert len(status) == 8 and all(r["Result"] == "PASS" for r in status)
        assert len(isolation) == 3 and len(captures) == 280 and len(functional) == 2
    print("Collected", sum(r["Result"] == "PASS" for r in status), "PASS / 8 planned cases;", len(captures), "real capture/unload records.")
    return status

def check_controller(trace, prefix, length, patterns):
    read = lambda n, t, pre=False: trace.integer(prefix, n, t, pre)
    state = position = completed = error = 0
    shifts = captures = unloads = 0
    clocks = [t for t, v in trace.values(prefix, "clk") if v == "1"]
    resets = [t for t, v in trace.values(prefix, "rst") if v == "0"]
    for t in sorted(set(clocks + resets)):
        if not read("rst", t):
            state = position = completed = error = 0
            assert read("state", t) == state and read("shift_count_v", t) == 0
            continue
        before = state
        start, pause, abort, ack, ready = [read(n, t, True) for n in ["start", "pause", "abort_test", "ack", "ready"]]
        assert read("state", t, True) == state and read("shift_count_v", t, True) == position
        assert read("se", t, True) == int(state in [2, 4] and not pause and not abort and not start)
        assert read("ce", t, True) == int(state == 3 and not pause and not abort and not start and ready)
        if state in [2, 4] and not pause and not abort and not start:
            if state == 2: shifts += 1
            else: unloads += 1
        if state == 3 and not pause and not abort and not start and ready:
            captures += 1
        pulse = 0
        if state not in [0, 5] and (abort or start):
            state = 5
            error = 1
        elif not pause:
            if state == 0 and start: state = 1
            elif state == 1 and ack: state = 2
            elif state in [2, 4]:
                position += 1
                if position == length:
                    position = 0
                    if state == 2: state = 3
                    else:
                        completed += 1
                        pulse = 1
                        state = 5 if completed == patterns else 2
            elif state == 3 and ready: state = 4
        assert read("state", t) == state and read("shift_count_v", t) == position
        assert read("pattern_index", t) == completed and read("pd", t) == pulse
        assert read("error_status", t) == error
    assert shifts == patterns * length + 1 and unloads == patterns * length and captures == patterns
    return dict(Kind="Controller", CheckedEdges=len(clocks), Shifts=shifts, Captures=captures,
                Unloads=unloads, DirectedResetPartialShifts=1, Result="PASS")

def check_core(trace, prefix):
    read = lambda n, t, pre=False: trace.integer(prefix, n, t, pre)
    words = struct.unpack("<" + "I" * ((ROOT / "cMIPS/prog.bin").stat().st_size // 4),
                          (ROOT / "cMIPS/prog.bin").read_bytes())
    protected = None
    held_pc = None
    state = 0xAAAA
    ordinal = shifts = captures = unloads = 0
    capture_response = None
    clocks = [t for t, v in trace.values(prefix, "clk") if v == "1"]
    resets = [t for t, v in trace.values(prefix, "rst") if v == "0"]
    for t in sorted(set(clocks + resets)):
        if read("rst", t) == 0:
            assert read("scan_state", t) == 0
            protected = held_pc = None
            state = 0xAAAA
            ordinal = 0
            continue
        if read("isolation_ack", t, True) == 0:
            continue
        if protected is None:
            protected = trace.value(prefix, "protected_state", t, True)
            held_pc = read("pc_observe", t, True)
        assert trace.value(prefix, "protected_state", t, True) == protected
        assert read("pc_observe", t) == held_pc
        old = read("scan_state", t, True)
        assert read("scan_feedback", t, True) == old & 1
        assert read("scan_out", t, True) == old >> 63
        assert read("generator_state", t, True) == state
        phase = read("test_phase", t, True)
        shift = read("scan_enable", t, True)
        capture = read("capture_enable", t, True)
        mode = 3 if 22 <= ordinal % 64 < 42 else 0
        assert read("mode_select", t, True) == mode
        expected = old
        if shift:
            assert phase in [2, 4] and not capture
            assert read("isolation_ack", t, True) == 1
            for name in ["phi1_sync", "phi2_sync", "ack_sync"]:
                assert trace.integer(prefix + "/dut", name, t, True) & 2
            bits = [(state >> k) & 1 for k in range(3)]
            for name, value in zip(["current_bit", "future1", "future2"], bits):
                assert read(name, t, True) == value
            bit = bits[0] if mode == 3 or bits[0] == bits[1] == bits[2] else old & 1
            assert read("scan_in", t, True) == bit
            if phase == 4:
                count = read("shift_count_v", t, True)
                assert capture_response is not None
                assert read("scan_out", t, True) == (capture_response >> (63 - count)) & 1
                unloads += 1
            else:
                shifts += 1
            expected = ((old << 1) | bit) & ((1 << 64) - 1)
            feedback = sum((state >> k) & 1 for k in [0, 4, 13, 15]) % 2
            state = (state >> 1) | (feedback << 15)
            ordinal += 1
        elif capture:
            assert phase == 3 and read("capture_ready", t, True)
            instruction_address = held_pc & ~3
            instruction = words[instruction_address // 4] if instruction_address // 4 < len(words) else 0
            operand = (old >> 32) & 0xfffffffc
            assert trace.integer(prefix + "/dut", "increment_operand", t, True) == operand
            expected = (((operand + 4) & 0xffffffff) << 32) | instruction
            capture_response = expected
            captures += 1
        assert read("scan_state", t) == expected, (t, "every scan bit and genuine capture")
        assert read("generator_state", t) == state
        assert trace.value(prefix, "protected_state", t) == protected
    assert captures > 0 and shifts == unloads == captures * 64
    # Verify the snapshot across ALL phases and all actual probe transitions.
    protected = None
    samples = sorted(set([t for name in ["clk", "protected_state", "isolation_ack", "rst"] for t, v in trace.values(prefix, name)]))
    for t in samples:
        if not read("rst", t) or not read("isolation_ack", t):
            protected = None
            continue
        value = trace.value(prefix, "protected_state", t)
        if protected is None: protected = value
        else: assert value == protected, (t, "protected-state transition")
        assert read("i_aval", t) == read("d_aval", t) == read("wr", t) == 1
        assert read("bsel", t) == 0 and read("register_write_actual", t) == 0
    return dict(Kind="Processor", CheckedEdges=len(clocks), Shifts=shifts, Captures=captures, Unloads=unloads, Result="PASS")

def waves():
    summaries, previews, events, provenance = [], [], [], []
    for group, tag, top in [PLAN[2], PLAN[3], PLAN[4], PLAN[5]]:
        folder = OUT / group / "waveforms"
        trace = Phase5Trace(folder / (tag + ".vcd"))
        prefix = "/" + top + ("/engine" if group != "Controller" else "")
        report = check_controller(trace, prefix, 64, 256) if group == "Controller" else check_core(trace, prefix)
        summaries.append(dict(Case=tag, **report))
        phase_name = "state" if group == "Controller" else "test_phase"
        phases = trace.values(prefix, phase_name)
        marks = {}
        for t, value in phases:
            code = int(value, 2)
            if t and code in [1, 2, 3, 4, 5] and code not in marks:
                marks[code] = t
        first_shift = next(t for t, v in trace.values(prefix, "clk") if v == "1" and t > marks[2])
        chosen = [(marks[n], label) for n, label in [(1, "test_entry"), (3, "shift_to_capture"),
                                                   (4, "capture_to_unload"), (5, "test_completion")] if n in marks]
        chosen.append((first_shift, "first_shift"))
        if group != "Controller":
            for a, b, label in [(0, 3, "first_plpf_switch"), (3, 0, "second_plpf_switch")]:
                found = [t for t, v in trace.values(prefix, "mode_select") if t and
                         trace.integer(prefix, "mode_select", t, True) == a and trace.integer(prefix, "mode_select", t) == b]
                assert found
                chosen.append((found[0], label))
            response_edges = [t for t, v in trace.values(prefix, "clk") if v == "1" and t > marks[4]
                              and trace.integer(prefix, "test_phase", t, True) == 4
                              and trace.integer(prefix, "scan_enable", t, True) == 1]
            assert response_edges
            chosen += [(marks[3], "last_shift"), (marks[4], "functional_capture"), (response_edges[0], "scan_out_response")]
            increments = [t for t, v in trace.values(prefix, "pattern_index") if int(v, 2) == 1]
            assert increments
            chosen.append((increments[0], "pattern_increment"))
            resets = [t for t, v in trace.values(prefix, "rst") if v == "0" and t > marks[5]]
            assert resets
            chosen.append((resets[0], "reset_only_exit"))
            released = [t for t, v in trace.values(prefix, "rst") if v == "1" and t > resets[0]]
            assert released
            restart = next(t for t, v in trace.values(prefix, "clk") if v == "1" and t > released[0])
            chosen.append((restart, "functional_restart"))
            blocked = [t for t, v in trace.values(prefix, "exit_attempt") if v == "1"]
            assert blocked and trace.integer(prefix, "isolation_ack", blocked[0]) == 1
            chosen.append((blocked[0], "exit_requires_reset"))
            ack = next(t for t, v in trace.values(prefix, "isolation_ack") if v == "1")
            chosen.append((ack, "all_clock_phases_held"))
            names = ["clk", "rst", "test_mode", "isolation_ack", "test_phase", "scan_enable", "capture_enable",
                     "shift_count_v", "pattern_index", "scan_state", "pc_observe", "scan_in", "scan_out", "scan_feedback",
                     "mode_select", "generator_state", "protected_equal", "wr", "d_aval", "register_write_actual"]
        else:
            names = ["clk", "rst", "start", "ack", "state", "tm", "se", "ce", "pause", "shift_count_v", "pattern_index", "pd", "done", "error_status"]
        for t, label in chosen:
            image = folder / (tag + "_" + label + ".svg")
            render_window(trace, prefix, names, max(0, t - 10000), min(trace.end, t + 12000),
                          image, tag + " - " + label.replace("_", " "), [(t, label.replace("_", " ") + " (captured event)")])
            previews.append(verify_preview(trace, prefix, image))
            events.append(dict(Case=tag, Event=label, TimePS=t, Result="PASS"))
        image = folder / (tag + "_overview.svg")
        render_window(trace, prefix, names, 0, min(trace.end, marks.get(4, 100000) + 40000),
                      image, tag + " - captured overview")
        previews.append(verify_preview(trace, prefix, image))
        if group != "Controller":
            for label, fields in [
                ("protected_state_hold", ["clk", "isolation_ack", "test_phase", "pc_observe", "protected_state", "protected_equal"]),
                ("write_suppression", ["clk", "isolation_ack", "scan_enable", "memory_write_attempt", "wr", "d_aval",
                                       "register_write_attempt", "register_write_actual"]),
            ]:
                t = first_shift
                image = folder / (tag + "_" + label + ".svg")
                render_window(trace, prefix, fields, max(0, t - 10000), min(trace.end, t + 12000),
                              image, tag + " - " + label.replace("_", " ") + " (legacy unreset bits remain X)")
                previews.append(verify_preview(trace, prefix, image))
            t = marks[4]
            image = folder / (tag + "_real_increment_capture.svg")
            render_window(trace, prefix + "/dut",
                          ["clk", "legal_capture", "increment_operand", "PCincd", "capture_word", "RF_PCincd", "RF_instruction"],
                          max(0, t - 10000), min(trace.end, t + 12000), image,
                          tag + " - actual PC increment adder and scan capture", [(t, "one capture edge")])
            previews.append(verify_preview(trace, prefix + "/dut", image))
        provenance.append(dict(Case=tag, VCD=trace.path.relative_to(ROOT).as_posix(),
                               SHA256=hashlib.sha256(trace.path.read_bytes()).hexdigest(), EndPS=trace.end))
        print("PHASE 5A CAPTURED BEHAVIOR: PASS --", tag)
    write("phase5a_waveform_validation.csv", summaries)
    write("phase5a_preview_validation.csv", previews)
    write("phase5a_waveform_events.csv", events)
    write("phase5a_waveform_sources.csv", provenance)
    print("Verified", len(previews), "saved waveform SVGs against actual captured transitions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-all", action="store_true")
    parser.add_argument("--waves", action="store_true")
    options = parser.parse_args()
    collect(options.require_all)
    if options.waves:
        waves()
