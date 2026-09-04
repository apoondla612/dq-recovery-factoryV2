from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .utils import stable_hash_json
from .semantic import concrete_slots

@dataclass(frozen=True)
class DescriptorSet:
    version: str
    descriptors: tuple[dict[str,Any], ...]
    hash: str

_PLACEHOLDERS={'FIELD','STR','NUM','NULL','BOOL','EMPTY','OUTCOME','REF','LIT'}

def _validate_shape(shape:Any, path:Path)->None:
    if isinstance(shape,dict):
        if set(shape) != {'placeholder','slot'} or shape.get('placeholder') not in _PLACEHOLDERS or not str(shape.get('slot','')).isdigit() or int(shape['slot']) < 1:
            raise ValueError(f"{path}: invalid placeholder shape {shape!r}")
        return
    if not isinstance(shape,list) or not shape or not isinstance(shape[0],str):
        raise ValueError(f"{path}: invalid shape node {shape!r}")
    if shape[0]=='reference_lookup':
        if len(shape)!=3: raise ValueError(f"{path}: reference_lookup shape needs reference and args")
        _validate_shape(shape[1],path)
        if not isinstance(shape[2],list): raise ValueError(f"{path}: reference_lookup args must be list")
        for child in shape[2]: _validate_shape(child,path)
        return
    if len(shape)==2:
        if not isinstance(shape[1],list): raise ValueError(f"{path}: shape args must be list")
        for child in shape[1]: _validate_shape(child,path)
        return
    if len(shape)==1: return
    raise ValueError(f"{path}: invalid shape arity {shape!r}")

def _validate_descriptor(d:dict[str,Any], path:Path)->dict[str,Any]:
    required={'name','version','shape','parameters','outcomes','example'}
    missing=sorted(required-set(d))
    if missing: raise ValueError(f"{path}: descriptor missing {missing}")
    if not isinstance(d['name'],str) or not d['name'].strip(): raise ValueError(f"{path}: invalid name")
    if not isinstance(d['parameters'],list): raise ValueError(f"{path}: parameters must be a list")
    _validate_shape(d['shape'],path)
    seen=set()
    for p in d['parameters']:
        if not isinstance(p,dict) or not isinstance(p.get('name'),str) or not str(p.get('slot','')).isdigit():
            raise ValueError(f"{path}: each parameter needs name and numeric slot")
        if p['name'] in seen: raise ValueError(f"{path}: duplicate parameter {p['name']}")
        seen.add(p['name'])
    return d

def load_descriptor_set(directory:Path|None)->DescriptorSet:
    if directory is None or not directory.exists():
        return DescriptorSet('none',tuple(),stable_hash_json([]))
    files=sorted(directory.glob('*.json'))
    desc=[]
    for p in files:
        obj=json.loads(p.read_text(encoding='utf-8'))
        if isinstance(obj,list):
            desc.extend(_validate_descriptor(x,p) for x in obj)
        else:
            desc.append(_validate_descriptor(obj,p))
    desc=sorted(desc,key=lambda d:(d['name'],str(d['version'])))
    version=stable_hash_json([(d['name'],d['version']) for d in desc])[:16] if desc else 'none'
    return DescriptorSet(version,tuple(desc),stable_hash_json(desc))

def match_rule(norm_tree:dict[str,Any], shape_obj:Any, descriptor_set:DescriptorSet, parse_status:str)->dict[str,Any]:
    same=[d for d in descriptor_set.descriptors if d.get('shape')==shape_obj]
    if not same: return {'status':'unmatched','matched_type':None,'parameters':{},'candidates':[]}
    slots=concrete_slots(norm_tree)
    complete=[]; partial=[]
    for d in same:
        params={}; missing=[]
        for p in d['parameters']:
            slot=str(p['slot'])
            if slot not in slots: missing.append(p['name'])
            else: params[p['name']]=slots[slot]
        record={'descriptor':d['name'],'version':d['version'],'parameters':params,'missing_parameters':missing}
        if missing: partial.append(record)
        else: complete.append(record)
    if parse_status!='complete':
        candidates=complete+partial
        return {'status':'partial','matched_type':None,'parameters':{},'candidates':candidates,'reason':'parse_status_caps_match'}
    if len(complete)>1:
        return {'status':'descriptor_conflict','matched_type':None,'parameters':{},'candidates':complete}
    if len(complete)==1:
        c=complete[0]; return {'status':'matched','matched_type':c['descriptor'],'matched_version':c['version'],'parameters':c['parameters'],'candidates':complete+partial}
    return {'status':'partial','matched_type':None,'parameters':{},'candidates':partial,'reason':'unbound_parameters'}
