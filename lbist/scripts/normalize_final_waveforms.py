"""Hide inherited unconnected TB aliases and focus new layouts on capture."""
from pathlib import Path
import argparse,re
R=Path(__file__).resolve().parents[2];base=R/'Results/Final/Verification'
parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path)
args=parser.parse_args()
paths=args.folder.glob('*.wcfg') if args.folder else base.rglob('*.wcfg')
for p in paths:
    assert p.resolve().is_relative_to(base.resolve())
    text=p.read_text()
    if not any(n in text for n in ['tb_final_activity','tb_phase6a_fault_comparison']):continue
    text=re.sub(r'\s*<wvobject fp_name="[^"]+/(?:current_bit|future1|future2|active_mode)".*?</wvobject>','',text,flags=re.S)
    text=re.sub(r'<WVObjectSize size="\d+"',f'<WVObjectSize size="{text.count("<wvobject ")}"',text)
    text=re.sub(r'<ZoomStartTime time="[^"]+"','<ZoomStartTime time="1800.000 ns"',text)
    text=re.sub(r'<ZoomEndTime time="[^"]+"','<ZoomEndTime time="2150.000 ns"',text)
    p.write_text(text)
print('Normalized final layouts; actual waveform data unchanged.')
