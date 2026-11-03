# Run with FreeCADCmd (FreeCAD 1.0+). The source is the supplied PMMA CAD assembly.
import FreeCAD as App
import Part,MeshPart
from pathlib import Path
import os,json,hashlib
BASE=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('CYGNO_GAS_OUTPUT_DIR',str(BASE/'generated_gas_boundary')))
OUT.mkdir(parents=True,exist_ok=True)
cad_path=os.environ.get('CYGNO_PMMA_CAD')
if not cad_path:
 raise RuntimeError('Set CYGNO_PMMA_CAD to the source PMMA FCStd file; Geant4 only needs the exported STLs.')
CAD=Path(cad_path).expanduser().resolve()
doc=App.openDocument(str(CAD))
hull=Part.makeBox(660,1190,990,App.Vector(-330,-593.5,-495))
lobes=[]
for name,level,sign in [('Part__Feature1550',369,-1),('Part__Feature1551',-369,1)]:
 obj=doc.getObject(name)
 if obj is None:raise RuntimeError('PMMA CAD object missing: '+name)
 shape=obj.Shape.copy();shape.Placement=obj.getGlobalPlacement()
 faces=[f for f in shape.Faces if abs(f.BoundBox.XMin-level)<1e-4 and abs(f.BoundBox.XMax-level)<1e-4]
 face=max(faces,key=lambda f:f.Area)
 lobes.append(Part.Face(face.OuterWire).extrude(App.Vector(sign*39.001,0,0)))
hull=hull.multiFuse(lobes,1e-4).removeSplitter()
assert hull.isValid() and len(hull.Solids)==1
hull.exportStep(str(OUT/'GasBoundary.step'))
mesh=MeshPart.meshFromShape(Shape=hull,LinearDeflection=.01,AngularDeflection=.1,Relative=False)
points,facets=mesh.Topology
path=OUT/'GasBoundary.stl'
with path.open('w',encoding='ascii',newline='\n') as f:
 f.write('solid GasBoundary\n')
 for ids in facets:
  a,b,c=[points[i] for i in ids];n=(b-a).cross(c-a)
  if n.Length:n.normalize()
  f.write('  facet normal {:.12g} {:.12g} {:.12g}\n    outer loop\n'.format(n.x,n.y,n.z))
  for v in [a,b,c]:f.write('      vertex {:.12g} {:.12g} {:.12g}\n'.format(v.x,v.y,v.z))
  f.write('    endloop\n  endfacet\n')
 f.write('endsolid GasBoundary\n')
(OUT/'GasBoundary.json').write_text(json.dumps({'source':str(CAD),'source_sha256':hashlib.sha256(CAD.read_bytes()).hexdigest(),'triangles':len(facets),'volume_L':hull.Volume/1e6,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'frame':'PMMA CAD; gas in Geant4 is GasBoundary minus PMMA','boundary':'Main walls and cover contours; external fitting bores excluded'},indent=2))
App.closeDocument(doc.Name)

if not App.GuiUp:
 os._exit(0)
