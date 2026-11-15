"""Render compact SVG previews from real XSim VCD captures (standard library)."""
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def render(path):
    declarations, traces = {}, {}
    now = 0
    for line in path.read_text().splitlines():
        fields = line.split()
        if line.startswith('$var'):
            _, _, width, code, name, *_ = fields
            declarations[code] = (name, int(width))
            traces[code] = []
        elif line.startswith('#'):
            now = int(line[1:])
        elif fields and fields[0].startswith(('b', 'B')) and len(fields)==2:
            value, code = fields[0][1:].lower(), fields[1]
            if code in traces: traces[code].append((now, value))
        elif line and line[0] in '01xXzZ' and line[1:] in traces:
            traces[line[1:]].append((now, line[0].lower()))
    selected = [c for c in declarations if declarations[c][0] in
                {'clk','rst','en','scan_enable','mode','active','state','c','f1','f2','past','y','scan_in','done','chain','bit_out'}]
    selected.sort(key=lambda c: ['clk','rst','en','scan_enable','mode','active','done','state','c','f1','f2','past','y','scan_in','chain','bit_out'].index(declarations[c][0]))
    width, height, left, span = 1400, 120+42*len(selected), 140, 1200
    end = 300000  # ps; XSim captures use an explicit 1ps timescale.
    assert '$timescale\n  1ps' in path.read_text().replace('\r','')
    x = lambda time: left+span*time/end
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="20" y="27" font-family="sans-serif" font-size="20">{escape(path.stem)}</text>',
           '<text x="20" y="49" font-family="sans-serif" font-size="12" fill="#52606d">Actual XSim VCD data; first 300 ns. Full trace and signal inspection: matching WDB + WCFG.</text>']
    for tick in range(0,301,20):
        at=x(tick*1000)
        parts += [f'<line x1="{at}" x2="{at}" y1="70" y2="{height-25}" stroke="#e2e8f0"/>',
                  f'<text x="{at}" y="68" text-anchor="middle" font-size="11" font-family="sans-serif">{tick} ns</text>']
    for row,code in enumerate(selected):
        name,bits=declarations[code]; y=96+42*row
        parts.append(f'<text x="12" y="{y+5}" font-family="monospace" font-size="13">{escape(name)}</text>')
        events=[]
        for time,value in traces[code]:
            if time>end: break
            if events and events[-1][0]==time: events[-1]=(time,value)
            elif not events or events[-1][1]!=value: events.append((time,value))
        for index,(time,value) in enumerate(events):
            stop=events[index+1][0] if index+1<len(events) else end
            a,b=x(time),x(stop)
            title=escape(f'{name}={value}, {time/1000:g}..{stop/1000:g} ns')
            if bits==1:
                level=y-11 if value=='1' else y+11 if value=='0' else y
                color='#bf3030' if value in {'x','z'} else '#116b60'
                parts.append(f'<path d="M {a} {level} H {b}" stroke="{color}" fill="none" stroke-width="1.5"><title>{title}</title></path>')
                if index and events[index-1][1]!=value:
                    old=events[index-1][1]; old_level=y-11 if old=='1' else y+11 if old=='0' else y
                    parts.append(f'<path d="M {a} {old_level} V {level}" stroke="{color}"/>')
            else:
                mode=name in {'mode','active'}
                fill=('#e0f2e9' if value=='0' else '#fff0cc') if mode else '#edf3ff'
                label=value.zfill(bits) if mode else (hex(int(value,2))[2:].upper() if all(c in '01' for c in value) else value)
                parts.append(f'<rect x="{a}" y="{y-13}" width="{max(0,b-a)}" height="26" fill="{fill}" stroke="#52739e" stroke-width="0.7"><title>{title}</title></rect>')
                if b-a>max(24,8*len(label)):
                    parts.append(f'<text x="{(a+b)/2}" y="{y+4}" text-anchor="middle" font-family="monospace" font-size="12">{escape(label)}</text>')
    parts.append('</svg>')
    path.with_suffix('.svg').write_text('\n'.join(parts))

if __name__=='__main__':
    paths=list((REPO/'Results/Phase2/waveforms').glob('*.vcd'))+list((REPO/'Results/Phase3/Basic/waveforms').glob('*.vcd'))
    for path in paths: render(path)
    print(f'Rendered {len(paths)} waveform previews from VCD data.')
