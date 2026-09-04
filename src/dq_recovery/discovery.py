from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .utils import attrs, local_name, decode_native
from .parser import parse_expression
from .binding import build_structure_map, bind_tree
from .semantic import infer_outcomes, normalise, canonical_semantics

def _expr_records(mapping):
    structure=build_structure_map(mapping); env={}; records=[]
    for e in mapping.iter():
        a=attrs(e)
        if local_name(e.tag)=='ExpressionField' and 'expression' in a:
            field=structure['fields_by_id'].get(a.get('id'), {})
            scope=field.get('owner_transform_id')
            dec,err=decode_native(a['expression']); pr=parse_expression(dec); br=bind_tree(pr.tree,structure,scope)
            rec={
                'id':a.get('id'),'name':a.get('name'),'raw':a['expression'],'decoded':dec,
                'decode_error':err,'parse_status':pr.parse_status,'bind_status':br['bind_status'],
                'tree':br['tree'],'comments':pr.comments,'output':a.get('output')=='true','input':a.get('input')=='true',
                'owner_transform_id':scope,'owner_transform_name':field.get('owner_transform_name'),
                'bindings':br['bindings'],'unresolved':br['unresolved'],'multiply_resolved':br['multiply_resolved'],
            }
            records.append(rec); env[(scope,a.get('name'))]=br['tree']
    return env,records,structure

def _domain_from_member(name:str)->str:
    p=Path(name)
    parts=[x for x in p.parts[:-1] if x not in {'.','..'}]
    return parts[-1] if parts else p.stem.split('_',1)[0]

def _canonical_dep_type(native:str|None)->str:
    v=(native or '').lower()
    if 'lookup' in v: return 'reference_lookup'
    if 'parser' in v: return 'parse'
    if 'labeler' in v: return 'label'
    if 'filter' in v: return 'filter'
    if 'joiner' in v: return 'row_join'
    if 'mapplet' in v: return 'reusable_operation'
    return 'external_operation'

def _collect_construct(constructs:dict[tuple[str,str],dict[str,Any]], cls:str, name:str, location:str):
    key=(cls,name)
    if key not in constructs:
        constructs[key]={'construct_class':cls,'construct_name':name,'count':0,'support_status':'observed','example':location}
    constructs[key]['count']+=1

def _build_closure(primary:dict[str,Any], recs:list[dict[str,Any]], structure:dict[str,Any], definition)->dict[str,Any]:
    ids=set(); unresolved=set(); multiply=set(); bound_fields={}; refs=set()
    byname={r['name']:r for r in recs if r.get('name') and r.get('owner_transform_id')==primary.get('owner_transform_id')}
    def collect(n):
        if not isinstance(n,dict): return
        if n.get('op')=='LKP' and n.get('name'): refs.add(n.get('name'))
        if n.get('op')=='IDENT':
            name=n.get('name'); binding=n.get('binding')
            if binding and binding.get('field_id'):
                fid=binding['field_id']; field=structure['fields_by_id'].get(fid)
                if field: bound_fields[fid]=field
            elif binding and binding.get('candidates'): multiply.add(name)
            else: unresolved.add(name)
            dep=byname.get(name)
            if dep and not dep.get('input') and name not in ids:
                ids.add(name); collect(dep['tree'])
        for ch in n.get('args',[]): collect(ch)
    collect(primary['tree'])
    supporting=[]
    for name in sorted(ids):
        r=byname[name]
        supporting.append({'id':r['id'],'name':r['name'],'parse_status':r['parse_status'],'bind_status':r['bind_status'],'canonical':canonical_semantics(normalise(r['tree'])),'raw':r['raw'],'decoded':r['decoded'],'_norm':normalise(r['tree'])})
        unresolved.update(r['unresolved']); multiply.update(r['multiply_resolved'])
    companions=[]
    for r in recs:
        if not r.get('output') or r['id']==primary['id'] or r.get('owner_transform_id')!=primary.get('owner_transform_id'): continue
        scope_env={name:tree for (scope,name),tree in {(rr['owner_transform_id'],rr['name']):rr['tree'] for rr in recs if rr.get('name')}.items() if scope==r['owner_transform_id']}
        if infer_outcomes(r['tree'],scope_env): continue
        companions.append({'id':r['id'],'name':r['name'],'parse_status':r['parse_status'],'bind_status':r['bind_status'],'canonical':canonical_semantics(normalise(r['tree'])),'raw':r['raw'],'decoded':r['decoded'],'_norm':normalise(r['tree'])})
        unresolved.update(r['unresolved']); multiply.update(r['multiply_resolved'])
    deps=[]
    for e in definition.iter():
        a=attrs(e)
        if local_name(e.tag)=='AbstractTransformation' and a.get('type') not in {None,'expression:ExpressionTx','mapplet:MappletInputTx','mapplet:MappletOutputTx'}:
            deps.append({'type':a.get('type'),'canonical_kind':_canonical_dep_type(a.get('type')),'id':a.get('id'),'name':a.get('name')})
    for ref in sorted(refs): deps.append({'type':'external_lookup','canonical_kind':'reference_lookup','name':ref})
    return {'supporting':supporting,'companions':companions,'external_dependencies':deps,'unresolved':sorted(unresolved),'multiply':sorted(multiply),'bound_fields':[bound_fields[k] for k in sorted(bound_fields)]}
