"""Build the final human report only after the complete matrix passes."""
from pathlib import Path
import csv
R=Path(__file__).resolve().parents[2];O=R/"Results/Phase6A"
def read(name):return list(csv.DictReader((O/"reports"/name).open()))
def main():
 verification=read("phase6a_verification_summary.csv")
 assert len(verification)==204 and all(r["Result"]=="PASS" for r in verification)
 faults=read("phase6a_fault_campaign.csv");wtm=read("phase6a_wtm_comparison.csv");gold=read("phase6a_golden_signatures.csv")
 coverage=read("phase6a_fault_coverage.csv");thresholds=read("phase6a_thresholds.csv")
 lines=[];sets=[]
 for cid in range(5):
  c=str(cid);g=next(r for r in gold if r["Config"]==c);w=next(r for r in wtm if r["Config"]==c)
  f=[r for r in faults if r["Config"]==c];assert len(f)==16
  direct=sum(r["DirectDetected"]=="True" for r in f);misr=sum(r["MISRDetected"]=="True" for r in f)
  aliases=sum(r["Aliasing"]=="True" for r in f)
  t=next(r for r in thresholds if r["Config"]==c and r["CoverageTarget"]=="75")
  lines.append(f"| {g['Approach']} | {w['Beta'] if cid>=2 else 'fixed'} | {float(w['MeasuredWTM']):.4f}% | {g['ActualSignature']} | {direct}/16 | {misr}/16 | {aliases} | {t['Patterns']} / {t['Cycles']} |")
  detected=", ".join(r["FaultID"] for r in f if r["MISRDetected"]=="True")
  undetected=", ".join(r["FaultID"] for r in f if r["MISRDetected"]!="True")
  sets.append(f"- {g['Approach']}: detected IDs {detected}; undetected IDs {undetected}.")
 previews=read("waveform_validation.csv");natives=list(O.glob("*/waveforms/*.wcfg"));images=list((O/"Comparison/figures").glob("*.svg"))
 attempt_rows=[]
 for path in (O/"Batch/reports").glob("*.csv"):
  attempt_rows.extend(csv.DictReader(path.open()))
 invalid=sum(r["Result"]!="PASS" for r in attempt_rows)
 text="""# Phase 6A — completed original-16 processor comparison

**204 processor experiments passed independent verification:** twelve fault-free
references and 192 one-fault experiments, covering twelve configurations.
The initial five approaches each have their own reference plus all sixteen
original eligible faults. Seven additional optimizer-selected configurations
also have complete original-16 campaigns.

Two router/safety tests and eight historical/functional regressions pass.
The MISR completion correction prevents aborted, restarted, reset or incomplete
streams from asserting a valid MATCH. Completed faulty streams remain valid.

| Approach | Beta | Measured WTM | Golden = actual | Direct | Final MISR | Aliases | Patterns / cycles to 75% |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
"""+ "\n".join(lines)+"""

Coverage denominators are sixteen faults, not sixteen processor-wide nets.
The universe is eight capture-input sites, each with SA0/SA1. The complete
detected and undetected sets for the initial configurations are:

"""+ "\n".join(sets)+"""

The original Basic campaign reproduces every Phase 5C faulty signature.
First direct mismatch, first prefix-signature mismatch, final detection and
aliasing are recorded separately. Prefix signature coverage is not forced
to be monotonic. Equal signatures do not prove fault-free operation.

## Measurement, matching and time

WTM uses actual verified pre/post scan-FF transitions during SHIFT:
sum(weighted transitions)/(256*64*2080). Input-stage weight is 1 and output
weight is 64. Capture and disposable UNLOAD transitions are excluded.
Serial toggle rate samples the concatenated SHIFT-input subsequence.
All per-fault activity counters are checked against an independent model.
These are switching proxies, not physical power measurements.

The legal optimizer estimates and achieved measurements are both retained.
Swap 20% is INFEASIBLE at L=64; nearest legal beta18 estimates 19.1964%.
It is not presented as an exact matched-target experiment. Direct/Constant
are fixed references. A 0.5 percentage-point tolerance is stated explicitly.
The nominal 10% configurations closely match one another near 9.4–9.5%,
but miss that strict requested-target tolerance. The 15% configurations are
checked for both feasibility and measured matching. Moving beta19 is the
optimizer-selected 20% candidate; the already-tested beta20 is separately
reported as measured calibration, rather than relabeled as optimizer output.
See the matched-comparison CSV for exact ranges and statuses.

Every processor experiment completes at 661.6002 us, under the 100 ms limit.
Runtime counters record 16384 SHIFT + 256 CAPTURE + 16384 UNLOAD = 33024
payload cycles. There are 33080 actual rising edges: 56 overhead edges,
including 3 paused cycles and 53 setup/acknowledgement/exit/reset/restart
edges. The completion marker is another 200 ps after the final falling edge.
Coverage-threshold cycles come from actual measured prefixes; all campaigns
still execute 256 patterns, so threshold results are not early-stop run claims.

## Safety and scheduling

phase6a_controlled_misr is the port-compatible safe replacement for the
historical lbist_controlled_misr. The old Phase 5B interfaces/results remain
unchanged for reproduction. Validity now requires final state, successful
controller completion, complete capture/response/pattern counts and no
sticky stream error. The actual UNLOAD scan-out bit drives the MISR.

Swap/Moving each use separate SHIFT and UNLOAD scheduling instances of the
unchanged Phase 3 controller. Both use schedule p, then the next SHIFT uses
p+1. This preserves Swap alternation and Moving progression through the
non-overlapped unload interval. LFSR advancement remains once per SHIFT
or UNLOAD edge; CAPTURE and pause never advance it.

The standalone router uses the actual IF/RF bank and checks 36 logical
patterns per approach, every FF, mode, feedback and wrap, plus invalid codes.
All processor experiments use the real isolated core_scan_fault. Each DUT
has its own state, clock, memory, generator, controller, scan bank and MISR.
Some experiments share an XSim run as isolated replicas to reduce compilation
overhead. Their original report records are split by actual instance hierarchy
and independently rechecked; no modeled processor replaces a DUT.

"""+f"""There were {invalid} rejected native batch attempts. The incomplete
sixteen-replica Moving attempt ended with an XSim/Tcl exception and supplied
no accepted fault outcomes. It was rerun with smaller groups; the default
batch limit is now eight. All 204 logical outcomes above are complete and
valid. Raw attempts remain archived separately.

## Evidence and synthesis

{len(previews)} SVG waveform previews ({sum(int(r['IntervalsChecked']) for r in previews)}
plotted intervals) were verified against VCD values and transition boundaries.
There are {len(natives)} portable WCFG layouts and {len(images)} comparison figures.
Native WDB/VCD remain local and can be regenerated. The separate native audit
reopens the WDB/WCFG pairs. Safety VCD includes vector aliases because XSim
does not export natural-number signals. Unused inherited TB aliases are
hidden in layouts; actual LFSR state remains visible.

"""+"""Synthesis at xc7a35tcpg236-1 reports:

| Boundary | FF | LUT | Latches |
| --- | ---: | ---: | ---: |
| Safe analyzer | 57 | 84 | 0 |
| Five-approach router, including LFSR | 58 | 94 | 0 |
| Safe controller + analyzer | 80 | 116 | 0 |

Compared with the same historical controller/analyzer boundary (39 FF,
61 LUT), completion safety adds 41 FF and 55 LUT. Fault mux and processor
debug-probe overhead are outside these measurements. Full processor/router
synthesis, constrained timing and physical power are not claimed.

Reports:

- [All verified experiments](reports/phase6a_verification_summary.csv).
- [Fault outcomes](reports/phase6a_fault_campaign.csv),
  [inventory and activation paths](reports/phase6a_fault_inventory.csv).
- [Coverage checkpoints](reports/phase6a_fault_coverage.csv),
  [latency](reports/phase6a_detection_latency.csv),
  [aliases](reports/phase6a_misr_aliasing.csv).
- [Golden/actual signatures](reports/phase6a_golden_signatures.csv),
  [WTM](reports/phase6a_wtm_comparison.csv),
  [target feasibility](reports/phase6a_feasibility.csv),
  [measured matches](reports/phase6a_matched_comparisons.csv).
- [Cycles and overhead](reports/phase6a_test_cycles.csv),
  [coverage thresholds](reports/phase6a_thresholds.csv).
- [Historical/functional regressions](reports/phase6a_regressions.csv),
  [VCD/SVG checks](reports/waveform_validation.csv),
  [actual event timestamps](reports/phase6a_waveform_events.csv).
- [Synthesis](reports/synthesis.csv),
  [preservation hashes](reports/protected_integrity.csv).

Native layouts: Router/waveforms and Faults/waveforms.
Graphs: Comparison/figures. Native/raw/compile/elaboration logs are retained
under Router, Faults, Regression and Batch. Batch is a verification harness
only, not extra hardware chains in the processor.

## Reproduction and limits

Use Python 3.10+ with matplotlib and Vivado/XSim 2025.1.1:

~~~powershell
python lbist/scripts/build_phase6a.py
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source lbist/scripts/run_all_phase6a.tcl
& 'E:/2025.1.1/Vivado/bin/vivado.bat' -mode batch -source lbist/scripts/synth_phase6a.tcl
~~~

PHASE6A_NATIVE_ROOT may point to a temporary directory outside OneDrive for
native build caches; reports remain in this tree. Separate requested runners
and the batch/synthesis/audit helpers are supplied. The native watchdog is
20 ms per run; there is no wall-clock campaign limit.

Added RTL comprises the router, safe analyzer and safe controller wrapper.
New processor/router/safety/batch benches, independent Python models/analysis,
Tcl runners, documentation and result artifacts are enumerated by the source
manifest. Previous Phase 1–5C files are protected against SHA-256 changes.

The verified boundary and reset-only exit remain those of Phase 5A. External
fabric must be idle before acknowledged isolation. Autonomous external device
state is outside the core boundary. Instruction capture still uses the held
ROM instruction, so some polarities are unexcited. Expanded fault inventories
and varied instruction stimulus are explicitly deferred second-stage work.
The remaining 656 pipeline scan bits are unchanged. These results do not
establish full MIPS32 fault coverage or physical power savings.

[Detailed protocol, audit and measurement definitions](../../docs/phase6a_design.md).
"""
 (O/"README.md").write_text(text,encoding="utf-8")
 print("Final Phase 6A report written from verified CSV data.")
if __name__=="__main__":main()
