from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .recovery import recover

def main(argv=None):
    p=argparse.ArgumentParser(prog='dq'); sub=p.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('recover'); r.add_argument('--export',required=True); r.add_argument('--out',default='out')
    a=p.parse_args(argv)
    if a.cmd=='recover':
        result=recover(Path(a.export),Path(a.out)); print(json.dumps({'coverage':result['coverage'],'gates':result['gates']},indent=2,sort_keys=True)); return 0 if result['gates']['ok'] else 1
    return 2
if __name__=='__main__': raise SystemExit(main())
