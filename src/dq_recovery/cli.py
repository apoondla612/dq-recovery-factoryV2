from __future__ import annotations
import argparse, json
from pathlib import Path
from .recovery import recover
from .utils import register_export

def main(argv=None):
    p=argparse.ArgumentParser(prog='dq'); sub=p.add_subparsers(dest='cmd',required=True)
    source=sub.add_parser('source'); ssub=source.add_subparsers(dest='source_cmd',required=True)
    reg=ssub.add_parser('register'); reg.add_argument('export'); reg.add_argument('--out',default='registered-source')
    r=sub.add_parser('recover')
    g=r.add_mutually_exclusive_group(required=True); g.add_argument('--export'); g.add_argument('--manifest')
    r.add_argument('--out',default='out'); r.add_argument('--descriptors'); r.add_argument('--previous'); r.add_argument('--code-sha'); r.add_argument('--budget')
    a=p.parse_args(argv)
    if a.cmd=='source' and a.source_cmd=='register':
        manifest=register_export(Path(a.export),Path(a.out)); print(json.dumps(manifest,indent=2,sort_keys=True)); return 0
    if a.cmd=='recover':
        result=recover(Path(a.export) if a.export else None,Path(a.out),Path(a.manifest) if a.manifest else None,Path(a.descriptors) if a.descriptors else None,Path(a.previous) if a.previous else None,a.code_sha,Path(a.budget) if a.budget else None)
        print(json.dumps({'coverage':result['coverage'],'gates':result['gates']},indent=2,sort_keys=True)); return 0 if result['gates']['ok'] else 1
    return 2

if __name__=='__main__': raise SystemExit(main())
