"""Hierarchical VCD reader; retain real unknown values and exact picosecond times."""
from bisect import bisect_left,bisect_right
from pathlib import Path
import re
class Trace:
    def __init__(self,path):
        self.path=Path(path).resolve(); self.signals={}; self.events={}; self.times={}; scopes=[]; now=0
        text=self.path.read_text()
        unit=re.search(r"\$timescale\s+(\d+)\s*(\w+)",text)
        if not unit or unit.groups()!=('1','ps'): raise ValueError("Expected actual XSim 1ps VCD")
        for line in text.splitlines():
            f=line.split()
            if line.startswith('$scope'): scopes.append(f[2])
            elif line.startswith('$upscope'): scopes.pop()
            elif line.startswith('$var'):
                code,name=f[3],f[4]; self.signals['/'+'/'.join(scopes+[name])]=(code,int(f[2])); self.events.setdefault(code,[])
            elif line.startswith('#'): now=int(line[1:])
            elif line and line[0] in '01xXzZuUwWlLhH-' and line[1:] in self.events: self._append(line[1:],now,line[0].lower())
            elif f and f[0].startswith(('b','B')) and len(f)==2 and f[1] in self.events: self._append(f[1],now,f[0][1:].lower())
        self.end=now
        self.times={code:[t for t,v in values] for code,values in self.events.items()}
    def _append(self,code,time,value):
        values=self.events[code]
        if values and values[-1][0]==time: values[-1]=(time,value)
        elif not values or values[-1][1]!=value: values.append((time,value))
    def has(self,prefix,name): return prefix+'/'+name in self.signals
    def values(self,prefix,name):return self.events[self.signals[prefix+'/'+name][0]]
    def value(self,prefix,name,time,before=False):
        code,width=self.signals[prefix+'/'+name]
        values=self.events[code]; times=self.times[code]
        i=(bisect_left(times,time) if before else bisect_right(times,time))-1
        if i<0:return 'x'*width
        v=values[i][1]
        if set(v)<={'0','1'}: return v.zfill(width)
        return v if len(v)==width else v[0]*width
    def integer(self,prefix,name,time,before=False):
        value=self.value(prefix,name,time,before)
        if not set(value)<={'0','1'}: raise AssertionError(f"Unknown {prefix}/{name} at {time}ps: {value}")
        return int(value,2)
