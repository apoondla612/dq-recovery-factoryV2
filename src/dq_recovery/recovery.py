from __future__ import annotations
import json, shutil
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any
from .constants import *
from .parser import parse_expression
from .utils import attrs, local_name, jwrite, sha256, register_export, decode_native
from .semantic import find_mapping, mapping_index, infer_outcomes, normalise, canonical_bytes, shape, canonical_semantics, render

def _expr_records(mapping):
    env={}; records=[]
    for e in mapping.iter():
        a=attrs(e)
        if local_name(e.tag)=='ExpressionField' and 'expression' in a:
            dec,err=decode_native(a['expression']); pr=parse_expression(dec)
            rec={'id':a.get('id'),'name':a.get('name'),'raw':a['expression'],'decoded':dec,'decode_error':err,'parse_status':pr.parse_status,'tree':pr.tree,'comments':pr.comments,'output':a.get('output')=='true','input':a.get('input')=='true'}
            records.append(rec); env[a.get('name')]=pr.tree
    return env,records

def scan_and_recover(work:Path, manifest:dict[str,Any], descriptors_dir:Path|None=None)->dict[str,Any]:
    counts=Counter(); parse_counts=Counter(); tx_counts=Counter(); constructs=Counter(); candidates=[]; rules=[]; ambiguous=[]; helpers=[]; decode_errors=[]
    total_elem=total_attr=total_text=0
    for mem in manifest['members']:
        path=work/mem['path']; root=ET.parse(path).getroot(); target=Path(mem['name']).stem; mids=mapping_index(root); selected=find_mapping(root,target)
        for e in root.iter():
            total_elem+=1; a=attrs(e); total_attr+=len(e.attrib)
            if e.text and e.text.strip(): total_text+=1
            if local_name(e.tag)=='AbstractTransformation' and a.get('type'): tx_counts[a['type']]+=1
            for k,v in a.items():
                if k in LOGIC_ATTRS:
                    kind=LOGIC_ATTRS[k]; counts[kind]+=1; constructs[('record_kind',kind)]+=1
                    if kind in PARSEABLE_KINDS:
                        dec,err=decode_native(v)
                        if err: decode_errors.append({'member':mem['name'],'owner_id':a.get('id'),'kind':kind,'error':err})
                        pr=parse_expression(dec); parse_counts[pr.parse_status]+=1
                        for c in pr.constructs:
                            cls,name=c.split(':',1); constructs[(cls,name)]+=1
                        def walk(n):
                            if isinstance(n,dict):
                                if n.get('op') in CANON_OPS: constructs[('expression_operator',n['op'])]+=1
                                for ch in n.get('args',[]): walk(ch)
                        walk(pr.tree)
        for t,n in tx_counts.items(): pass
        if selected is None: continue
        invs=[e for e in selected.iter() if attrs(e).get('type')=='mapplet:MappletTx' and (attrs(e).get('name') or '').startswith('rule_')]
        for inv in invs:
            ia=attrs(inv); candidates.append({'member':mem['name'],'mapping':target,'invocation_id':ia.get('id'),'invocation_name':ia.get('name'),'definition_id':ia.get('mapplet')})
            definition=mids.get(ia.get('mapplet'))
            if definition is None:
                helpers.append({**candidates[-1],'reason':'definition_missing'}); continue
            env,recs=_expr_records(definition)
            prim=[]
            for r in recs:
                if not r['output']: continue
                outs=infer_outcomes(r['tree'],env)
                if outs:
                    prim.append((r,sorted(outs)))
            if len(prim)==0:
                helpers.append({**candidates[-1],'reason':'no_bounded_primary_endpoint'}); continue
            if len(prim)>1:
                ambiguous.append({**candidates[-1],'reason':'multiple_primary_endpoints','endpoints':[{'id':r['id'],'name':r['name'],'outcomes':o} for r,o in prim]}); continue
            p,outcomes=prim[0]
            norm=normalise(p['tree']); cb=canonical_bytes(norm); shape_sig=json.dumps(shape(norm),sort_keys=True,separators=(',',':'))
            # conservative closure: expression dependencies plus every non-expression operation in definition
            ids=set(); unresolved=set(); byname={r['name']:r for r in recs if r.get('name')}
            def collect(n):
                if not isinstance(n,dict): return
                if n.get('op')=='IDENT':
                    name=n.get('name');
                    if name in byname and name not in ids:
                        ids.add(name); collect(byname[name]['tree'])
                    else: unresolved.add(name)
                for ch in n.get('args',[]): collect(ch)
            collect(p['tree'])
            deps=[]
            for e in definition.iter():
                a=attrs(e)
                if local_name(e.tag)=='AbstractTransformation' and a.get('type') not in {None,'expression:ExpressionTx','mapplet:MappletInputTx','mapplet:MappletOutputTx'}:
                    deps.append({'type':a.get('type'),'id':a.get('id'),'name':a.get('name')})
            parse_status='complete' if p['parse_status']=='complete' and not p['decode_error'] else p['parse_status']
            verification='blocked_external' if deps or unresolved or parse_status!='complete' else 'not_run'
            rule={
                'semantics':{'primary':canonical_semantics(norm),'outcome_universe':['VALID','INVALID','NOT_EVALUATED'],'reachable_outcomes':outcomes},
                'bindings':{'unresolved_identifiers':sorted(unresolved),'external_dependencies':deps},
                'evidence':{'source_member':mem['name'],'source_sha256':mem['sha256'],'mapping':target,'invocation_id':ia.get('id'),'invocation_name':ia.get('name'),'definition_id':ia.get('mapplet'),'primary_endpoint_id':p['id'],'primary_endpoint_name':p['name'],'primary_expression_raw':p['raw'],'primary_expression_decoded':p['decoded'],'supporting_expression_names':sorted(ids),'semantic_hash':sha256(cb),'shape_signature':shape_sig},
                'status':{'parse_status':parse_status,'recovery_status':'unmatched','verification_status':verification}
            }
            # independent render/parse/normalise byte gate for verifiable expression-only case
            if verification=='not_run':
                rend=render(norm); rr=parse_expression(rend)
                if rr.parse_status=='complete' and canonical_bytes(normalise(rr.tree))==cb: rule['status']['verification_status']='passed'
                else: rule['status']['verification_status']='failed'
            rules.append(rule)
    # construct matrix includes transformations once after full scan
    for k,v in tx_counts.items(): constructs[('transformation_type',k)]=v
    rules_dir=work/'output'/'rules'; rules_dir.mkdir(parents=True,exist_ok=True)
    for i,r in enumerate(sorted(rules,key=lambda x:(x['evidence']['mapping'],x['evidence']['invocation_id'],x['evidence']['primary_endpoint_id']))):
        name=f"{i+1:04d}-{r['evidence']['mapping']}-{r['evidence']['invocation_id'].replace(':','_')}.json"; jwrite(rules_dir/name,r)
    clusters=Counter(r['evidence']['shape_signature'] for r in rules)
    coverage={
        'source_members':manifest['member_count'],'structural':{'elements':total_elem,'attributes':total_attr,'text_non_whitespace':total_text},
        'record_kinds':dict(sorted(counts.items())),'parse_status':dict(sorted(parse_counts.items())),
        'candidate_rule_invocations':len(candidates),'primary_endpoint_denominator':len(rules),'helper_or_non_outcome_invocations':len(helpers),'semantic_ambiguities':len(ambiguous),
        'recovery_status':dict(Counter(r['status']['recovery_status'] for r in rules)),
        'verification_status':dict(Counter(r['status']['verification_status'] for r in rules)),
        'descriptor_note':'No human-owned descriptor set supplied; candidate rules remain unmatched.'
    }
    matrix=[{'construct_class':k[0],'construct_name':k[1],'count':v,'support_status':'supported' if k[0] in {'record_kind','transformation_type','expression_operator','expression_builtin','external_invocation'} else 'observed'} for k,v in sorted(constructs.items())]
    jwrite(work/'output'/'coverage.json',coverage); jwrite(work/'output'/'construct-matrix.json',matrix); jwrite(work/'output'/'ambiguities.json',ambiguous); jwrite(work/'output'/'helpers.json',helpers)
    jwrite(work/'output'/'candidate-clusters.json',[{'shape_signature':s,'count':c} for s,c in clusters.most_common()])
    # deterministic run manifest pins authority docs if present
    spec_hashes={}
    auth=Path.cwd()/'specs'/'authority-hashes.json'
    if auth.exists(): spec_hashes=json.loads(auth.read_text(encoding='utf-8')).get('documents',{})
    run_manifest={'archive_sha256':manifest['archive_sha256'],'member_shas':[m['sha256'] for m in manifest['members']],'tool_version':'0.2.0','specification_hashes':spec_hashes,'counts':coverage}
    jwrite(work/'output'/'run-manifest.json',run_manifest)
    failures=[]
    expected={'expression':2084,'lookup-condition':235,'filter-condition':5,'join-condition':11,'sql-query':194,'update-dynamic-cache-condition':235}
    if total_elem!=52313 or total_attr!=249774 or total_text!=0: failures.append('structural baseline mismatch')
    if dict(counts)!=expected: failures.append('record-kind baseline mismatch')
    if parse_counts.get('opaque',0) or parse_counts.get('partial',0): failures.append('parse completeness regression')
    if decode_errors: failures.append('decode errors')
    if any(r['status']['verification_status']=='failed' for r in rules): failures.append('round-trip failure')
    gates={'accounting':not any('baseline mismatch' in x for x in failures),'parse_totality_on_pilot':not any('parse' in x for x in failures),'roundtrip_for_verifiable_rules':not any('round-trip' in x for x in failures),'vendor_neutral_semantics':True,'failures':failures,'ok':not failures}
    # semantics vendor token check
    bad=[]
    for p in rules_dir.glob('*.json'):
        obj=json.loads(p.read_text()); s=json.dumps(obj['semantics']).lower()
        for token in ('informatica','snowflake',':lkp'):
            if token in s: bad.append((p.name,token))
    if bad: gates['vendor_neutral_semantics']=False; gates['failures'].append('vendor token in semantics'); gates['ok']=False
    jwrite(work/'output'/'gates.json',gates)
    return {'coverage':coverage,'gates':gates,'rules':rules,'ambiguous':ambiguous,'helpers':helpers}

def recover(export:Path,out:Path)->dict[str,Any]:
    if out.exists(): shutil.rmtree(out)
    manifest=register_export(export,out)
    return scan_and_recover(out,manifest)
