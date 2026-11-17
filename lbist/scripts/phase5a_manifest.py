"""Record source and original input-image SHA-256 provenance for Phase 5A."""
from pathlib import Path
import csv
import hashlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Results/Phase5A"


def record(name, paths):
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["File", "Bytes", "SHA256"])
        writer.writeheader()
        for path in sorted(set(paths)):
            content = path.read_bytes()
            writer.writerow(dict(File=path.relative_to(ROOT).as_posix(),
                                 Bytes=len(content), SHA256=hashlib.sha256(content).hexdigest()))


def main():
    paths = list((ROOT / "lbist/core_scan/phase5a").glob("*.vhd"))
    paths += [ROOT / "lbist/core_scan/core_scan_test.vhd"]
    paths += [ROOT / "lbist/rtl" / name for name in
              ["lbist_test_controller.vhd", "phase5a_ifrf_subsystem.vhd"]]
    for pattern in ["*phase5a*.py", "*phase5a*.tcl", "run_test_controller.tcl",
                    "run_core_scan_isolation.tcl", "run_core_shift_capture.tcl"]:
        paths += list((ROOT / "lbist/scripts").glob(pattern))
    for name in ["phase5a_rom_pkg", "phase5a_processor_check", "tb_lbist_test_controller",
                 "tb_core_scan_isolation", "tb_core_scan_shift_capture", "tb_core_scan_test_regression"]:
        paths.append(ROOT / "lbist/tb" / (name + ".vhd"))
    paths += list((ROOT / "docs").glob("phase5a*.md")) + [OUT / "README.md"]
    record("phase5a_source_manifest.csv", paths)
    record("phase5a_input_images.csv", [ROOT / "cMIPS" / name for name in
                                      ["prog.bin", "data.bin", "input.data", "serial.inp"]])
    print("Phase 5A source/image SHA-256 manifests written.")


if __name__ == "__main__":
    main()
