"""Phase 5 VCD reader: correctly extend compressed buses with mixed X/Z bits."""
from bisect import bisect_left, bisect_right
from phase3_trace import Trace
from fractions import Fraction
import re
import xml.etree.ElementTree as ET
from pathlib import Path

class Phase5Trace(Trace):
    def value(self, prefix, name, time, before=False):
        code, width = self.signals[prefix + "/" + name]
        index = (bisect_left(self.times[code], time) if before else bisect_right(self.times[code], time)) - 1
        if index < 0:
            return "x" * width
        value = self.events[code][index][1]
        fill = value[0] if value[0] in "xzuwlh-" else "0"
        return value.rjust(width, fill)

def verify_preview(trace, prefix, path):
    """Check saved interval values, including mixed known/unknown VCD buses."""
    root = Path(__file__).resolve().parents[2]
    pattern = re.compile(r"^(.+)/([^/ ]+) = ([01xuzwhl-]+), ([0-9.]+)\.\.([0-9.]+) ns$", re.I)
    count = 0
    for item in ET.parse(path).getroot().iter():
        if item.tag.rsplit("}", 1)[-1] != "title":
            continue
        match = pattern.fullmatch(item.text or "")
        assert match, path
        hierarchy, name, value, start, end = match.groups()
        assert hierarchy == prefix
        start, end = int(Fraction(start) * 1000), int(Fraction(end) * 1000)
        assert 0 <= start < end <= trace.end
        code, width = trace.signals[prefix + "/" + name]
        fill = value[0] if value[0] in "xzuwlh-" else "0"
        assert trace.value(prefix, name, start) == value.rjust(width, fill), (path, name, start)
        following = bisect_right(trace.times[code], start)
        assert following == len(trace.times[code]) or trace.times[code][following] >= end
        count += 1
    assert count > 0
    file = Path(path)
    return dict(File=file.relative_to(root).as_posix() if file.is_relative_to(root) else str(file),
                IntervalsChecked=count, Result="PASS")
