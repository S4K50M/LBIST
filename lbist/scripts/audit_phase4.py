"""Preserve pre-existing sources/results; write a real SHA-256 before/after audit."""
import argparse,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Results/Phase4'
SNAP=OUT/'work/protected_before.json'
def snapshot():
    if SNAP.exists():return
    files={}
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(n in {'.git','.Xil','work','__pycache__'} for n in rel.parts):continue
        if rel.as_posix().startswith('Results/Phase4/'):continue
        files[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    SNAP.parent.mkdir(parents=True,exist_ok=True);SNAP.write_text(json.dumps(files,indent=2))
def audit():
    rows=[]
    for name,prior in json.loads(SNAP.read_text()).items():
        p=ROOT/name;now=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'MISSING'
        rows.append(dict(File=name,BeforeSHA256=prior,AfterSHA256=now,Result='PASS' if now==prior else 'FAIL'))
    with (OUT/'protected_file_integrity.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    assert all(r['Result']=='PASS' for r in rows),[r['File'] for r in rows if r['Result']!='PASS']
    print('Protected files unchanged:',len(rows),'PASS')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',action='store_true');args=p.parse_args()
    if args.snapshot:snapshot()
    else:audit()
