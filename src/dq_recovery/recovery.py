from __future__ import annotations
import shutil
from pathlib import Path
from typing import Any
from .utils import register_export, load_manifest, jread
from .batch import scan_and_recover

def recover(export:Path|None,out:Path,manifest_path:Path|None=None,descriptors_dir:Path|None=None,previous:Path|None=None,code_sha:str|None=None,budget_path:Path|None=None)->dict[str,Any]:
    if export is not None:
        if out.exists(): shutil.rmtree(out)
        manifest=register_export(export,out); work=out
    elif manifest_path is not None:
        work,manifest=load_manifest(manifest_path)
        if out.resolve()!=work.resolve():
            if out.exists(): shutil.rmtree(out)
            shutil.copytree(work,out); work=out; manifest=jread(work/'pilot-source.manifest.json')
    else:
        raise ValueError('either export or manifest_path is required')
    output_dir=work/'output'
    if output_dir.exists(): shutil.rmtree(output_dir)
    return scan_and_recover(work,manifest,descriptors_dir=descriptors_dir,previous=previous,code_sha=code_sha,budget_path=budget_path)
