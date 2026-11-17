"""Portable native layouts focused on actual test activity."""
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[2]/"Results/Phase6A"
def clean():
 for p in R.glob("*/waveforms/*.wcfg"):
  tree=ET.parse(p);root=tree.getroot()
  for obj in list(root.findall("wvobject")):
   if obj.get("fp_name","").rsplit("/",1)[-1] in {"current_bit","future1","future2","active_mode"}:
    root.remove(obj) # unused inherited TB aliases; actual generator_state remains visible
  size=root.find("WVObjectSize")
  if size is not None:size.set("size",str(len(root.findall("wvobject"))))
  start=root.find("zoom_setting/ZoomStartTime");end=root.find("zoom_setting/ZoomEndTime")
  a,b=(350,3500) if p.parent.parent.name=="Faults" else (0,1050) if p.stem=="safety" else (0,2600)
  if start is not None:start.set("time",f"{a:.3f} ns")
  if end is not None:end.set("time",f"{b:.3f} ns")
  ET.indent(tree,space="   ");tree.write(p,encoding="UTF-8",xml_declaration=True)
 print("Phase 6A native layouts focused; unused compatibility aliases hidden.")
if __name__=="__main__":clean()
