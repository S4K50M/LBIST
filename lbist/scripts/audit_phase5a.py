"""Hash all protected previous-phase files without changing them."""
from pathlib import Path
import argparse
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Results/Phase5A"
SNAPSHOT = OUT / "work/protected_before.json"
def snapshot():
    if SNAPSHOT.exists():
        return
    files = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(v in {".git", ".Xil", "work", "__pycache__"} for v in rel.parts):
            continue
        if rel.as_posix().startswith("Results/Phase5A/"):
            continue
        files[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(files, indent=2))
def audit():
    rows = []
    for name, before in json.loads(SNAPSHOT.read_text()).items():
        path = ROOT / name
        after = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"
        rows.append(dict(File=name, BeforeSHA256=before, AfterSHA256=after, Result="PASS" if before == after else "FAIL"))
    with (OUT / "protected_file_integrity.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert all(v["Result"] == "PASS" for v in rows), [v["File"] for v in rows if v["Result"] != "PASS"]
    print("Previous-phase protected files unchanged:", len(rows), "PASS")
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", action="store_true")
    if p.parse_args().snapshot: snapshot()
    else: audit()
