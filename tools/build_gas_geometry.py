from pathlib import Path
import sys,json,hashlib,argparse
p=argparse.ArgumentParser(description='Build N66 clearance and an optional visualization-only PMMA gas envelope.')
p.add_argument('--geometry-dir',type=Path,default=Path(__file__).resolve().parents[1]/'cygno04_v4_ASCII')
p.add_argument('--output-dir',type=Path,required=True)
p.add_argument('--source-n66',type=Path)
p.add_argument('--cut-n66',action='store_true',help='Cut field-cage clearance into the supplied N66 model.')
p.add_argument('--skip-preview',action='store_true',help='Omit the optional, visualization-only gas-envelope mesh.')
a=p.parse_args()
ROOT=a.output_dir.resolve();ROOT.mkdir(parents=True,exist_ok=True)
import numpy as np
import trimesh
import manifold3d as md

GEOM=a.geometry_dir.resolve()
report={'status':'starting','inputs':{},'outputs':{}}
def save():(ROOT/'mesh_build_report.json').write_text(json.dumps(report,indent=2))
def load(path,label):
    data=path.read_bytes();report['inputs'][label]={'path':str(path),'sha256':hashlib.sha256(data).hexdigest()}
    triangles=np.array([s.split()[1:] for s in data.splitlines() if s.lstrip().startswith(b'vertex ')],float).reshape(-1,3,3)
    if label=='N66' and a.cut_n66:
        # Remove only the 61 nm STL-rounding intrusion into the lower PMMA wall.
        mask=triangles[:,:,2]==-475.
        report['lower_N66_rounding_records']=int(mask.sum())
        triangles[:,:,2][mask]=-474.999939
    v,f=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
    f=f.reshape(-1,3)
    m=md.Manifold(md.Mesh64(np.ascontiguousarray(v),np.ascontiguousarray(f,dtype=np.uint64)))
    assert m.status()==md.Error.NoError,(label,m.status())
    print('Loaded',label,'triangles',m.num_tri(),'volume_mm3',m.volume(),flush=True)
    save();return m
def write(m,name,frame):
    # Geant4 merges coincident vertices at its surface tolerance. Remove
    # Boolean slivers first so that this cannot collapse edges on import.
    m=m.as_original().simplify(1e-5)
    assert m.status()==md.Error.NoError,(name,m.status())
    mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties)[:,:3];f=np.asarray(mesh.tri_verts)
    check=trimesh.Trimesh(v,f,process=False)
    assert check.is_watertight and check.is_winding_consistent,name
    path=ROOT/(name+'.stl')
    t=v[f];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(n,axis=1)
    assert (length>1e-18).all(),name
    n/=length[:,None]
    with path.open('w') as out:
        out.write('solid '+name+'\n')
        for tri,normal in zip(t,n):
            out.write(' facet normal {:.15g} {:.15g} {:.15g}\n  outer loop\n'.format(*normal))
            for p in tri:out.write('   vertex {:.15g} {:.15g} {:.15g}\n'.format(*p))
            out.write('  endloop\n endfacet\n')
        out.write('endsolid '+name+'\n')
    serialized=trimesh.load_mesh(path,process=True)
    assert serialized.is_watertight and serialized.is_winding_consistent,name
    report['outputs'][name]={'triangles':len(f),'vertices':len(v),'volume_L':m.volume()/1e6,'watertight':True,'winding_consistent':True,'frame':frame,'bounds_mm':[v.min(0).tolist(),v.max(0).tolist()],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    print('Wrote',name,report['outputs'][name],flush=True);save()

save()
n=load(a.source_n66 or GEOM/'N66.stl','N66');fc=load(GEOM/'FieldCage.stl','FieldCage')
overlap=n^fc
report['N66_field_cage_intersection_mm3']=overlap.volume()
fixed=(n-fc).as_original().simplify(1e-5) if a.cut_n66 else n
report['N66_volume_removed_mm3']=n.volume()-fixed.volume()
if a.cut_n66:write(fixed,'N66_clearance','legacy CAD: Rx(-90deg), T=(470,0,0) mm')
boundary=load(GEOM/'GasBoundary.stl','GasBoundary');pmma=load(GEOM/'PMMA.stl','PMMA')
if not a.skip_preview:
    gas=boundary-pmma
    write(gas,'GasEnvelope_preview','PMMA CAD: visualization only; Geant4 uses direct GasBoundary minus PMMA subtraction')
report['status']='ready';save()
